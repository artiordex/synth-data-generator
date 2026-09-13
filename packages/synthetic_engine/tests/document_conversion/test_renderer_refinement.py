# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_renderer_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_renderer_refinement.py
# 목적: 문서 렌더러 서식 출력 개선 사항을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Inspect renderer output directly; integration runs are owned by main QA."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import posixpath
from zipfile import ZipFile

import pytest
from lxml import etree, html
from PIL import Image

from synthetic_engine.document_conversion.core.enums import (
    BorderStyle, ParagraphAlign, StrikeStyle, TableAlign, UnderlineStyle, VerticalAlign,
)
from synthetic_engine.document_conversion.core.ir import (
    BorderIR, DocumentIR, DrawingIR, FieldIR, HeaderFooterIR, HyperlinkIR,
    ImageIR, ParagraphIR, SectionIR, TableCellIR, TableIR, TabIR, TextRunIR,
    UnsupportedRecordIR,
)
from synthetic_engine.document_conversion.core.source_ref import SourceRef
from synthetic_engine.document_conversion.parsers.docx_parser import DocxParser
from synthetic_engine.document_conversion.parsers.hwpx_parser import HwpxParser
from synthetic_engine.document_conversion.renderers.docx_renderer import DocxRenderer
from synthetic_engine.document_conversion.renderers.html_renderer import HtmlRenderer
from synthetic_engine.document_conversion.renderers.hwpx_renderer import HwpxRenderer


NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


# word xml 작업을 수행함
def word_xml(path, member='word/document.xml'):
    with ZipFile(path) as archive:
        return etree.fromstring(archive.read(member))


# attr 작업을 수행함
def attr(root, xpath, name='val'):
    return root.xpath(xpath, namespaces=NS)[0].get('{' + NS['w'] + '}' + name)


# styled document 작업을 수행함
def styled_document():
    run = TextRunIR(
        ' literal <&> ', font_family_ko='Malgun Gothic', font_family_en='Arial',
        size_pt=12, bold=True, italic=True, underline=UnderlineStyle.WAVY,
        strike=StrikeStyle.DOUBLE, color_hex='112233', bg_color_hex='AABBCC',
        letter_spacing_pt=0.75, scale_percent=85, superscript=True, language='ko-KR',
    )
    paragraph = ParagraphIR(
        [run, TextRunIR('sub', subscript=True), TabIR(position_pt=48)],
        align=ParagraphAlign.DISTRIBUTE, line_spacing_percent=150,
        space_before_pt=6, space_after_pt=8, indent_pt=24, hanging_pt=12,
        page_break_before=True, keep_with_next=True, keep_lines_together=True,
    )
    return DocumentIR(sections=[SectionIR(elements=[paragraph])])


# 워드(DOCX) native typography and 문단 layout 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_native_typography_and_paragraph_layout(tmp_path):
    path = tmp_path / 'styles.docx'
    DocxRenderer().render(styled_document(), path)
    root = word_xml(path)
    run = root.xpath('//w:body/w:p/w:r', namespaces=NS)[0]
    assert attr(run, './w:rPr/w:u') == 'wave'
    assert attr(run, './w:rPr/w:vertAlign') == 'superscript'
    assert run.xpath('./w:rPr/w:dstrike', namespaces=NS)
    assert attr(run, './w:rPr/w:spacing') == '15'
    assert attr(run, './w:rPr/w:w') == '85'
    assert attr(run, './w:rPr/w:rFonts', 'eastAsia') == 'Malgun Gothic'
    assert attr(run, './w:rPr/w:rFonts', 'ascii') == 'Arial'
    assert attr(run, './w:rPr/w:shd', 'fill') == 'AABBCC'
    assert attr(run, './w:rPr/w:lang') == 'ko-KR'
    assert root.xpath('//w:vertAlign[@w:val="subscript"]', namespaces=NS)
    assert attr(root, '//w:pPr/w:jc') == 'distribute'
    assert attr(root, '//w:pPr/w:spacing', 'line') == '360'
    assert attr(root, '//w:pPr/w:spacing', 'before') == '120'
    assert attr(root, '//w:pPr/w:ind', 'hanging') == '240'
    for tag in ('pageBreakBefore', 'keepNext', 'keepLines'):
        assert root.xpath('//w:pPr/w:' + tag, namespaces=NS)
    assert attr(root, '//w:tabs/w:tab', 'pos') == '960'
    assert root.xpath('//w:t/text()', namespaces=NS)[0] == ' literal <&> '
    with ZipFile(path) as archive:
        assert not any(name.startswith(('word/header', 'word/footer')) for name in archive.namelist())


