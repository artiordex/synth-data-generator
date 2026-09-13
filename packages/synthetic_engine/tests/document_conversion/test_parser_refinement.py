# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_parser_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_parser_refinement.py
# 목적: 문서 파서 세부 구현 개선 사항을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Parser regressions using in-memory documents; executed by the main agent."""
from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image

from synthetic_engine.document_conversion.core.ir import (
    ImageIR, LineBreakIR, ParagraphIR, TableIR, TabIR, TextRunIR, UnsupportedRecordIR, HyperlinkIR,
)
from synthetic_engine.document_conversion.core.enums import BorderStyle
from synthetic_engine.document_conversion.parsers.docx_parser import DocxParser, W, R, A, WP, REL
from synthetic_engine.document_conversion.parsers.hwpx_parser import HwpxParser, HP, HH, HS
from synthetic_engine.document_conversion.parsers.html_parser import HtmlParser
from synthetic_engine.document_conversion.parsers.markdown_parser import MarkdownParser
from synthetic_engine.document_conversion.parsers.package import DocumentPackage


# archive 작업을 수행함
def archive(entries):
    stream = BytesIO()
    with ZipFile(stream, 'w') as package:
        for name, data in entries.items():
            package.writestr(name, data)
    stream.seek(0)
    return stream


# 워드(DOCX) 작업을 수행함
def docx(body, extra=None):
    return archive({'word/document.xml': (
        f'<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:a="{A}" xmlns:wp="{WP}">'
        f'<w:body>{body}</w:body></w:document>'), **(extra or {})})


# 한글 표준(HWPX) 작업을 수행함
def hwpx(body, extra=None):
    return archive({
        'Contents/header.xml': f'<h:head xmlns:h="{HH}"/>',
        'Contents/section0.xml': f'<s:sec xmlns:s="{HS}" xmlns:p="{HP}">{body}</s:sec>',
        **(extra or {}),
    })


# raster 작업을 수행함
def raster():
    stream = BytesIO()
    Image.new('RGB', (4, 2), 'white').save(stream, format='PNG')
    return stream.getvalue()


# word 셀 작업을 수행함
def word_cell(content, props=''):
    return f'<w:tc><w:tcPr>{props}</w:tcPr>{content}</w:tc>'


# word 문단 작업을 수행함
def word_paragraph(text):
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


# word drawing 작업을 수행함
def word_drawing():
    return ('<w:drawing><wp:inline><wp:extent cx="914400" cy="457200"/>'
            '<a:graphic><a:blip r:embed="img"/></a:graphic></wp:inline></w:drawing>')


# relationships 작업을 수행함
def relationships(target='media/image.png', mode='Internal'):
    return (f'<Relationships xmlns="{REL}"><Relationship Id="img" '
            f'Type="{R}/image" Target="{target}" TargetMode="{mode}"/></Relationships>')


# hyperlink relationships 작업을 수행함
def hyperlink_relationships():
    return (f'<Relationships xmlns="{REL}"><Relationship Id="link" '
            f'Type="{R}/hyperlink" Target="https://example.test/a?b=1" TargetMode="External"/></Relationships>')


# 워드(DOCX) verbatim whitespace controls comments and empty 문단 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_verbatim_whitespace_controls_comments_and_empty_paragraph():
    body = ('<w:p><w:r><!-- note --><w:t xml:space="preserve"> A\u00a0\u3000 </w:t>'
            '<w:tab/><w:t> B </w:t><w:cr/><w:t>C </w:t></w:r></w:p><w:p/>')
    document = DocxParser().parse(docx(body))
    paragraph, empty = document.sections[0].elements
    assert [run.text for run in paragraph.inlines if isinstance(run, TextRunIR)] == [' A\u00a0\u3000 ', ' B ', 'C ']
    assert isinstance(paragraph.inlines[1], TabIR)
    assert isinstance(paragraph.inlines[3], LineBreakIR)
    assert empty.inlines == []
    assert len({run.source_ref.xml_path for run in paragraph.inlines}) == 5


