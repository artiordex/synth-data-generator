# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: html_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/html_parser.py
# 목적: HTML 웹 문서를 분석하여 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Offline semantic HTML parser; scripts and external resources are not executed."""
import base64
from dataclasses import replace
from math import isfinite
import re
from lxml import html, etree
from .common import check_table_size, image_from_bytes, table_source_refs
from ..core.source_ref import SourceRef
from ..core.enums import UnderlineStyle, StrikeStyle, ParagraphAlign
from ..core.ir import DocumentIR, SectionIR, ParagraphIR, TextRunIR, TableIR, TableCellIR, LineBreakIR, ConversionWarning, TabIR, FieldIR, HeaderFooterIR, UnsupportedRecordIR


INLINE = (TextRunIR, TabIR, LineBreakIR, FieldIR)


# css 작업을 수행함
def _css(node):
    try:
        import tinycss2
    except ImportError:
        return {}
    return {item.lower_name: tinycss2.serialize(item.value).strip()
            for item in tinycss2.parse_declaration_list(node.get('style', ''), skip_comments=True, skip_whitespace=True)
            if item.type == 'declaration'}


# points 작업을 수행함
def _points(value):
    match = re.fullmatch(r'([+\-]?(?:\d+(?:\.\d*)?|\.\d+))(pt|px)?', value or '')
    if not match:
        return None
    number = float(match[1]) * (0.75 if match[2] in {'px', None} else 1)
    return number if isfinite(number) and number >= 0 else None


# 텍스트 작업을 수행함
def _text(text, ref, options):
    values = []
    for index, part in enumerate(text.split('\t')):
        if index:
            values.append(TabIR(source_ref=ref))
        if part:
            values.append(TextRunIR(part, source_ref=ref, **options))
    return values


# 블록 목록 작업을 수행함
def _blocks(children, ref, *, empty=False):
    blocks, inline = [], []
    for child in children:
        if isinstance(child, INLINE):
            inline.append(child)
        else:
            if inline:
                blocks.append(ParagraphIR(inlines=inline, source_ref=ref))
                inline = []
            blocks.append(child)
    if inline or (empty and not blocks):
        blocks.append(ParagraphIR(inlines=inline, source_ref=ref))
    return blocks


# options 작업을 실행함
def _run_options(node, inherited, css):
    options = dict(inherited)
    tag = node.tag.lower()
    if tag in {'b', 'strong'}:
        options['bold'] = True
    if tag in {'i', 'em'}:
        options['italic'] = True
    if tag in {'sup', 'sub'}:
        options.update(superscript=tag == 'sup', subscript=tag == 'sub')
    if tag == 'u':
        options['underline'] = UnderlineStyle.SINGLE
    if 'font-weight' in css:
        options['bold'] = css['font-weight'] in {'bold', 'bolder', '600', '700', '800', '900'}
    if 'font-style' in css:
        options['italic'] = css['font-style'] in {'italic', 'oblique'}
    if css.get('vertical-align') in {'super', 'sub', 'baseline'}:
        options.update(superscript=css['vertical-align'] == 'super', subscript=css['vertical-align'] == 'sub')
    decoration = css.get('text-decoration-line', css.get('text-decoration', ''))
    if 'underline' in decoration:
        style = css.get('text-decoration-style', 'solid')
        options['underline'] = UnderlineStyle({'solid': 'single'}.get(style, style)) if style in {'solid', 'double', 'dotted', 'dashed', 'wavy'} else UnderlineStyle.SINGLE
    if 'line-through' in decoration or tag in {'s', 'strike', 'del'}:
        options['strike'] = StrikeStyle.DOUBLE if css.get('text-decoration-style') == 'double' else StrikeStyle.SINGLE
    for css_key, option in [('font-size', 'size_pt'), ('letter-spacing', 'letter_spacing_pt')]:
        value = _points(css.get(css_key))
        if value is not None:
            options[option] = value
    for css_key, option in [('color', 'color_hex'), ('background-color', 'bg_color_hex')]:
        if re.fullmatch(r'#[0-9a-fA-F]{6}', css.get(css_key, '')):
            options[option] = css[css_key][1:]
    if node.get('lang'):
        options['language'] = node.get('lang')
    return options