# HTML 웹 문서 typography escaping and layout 기능의 정상 동작 및 제약조건을 테스트함
def test_html_typography_escaping_and_layout(tmp_path):
    path = tmp_path / 'styles.html'
    HtmlRenderer().render(styled_document(), path)
    root = html.fromstring(path.read_text(encoding='utf-8'))
    paragraph = root.xpath('//p')[0]
    assert paragraph.text_content().startswith(' literal <&> sub')
    assert 'text-align-last:justify' in paragraph.get('style')
    assert 'line-height:1.5' in paragraph.get('style')
    assert 'text-indent:-12pt' in paragraph.get('style')
    assert 'break-before:page' in paragraph.get('style')
    assert root.xpath('//span[@lang="ko-KR"]')
    styles = ';'.join(root.xpath('//span/@style'))
    for value in ('vertical-align:super', 'vertical-align:sub', 'text-decoration-style:wavy',
                  'text-decoration-style:double', 'letter-spacing:0.75pt', 'transform:scaleX(0.85)'):
        assert value in styles
    assert not HtmlRenderer.capabilities.supports_font_scaling


# 표(테이블) document 작업을 수행함
def table_document():
    nested = TableIR(rows=[[TableCellIR(0, 0)]], column_widths_pt=[70])
    cell = TableCellIR(
        0, 0, content=[nested], padding_pt=(1, 2, 3, 4),
        vertical_align=VerticalAlign.CENTER, bg_color_hex='EEEEEE', height_pt=24,
        borders={'top': BorderIR(BorderStyle.NONE),
                 'bottom': BorderIR(BorderStyle.DOUBLE, 1, '123456'),
                 'slash': BorderIR(BorderStyle.SOLID, 0.5, 'FF0000')},
    )
    table = TableIR(rows=[[cell], [TableCellIR(1, 0)]], column_widths_pt=[100],
                    total_width_pt=100, alignment=TableAlign.RIGHT,
                    repeat_header_rows=1, cant_split=True)
    return DocumentIR(sections=[SectionIR(elements=[table])])


# 워드(DOCX) 표(테이블) 스타일 목록 and required final 셀 문단 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_table_styles_and_required_final_cell_paragraph(tmp_path):
    path = tmp_path / 'table.docx'
    DocxRenderer().render(table_document(), path)
    root = word_xml(path)
    table = root.xpath('//w:body/w:tbl', namespaces=NS)[0]
    assert attr(table, './w:tblPr/w:jc') == 'right'
    assert attr(table, './w:tblPr/w:tblW', 'w') == '2000'
    assert len(table.xpath('./w:tr/w:trPr/w:tblHeader', namespaces=NS)) == 1
    assert len(table.xpath('./w:tr/w:trPr/w:cantSplit', namespaces=NS)) == 2
    cell = table.xpath('./w:tr/w:tc', namespaces=NS)[0]
    assert attr(cell, './w:tcPr/w:vAlign') == 'center'
    assert attr(cell, './w:tcPr/w:tcMar/w:left', 'w') == '80'
    assert attr(cell, './w:tcPr/w:tcBorders/w:top') == 'nil'
    assert attr(cell, './w:tcPr/w:tcBorders/w:bottom') == 'double'
    assert attr(cell, './w:tcPr/w:tcBorders/w:tr2bl', 'sz') == '4'
    assert cell[-1].tag == '{' + NS['w'] + '}p'
    assert cell[-2].tag == '{' + NS['w'] + '}tbl'