# 워드(DOCX) hyperlink relationship is preserved 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_hyperlink_relationship_is_preserved():
    body = ('<w:p><w:hyperlink r:id="link" w:tooltip="source tip">'
            '<w:r><w:t>Linked</w:t></w:r></w:hyperlink></w:p>')
    document = DocxParser().parse(docx(body, {'word/_rels/document.xml.rels': hyperlink_relationships()}))
    link = document.sections[0].elements[0].inlines[0]
    assert isinstance(link, HyperlinkIR)
    assert link.target == 'https://example.test/a?b=1'
    assert link.title == 'source tip'
    assert link.inlines[0].text == 'Linked'


# 워드(DOCX) nested 표 목록 keep order depth and local source addresses 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_nested_tables_keep_order_depth_and_local_source_addresses():
    inner = '<w:tbl><w:tr>' + word_cell(word_paragraph('inner')) + '</w:tr></w:tbl>'
    outer = '<w:tbl><w:tr>' + word_cell(word_paragraph('before') + inner + word_paragraph('after')) + '</w:tr></w:tbl>'
    document = DocxParser().parse(docx(outer))
    tables = [block for block in document.iter_blocks() if isinstance(block, TableIR)]
    assert [table.depth for table in tables] == [0, 1]
    assert [type(block) for block in tables[0].rows[0][0].content] == [ParagraphIR, TableIR, ParagraphIR]
    for table in tables:
        ref = table.rows[0][0].source_ref
        assert ref.table_id == table.table_id == table.source_ref.table_id
        assert (ref.row_index, ref.col_index) == (0, 0)


# 워드(DOCX) 격자 구조 offset and vertical 병합 preserve continuation 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_grid_offset_and_vertical_merge_preserve_continuation_text():
    first = word_cell(word_paragraph('first'), '<w:vMerge w:val="restart"/>')
    second = word_cell(word_paragraph('continued'), '<w:vMerge/>')
    before = '<w:trPr><w:gridBefore w:val="1"/></w:trPr>'
    body = f'<w:tbl><w:tblGrid><w:gridCol/><w:gridCol/></w:tblGrid><w:tr>{before}{first}</w:tr><w:tr>{before}{second}</w:tr></w:tbl>'
    table = DocxParser().parse(docx(body)).sections[0].elements[0]
    cell = table.rows[0][0]
    assert (cell.col_index, cell.row_span) == (1, 2)
    assert table.rows[1] == []
    assert [block.inlines[0].text for block in cell.content] == ['first', 'continued']


# 워드(DOCX) 표(테이블) 격자 구조 너비 목록 셀 너비 padding and borders 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_table_grid_widths_cell_width_padding_and_borders():
    props = ('<w:tcW w:w="1440" w:type="dxa"/>'
             '<w:tcMar><w:top w:w="20" w:type="dxa"/><w:right w:w="40" w:type="dxa"/>'
             '<w:bottom w:w="60" w:type="dxa"/><w:left w:w="80" w:type="dxa"/></w:tcMar>'
             '<w:tcBorders><w:bottom w:val="double" w:sz="8" w:color="123456"/></w:tcBorders>')
    body = '<w:tbl><w:tblGrid><w:gridCol w:w="1440"/><w:gridCol w:w="2880"/></w:tblGrid><w:tr>' + word_cell(word_paragraph('A'), props) + '</w:tr></w:tbl>'
    table = DocxParser().parse(docx(body)).sections[0].elements[0]
    cell = table.rows[0][0]
    assert table.column_widths_pt == [72, 144]
    assert table.total_width_pt == 216
    assert cell.width_pt == 72
    assert cell.padding_pt == (1, 2, 3, 4)
    assert cell.borders['bottom'].style == BorderStyle.DOUBLE
    assert cell.borders['bottom'].width_pt == 1
    assert cell.borders['bottom'].color_hex == '123456'