class HtmlParser:
    # parse 작업을 수행함
    def parse(self, path):
        return self.parse_content(path.read_bytes(), source_path=str(path))

    # content 데이터를 분석하여 파싱함
    def parse_content(self, content, *, source_path=None, source_format='html'):
        """Parse in memory; Markdown callers need no temporary files."""
        root = html.fromstring(content, parser=html.HTMLParser(no_network=True))
        document = DocumentIR(source_format=source_format, source_path=source_path,
                              sections=[SectionIR(source_ref=SourceRef(source_format, section_no=1))])
        try:
            import tinycss2
        except ImportError:
            document.warnings.append(ConversionWarning('HTML_CSS_UNAVAILABLE', 'Optional tinycss2 is unavailable; inline CSS is not mapped.'))
        options, styles, section_numbers = {}, {}, {}
        section_count = 0
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            parent = node.getparent()
            styles[node] = _css(node)
            options[node] = _run_options(node, options.get(parent, {}), styles[node])
            if node.tag.lower() == 'section':
                section_count += 1
                section_numbers[node] = section_count
            else:
                section_numbers[node] = section_numbers.get(parent, 1)
        mapped = {}
        for node in reversed(list(root.iter())):
            if not isinstance(node.tag, str):
                continue
            tag = node.tag.lower()
            ref = SourceRef(source_format, section_no=section_numbers[node], xml_path=root.getroottree().getpath(node))
            children = []
            if node.text is not None:
                children.extend(_text(node.text, ref, options[node]))
            for child in node:
                children.extend(mapped.get(child, []))
                if child.tail is not None:
                    children.extend(_text(child.tail, ref, options[node]))
            if tag in {'script', 'style', 'head', 'svg'}:
                mapped[node] = []
            elif node.get('data-field-type') is not None:
                cached = ''.join(item.text if isinstance(item, TextRunIR) else '\t' if isinstance(item, TabIR)
                                 else '\n' if isinstance(item, LineBreakIR) else '' for item in children)
                mapped[node] = [FieldIR(node.get('data-field-type'), instruction=node.get('data-field-instruction'),
                                       cached_text=cached, source_ref=ref)]
            elif tag == 'br':
                mapped[node] = [LineBreakIR(source_ref=ref)]
            elif tag == 'img':
                try:
                    source = node.get('src', '')
                    metadata, encoded = source.split(',', 1)
                    if not metadata.lower().startswith('data:image/') or not metadata.lower().endswith(';base64'):
                        raise ValueError('Only embedded base64 images are mapped')
                    if len(encoded) > 90 * 1024 ** 2:
                        raise ValueError('Image exceeds size limit')
                    data = base64.b64decode(encoded, validate=True)
                    width = _points(styles[node].get('width', node.get('width')))
                    height = _points(styles[node].get('height', node.get('height')))
                    if width is None or height is None:
                        raise ValueError('Explicit image dimensions are required')
                    mapped[node] = [image_from_bytes(data, width, height, ref)]
                except (OSError, ValueError):
                    mapped[node] = [UnsupportedRecordIR(0, 0, etree.tostring(node), source_ref=ref)]
                    document.warnings.append(ConversionWarning('HTML_IMAGE_UNRESOLVED',
                        'Image reference, format or size is unsupported; no resource was fetched.', source_ref=ref))
            elif tag in {'td', 'th'}:
                blocks = _blocks(children, ref)
                row_span, col_span = int(node.get('rowspan', 1)), int(node.get('colspan', 1))
                if row_span < 1 or col_span < 1:
                    raise ValueError('Unsupported nonpositive HTML span')
                check_table_size(row_span, col_span)
                mapped[node] = [TableCellIR(0, 0, row_span=row_span, col_span=col_span, content=blocks, source_ref=ref)]
            elif tag == 'tr':
                mapped[node] = [[c for c in children if isinstance(c, TableCellIR)]]
            elif tag == 'table':
                rows, occupied = [], set()
                for row_no, cells in enumerate(c for c in children if isinstance(c, list)):
                    col = 0
                    for cell in cells:
                        while (row_no, col) in occupied:
                            col += 1
                        cell.row_index, cell.col_index = row_no, col
                        check_table_size(row_no + cell.row_span, col + cell.col_span)
                        for r in range(row_no, row_no + cell.row_span):
                            for c in range(col, col + cell.col_span):
                                if (r, c) in occupied:
                                    raise ValueError('HTML table merge conflict')
                                occupied.add((r, c))
                        col += cell.col_span
                    rows.append(cells)
                table = TableIR(rows=rows, source_ref=ref)
                table_source_refs(table, node, 'table')
                mapped[node] = [table]
            elif tag in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
                blocks = _blocks(children, ref, empty=True)
                for block in blocks:
                    if isinstance(block, ParagraphIR):
                        alignment = styles[node].get('text-align', 'left')
                        if alignment in ParagraphAlign._value2member_map_:
                            block.align = ParagraphAlign(alignment)
                        if tag != 'p':
                            block.heading_level = int(tag[1])
                mapped[node] = blocks
            elif tag in {'header', 'footer'}:
                mapped[node] = [(tag, HeaderFooterIR(_blocks(children, ref), source_ref=ref))]
            elif tag == 'section':
                section = SectionIR(source_ref=ref)
                section.page_width_pt = _points(styles[node].get('width'))
                for item in children:
                    if isinstance(item, tuple) and item[0] in {'header', 'footer'}:
                        setattr(section, item[0], item[1])
                    else:
                        section.elements.extend(_blocks([item], ref))
                mapped[node] = [section]
            else:
                mapped[node] = children
        document.sections = []
        pending = []
        for item in mapped[root]:
            if isinstance(item, SectionIR):
                if pending:
                    document.sections.append(SectionIR(elements=_blocks(pending, SourceRef(source_format))))
                    pending = []
                document.sections.append(item)
            elif isinstance(item, tuple) and item[0] in {'header', 'footer'}:
                if not document.sections:
                    document.sections.append(SectionIR())
                setattr(document.sections[-1], item[0], item[1])
            else:
                pending.append(item)
        if pending or not document.sections:
            document.sections.append(SectionIR(elements=_blocks(pending, SourceRef(source_format))))
        document.warnings.append(ConversionWarning('HTML_PARTIAL', 'Inline styles and embedded raster images are mapped; external CSS, drawings and browser layout are not fully mapped.'))
        document.intern_resources()
        return document