# 워드(DOCX) 표(테이블) 병합 너비 padding 테두리 roundtrip 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_table_merge_width_padding_border_roundtrip(tmp_path):
    table = TableIR(
        rows=[
            [TableCellIR(0, 0, col_span=2, padding_pt=(1, 2, 3, 4),
                         borders={'bottom': BorderIR(BorderStyle.DOUBLE, 1, '123456')},
                         content=[ParagraphIR([TextRunIR('merged')])])],
            [TableCellIR(1, 0, content=[ParagraphIR([TextRunIR('left')])]),
             TableCellIR(1, 1, content=[ParagraphIR([TextRunIR('right')])])],
        ],
        column_widths_pt=[72, 144],
        total_width_pt=216,
    )
    path = tmp_path / 'roundtrip-table.docx'
    DocxRenderer().render(DocumentIR(sections=[SectionIR(elements=[table])]), path)
    parsed = DocxParser().parse(path)
    parsed_table = next(block for block in parsed.iter_blocks() if isinstance(block, TableIR))
    merged = parsed_table.rows[0][0]
    assert parsed_table.column_widths_pt == [72, 144]
    assert parsed_table.total_width_pt == 216
    assert (merged.row_index, merged.col_index, merged.row_span, merged.col_span) == (0, 0, 1, 2)
    assert merged.padding_pt == (1, 2, 3, 4)
    assert merged.borders['bottom'].style == BorderStyle.DOUBLE
    assert merged.borders['bottom'].color_hex == '123456'


# HTML 웹 문서 표(테이블) headers padding borders and diagonal 기능의 정상 동작 및 제약조건을 테스트함
def test_html_table_headers_padding_borders_and_diagonal(tmp_path):
    path = tmp_path / 'table.html'
    HtmlRenderer().render(table_document(), path)
    root = html.fromstring(path.read_text(encoding='utf-8'))
    assert root.xpath('//table/thead/tr/th')
    cell = root.xpath('//table/thead/tr/th')[0]
    assert 'vertical-align:middle' in cell.get('style')
    assert 'padding:1pt 2pt 3pt 4pt' in cell.get('style')
    assert 'border-bottom:1pt double #123456' in cell.get('style')
    assert cell.xpath('./svg/line[@y1="100"]')
    assert root.xpath('//tr[contains(@style,"break-inside:avoid")]')


# 한글 표준(HWPX) renderer embeds 이미지 bytes 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_renderer_embeds_image_bytes(tmp_path):
    stream = BytesIO()
    Image.new('RGB', (3, 2), 'white').save(stream, format='PNG')
    image_bytes = stream.getvalue()
    source = DocumentIR(sections=[SectionIR(elements=[
        ParagraphIR([TextRunIR('before image')]),
        ImageIR(image_bytes, 'image/png', 'PNG', 30, 20, original_width_px=3, original_height_px=2),
    ])])
    path = tmp_path / 'image.hwpx'
    HwpxRenderer().render(source, path)
    from hwpx.document import HwpxDocument
    HwpxDocument.open(path)
    parsed = HwpxParser().parse(path)
    images = [block for block in parsed.iter_blocks() if isinstance(block, ImageIR)]
    paragraphs = [block for block in parsed.iter_blocks() if isinstance(block, ParagraphIR)]
    assert len(images) == 1
    assert images[0].image_bytes == image_bytes
    assert any('before image' == ''.join(run.text for run in paragraph.inlines if isinstance(run, TextRunIR))
               for paragraph in paragraphs)
    with ZipFile(path) as archive:
        section = etree.fromstring(archive.read('Contents/section0.xml'))
        references = [
            value
            for node in section.iter()
            for key, value in node.attrib.items()
            if etree.QName(key).localname == 'binaryItemIDRef'
        ]
        manifest = etree.fromstring(archive.read('Contents/content.hpf'))
        hrefs = {node.get('id'): node.get('href') for node in manifest.iter() if node.get('id') and node.get('href')}
        assert len(references) == 1
        href = hrefs[references[0]]
        resolved = href if href in archive.namelist() else posixpath.normpath(posixpath.join('Contents', href))
        assert resolved in archive.namelist()
        assert sha256(archive.read(resolved)).digest() == sha256(image_bytes).digest()