# 워드(DOCX) 이미지 original bytes order dimensions and resource ref 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_image_original_bytes_order_dimensions_and_resource_ref():
    data = raster()
    body = '<w:p><w:r><w:t> before </w:t>' + word_drawing() + '<w:t> after </w:t></w:r></w:p>'
    document = DocxParser().parse(docx(body, {
        'word/_rels/document.xml.rels': relationships(), 'word/media/image.png': data,
    }))
    before, image, after = document.sections[0].elements
    assert before.inlines[0].text == ' before '
    assert after.inlines[0].text == ' after '
    assert isinstance(image, ImageIR)
    assert image.image_bytes == document.resources.get(image.resource_id) == data
    assert (image.width_pt, image.height_pt) == (72, 36)
    assert (image.original_width_px, image.original_height_px) == (4, 2)
    assert image.source_ref.xml_path.endswith('/w:drawing')


# 워드(DOCX) unresolved 이미지 목록 are retained without fetching 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('target,mode', [
    ('https://example.invalid/image.png', 'External'),
    ('../../outside.png', 'Internal'),
    ('media/missing.png', 'Internal'),
])
def test_docx_unresolved_images_are_retained_without_fetching(target, mode):
    document = DocxParser().parse(docx('<w:p><w:r>' + word_drawing() + '</w:r></w:p>', {
        'word/_rels/document.xml.rels': relationships(target, mode),
    }))
    assert isinstance(document.sections[0].elements[0], UnsupportedRecordIR)
    assert any(w.code == 'DOCX_IMAGE_UNRESOLVED' and w.source_ref for w in document.warnings)


# 한글 표준(HWPX) relative binary reference and 텍스트 tails 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_relative_binary_reference_and_text_tails():
    data = raster()
    body = ('<p:p><p:run><p:t> A <p:tab/> B <p:lineBreak/> C </p:t>'
            '<p:pic id="picture"><p:sz width="7200" height="3600"/>'
            '<p:img binaryItemIDRef="img"/></p:pic></p:run></p:p>')
    document = HwpxParser().parse(hwpx(body, {
        'Contents/content.hpf': '<package><item id="img" href="../BinData/image.png"/></package>',
        'BinData/image.png': data,
    }))
    paragraph, image = document.sections[0].elements
    assert [run.text for run in paragraph.inlines if isinstance(run, TextRunIR)] == [' A ', ' B ', ' C ']
    assert isinstance(image, ImageIR)
    assert document.resources.get(image.resource_id) == data
    assert image.source_ref.object_id == 'picture'


# 한글 표준(HWPX) unsupported 이미지 preserves xml and continues 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_unsupported_image_preserves_xml_and_continues():
    body = '<p:pic><p:sz width="100" height="100"/><p:img binaryItemIDRef="img"/></p:pic>'
    document = HwpxParser().parse(hwpx(body, {
        'Contents/content.hpf': '<package><item id="img" href="../BinData/image.wmf"/></package>',
        'BinData/image.wmf': b'unsupported image payload',
    }))
    assert isinstance(document.sections[0].elements[0], UnsupportedRecordIR)
    assert any(w.code == 'HWPX_IMAGE_UNRESOLVED' for w in document.warnings)


# 한글 표준(HWPX) nested source refs and depth 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_nested_source_refs_and_depth():
    body = '<p:p><p:run><p:t>text</p:t></p:run></p:p>'
    for _ in range(3):
        body = ('<p:tbl rowCnt="1" colCnt="1"><p:tr><p:tc><p:cellAddr rowAddr="0" colAddr="0"/>'
                '<p:subList>' + body + '</p:subList></p:tc></p:tr></p:tbl>')
    tables = [block for block in HwpxParser().parse(hwpx(body)).iter_blocks() if isinstance(block, TableIR)]
    assert [table.depth for table in tables] == [0, 1, 2]
    assert all(table.rows[0][0].source_ref.table_id == table.table_id for table in tables)


# 한글 표준(HWPX) rejects invalid 격자 구조 before 기하 구조 allocation 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('body', [
    '<p:tbl rowCnt="1000000000"/>',
    '<p:tbl rowCnt="1" colCnt="1"><p:tr><p:tc><p:cellAddr rowAddr="-1" colAddr="0"/></p:tc></p:tr></p:tbl>',
    '<p:tbl rowCnt="1" colCnt="1"><p:tr><p:tc><p:cellAddr rowAddr="0" colAddr="1"/></p:tc></p:tr></p:tbl>',
])
def test_hwpx_rejects_invalid_grid_before_geometry_allocation(body):
    with pytest.raises(ValueError):
        HwpxParser().parse(hwpx(body))


# 워드(DOCX) rejects oversized 격자 구조 스팬 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_rejects_oversized_grid_span():
    body = '<w:tbl><w:tr>' + word_cell('', '<w:gridSpan w:val="1000000000"/>') + '</w:tr></w:tbl>'
    with pytest.raises(ValueError, match='grid limits'):
        DocxParser().parse(docx(body))


# package rejects ambiguous member names 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('name', ['word/./document.xml', 'word//document.xml', '../escape', '/absolute'])
def test_package_rejects_ambiguous_member_names(name):
    with pytest.raises(ValueError, match='Unsafe'):
        DocumentPackage(archive({name: b'x'}))


# package rejects raw windows separator member name 기능의 정상 동작 및 제약조건을 테스트함
def test_package_rejects_raw_windows_separator_member_name():
    # ZipInfo normalizes backslashes while writing on Windows. Patch the raw
    # local and central directory names so this exercises an imported archive.
    payload = archive({'word/file': b'x'}).getvalue().replace(b'word/file', b'word\\file')
    with pytest.raises(ValueError, match='Unsafe'):
        DocumentPackage(BytesIO(payload))


# package reference resolution cannot escape 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('target', ['../../escape', '%2e%2e/%2e%2e/escape', 'file:///etc/passwd', '//host/image', 'media%5cimage.png'])
def test_package_reference_resolution_cannot_escape(target):
    with DocumentPackage(archive({'word/media/image.png': b'x'})) as package:
        with pytest.raises(ValueError):
            package.resolve('word/document.xml', target)


# package allows internal parent reference and rejects utf16 dtd 기능의 정상 동작 및 제약조건을 테스트함
def test_package_allows_internal_parent_reference_and_rejects_utf16_dtd():
    xml = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY e "bad">]><x>&e;</x>'
    with DocumentPackage(archive({'BinData/image.png': b'x', 'doc.xml': xml.encode('utf-16')})) as package:
        assert package.resolve('Contents/content.hpf', '../BinData/image.png') == 'BinData/image.png'
        with pytest.raises(ValueError, match='DTD'):
            package.xml('doc.xml')


# HTML 웹 문서 bounds nested 표 목록 and source refs 기능의 정상 동작 및 제약조건을 테스트함
def test_html_bounds_nested_tables_and_source_refs():
    document = HtmlParser().parse_content('<table><tr><td> before <table><tr><td>inner</td></tr></table> after </td></tr></table>')
    tables = [block for block in document.iter_blocks() if isinstance(block, TableIR)]
    assert [table.depth for table in tables] == [0, 1]
    assert tables[1].rows[0][0].source_ref.table_id == tables[1].table_id
    with pytest.raises(ValueError, match='grid limits'):
        HtmlParser().parse_content('<table><tr><td rowspan="1000000000">x</td></tr></table>')


# 마크다운 uses no temporary 파일 목록 and keeps source format 기능의 정상 동작 및 제약조건을 테스트함
def test_markdown_uses_no_temporary_files_and_keeps_source_format(monkeypatch):
    pytest.importorskip('markdown')
    import tempfile

    # forbidden 작업을 수행함
    def forbidden(*args, **kwargs):
        raise AssertionError('Parser must not write temporary files')

    monkeypatch.setattr(tempfile, 'TemporaryDirectory', forbidden)

    class Source:
        # read 텍스트 작업을 수행함
        def read_text(self, encoding):
            return 'A **bold** paragraph'

        # Source 인스턴스의 문자열 표현을 반환함
        def __str__(self):
            return 'source.md'

    document = MarkdownParser().parse(Source())
    assert document.source_format == 'md' and document.source_path == 'source.md'
    assert all(block.source_ref.source_format == 'md' for block in document.iter_blocks())