# section headers footers fields and links 기능의 정상 동작 및 제약조건을 테스트함
def test_section_headers_footers_fields_and_links(tmp_path):
    link = HyperlinkIR('https://example.test/?a=1&b=2', [TextRunIR('linked', bold=True)], title='title')
    header = HeaderFooterIR([ParagraphIR([link])])
    footer = HeaderFooterIR([ParagraphIR([FieldIR('PAGE_NUMBER', cached_text='7')])])
    document = DocumentIR(sections=[
        SectionIR(page_width_pt=600, page_height_pt=800, margin_left_pt=30,
                  margin_right_pt=40, header_distance_pt=12, footer_distance_pt=18,
                  column_count=2, column_gap_pt=20, header=header, footer=footer),
        SectionIR(elements=[ParagraphIR([TextRunIR('second')])]),
    ])
    path = tmp_path / 'sections.docx'
    DocxRenderer().render(document, path)
    root = word_xml(path)
    assert attr(root, '//w:sectPr/w:pgMar', 'left') == '600'
    assert attr(root, '//w:sectPr/w:cols', 'num') == '2'
    assert attr(word_xml(path, 'word/footer1.xml'), '//w:fldSimple', 'instr') == 'PAGE'
    assert word_xml(path, 'word/header1.xml').xpath('//w:hyperlink/w:r/w:rPr/w:b', namespaces=NS)
    assert not word_xml(path, 'word/header2.xml').xpath('//w:hyperlink', namespaces=NS)
    with ZipFile(path) as archive:
        relationships = etree.fromstring(archive.read('word/_rels/header1.xml.rels'))
        assert relationships[0].get('Target') == link.target
        assert relationships[0].get('TargetMode') == 'External'
    parsed = DocxParser().parse(path)
    parsed_link = parsed.sections[0].header.elements[0].inlines[0]
    assert isinstance(parsed_link, HyperlinkIR)
    assert parsed_link.target == link.target
    assert parsed_link.title == 'title'
    html_path = tmp_path / 'sections.html'
    HtmlRenderer().render(document, html_path)
    rendered = html.fromstring(html_path.read_text(encoding='utf-8'))
    assert rendered.xpath('//header//a')[0].get('href') == link.target
    assert rendered.xpath('//footer//span[@data-field-type="PAGE_NUMBER"]')[0].text == '7'
    assert not HtmlRenderer.capabilities.supports_headers


@dataclass
class UnknownInline:
    source_ref: SourceRef


# unmapped objects 분석 리포트 their source 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('renderer,suffix', [(DocxRenderer, 'docx'), (HtmlRenderer, 'html')])
def test_unmapped_objects_report_their_source(renderer, suffix, tmp_path):
    ref = SourceRef('fixture', object_id='unsupported')
    document = DocumentIR(sections=[SectionIR(elements=[
        ParagraphIR([UnknownInline(ref), FieldIR('UNKNOWN', cached_text='cache', source_ref=ref)]),
        DrawingIR('shape', source_ref=ref),
        UnsupportedRecordIR(1, 0, b'opaque', source_ref=ref),
    ])])
    renderer().render(document, tmp_path / ('unsupported.' + suffix))
    warnings = [w for w in document.warnings if w.code.endswith('UNMAPPED_CONTENT')]
    assert len(warnings) == 4
    assert all(w.source_ref is ref for w in warnings)
    assert {w.feature for w in warnings} >= {'UnknownInline', 'DrawingIR', 'UnsupportedRecordIR'}


# HTML 웹 문서 preserves 병합 crossing header boundary with warning 기능의 정상 동작 및 제약조건을 테스트함
def test_html_preserves_merge_crossing_header_boundary_with_warning(tmp_path):
    ref = SourceRef('fixture', object_id='merged')
    table = TableIR(rows=[[TableCellIR(0, 0, row_span=2)], []], repeat_header_rows=1, source_ref=ref)
    document = DocumentIR(sections=[SectionIR(elements=[table])])
    path = tmp_path / 'crossing.html'
    HtmlRenderer().render(document, path)
    root = html.fromstring(path.read_text(encoding='utf-8'))
    assert not root.xpath('//thead')
    assert root.xpath('//tbody/tr/td[@rowspan="2"]')
    assert any(w.feature == 'repeat-header-rowspan-crossing' and w.source_ref is ref
               for w in document.warnings)
