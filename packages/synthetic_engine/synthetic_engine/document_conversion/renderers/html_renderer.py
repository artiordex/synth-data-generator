# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: html_renderer.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/html_renderer.py
# 목적: IR 트리를 표준 반응형 HTML 페이지로 렌더링함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Standalone HTML with explicit CSS fallbacks for non-browser document features."""
import base64
import json
import re
from html import escape
from urllib.parse import urlsplit

from lxml import etree

from ..core.ir import (
    ConversionWarning, FieldIR, HyperlinkIR, ImageIR, LineBreakIR, MathIR,
    ParagraphIR, TableIR, TabIR, TextRunIR,
)
from ..core.capabilities import TargetCapabilities


MATHML_NAMESPACE = 'http://www.w3.org/1998/Math/MathML'
MATHML_ELEMENTS = {
    'math', 'maction', 'menclose', 'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts',
    'mn', 'mo', 'mover', 'mpadded', 'mphantom', 'mprescripts', 'mroot', 'mrow',
    'ms', 'mspace', 'msqrt', 'mstyle', 'msub', 'msubsup', 'msup', 'mtable', 'mtd',
    'mtext', 'mtr', 'munder', 'munderover', 'none', 'semantics',
}
MATHML_ATTRIBUTES = {
    'accent', 'accentunder', 'columnalign', 'columnspan', 'denomalign', 'depth',
    'display', 'displaystyle', 'fence', 'height', 'linethickness', 'lspace',
    'mathbackground', 'mathcolor', 'mathsize', 'mathvariant', 'maxsize', 'minsize',
    'movablelimits', 'notation', 'numalign', 'rowalign', 'rowspan', 'rspace',
    'scriptlevel', 'separator', 'stretchy', 'symmetric', 'voffset', 'width',
}


def _color(value):
    value = value.lstrip('#')
    return '#' + value if re.fullmatch(r'[0-9a-fA-F]{6}', value) else '#000000'


def _style(value):
    return escape(value, quote=True)


def _unmapped(warnings, source, feature):
    warnings.append(ConversionWarning(
        'HTML_UNMAPPED_CONTENT', f'HTML renderer cannot fully map {feature}.',
        source_ref=getattr(source, 'source_ref', None), feature=feature,
    ))


def _safe_mathml(value):
    """Return a browser-native MathML fragment after rejecting active markup."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = etree.fromstring(value.encode('utf-8'), parser=parser)
    if etree.QName(root).namespace != MATHML_NAMESPACE or etree.QName(root).localname != 'math':
        raise ValueError('MathML root must be a namespaced math element')
    for node in root.iter():
        if not isinstance(node.tag, str):
            raise ValueError('MathML comments and processing instructions are unsupported')
        qname = etree.QName(node)
        if qname.namespace != MATHML_NAMESPACE or qname.localname not in MATHML_ELEMENTS:
            raise ValueError(f'Unsupported MathML element: {qname.localname}')
        for name in node.attrib:
            attribute = etree.QName(name)
            if attribute.namespace not in {None, MATHML_NAMESPACE}:
                raise ValueError('Namespaced MathML attributes are unsupported')
            if attribute.localname not in MATHML_ATTRIBUTES:
                raise ValueError(f'Unsupported MathML attribute: {attribute.localname}')
    return etree.tostring(root, encoding='unicode', with_tail=False)


def _fallback_image(source, resources):
    resource_id = source.fallback_image_resource_id
    if not resource_id or resource_id not in resources:
        return ''
    metadata = resources.get_metadata(resource_id)
    mime_type = next((value for value in metadata.mime_types if value.startswith('image/')), None)
    if mime_type is None:
        return ''
    encoded = base64.b64encode(resources.get(resource_id)).decode('ascii')
    return (
        '<img class="document-math__fallback-image" '
        f'alt="검토용 원본 수식 이미지" src="data:{escape(mime_type, quote=True)};base64,{encoded}">'
    )


def _math(source, warnings, resources):
    """Render MathIR without hiding recognition or presentation failures."""
    render_failure = None
    presentation = ''
    if source.mathml:
        try:
            presentation = '<span class="document-math__mathml">' + _safe_mathml(source.mathml) + '</span>'
        except (ValueError, etree.XMLSyntaxError) as exc:
            render_failure = f'MathML rendering failed: {exc}'
            warnings.append(ConversionWarning(
                'HTML_MATH_RENDER_FAILED', render_failure,
                source_ref=source.source_ref, feature='math',
            ))
    if not presentation and source.latex:
        presentation = (
            '<code class="document-math__latex" data-math-notation="latex">'
            + escape(source.latex) + '</code>'
        )
    if not presentation and source.source_expression:
        presentation = '<code class="document-math__source">' + escape(source.source_expression) + '</code>'
    if not presentation and source.ocr_candidates:
        presentation = '<code class="document-math__source">' + escape(source.ocr_candidates[0]) + '</code>'
    if not presentation:
        resource = source.source_resource_id or source.fallback_image_resource_id
        presentation = (
            '<span class="document-math__preserved">원본 수식 콘텐츠 보존됨'
            + (f' · {escape(resource[:12])}…' if resource else '') + '</span>'
        )

    needs_review = source.needs_review or render_failure is not None
    reason = source.failure_reason or render_failure
    confidence = (
        f'<span class="document-math__confidence">신뢰도 {source.confidence * 100:.1f}%</span>'
        if source.confidence is not None else ''
    )
    review = ''
    if needs_review:
        review = (
            '<span class="document-math__review" role="status">'
            '<strong>수식 검토 필요</strong>'
            + (f'<span>{escape(reason)}</span>' if reason else '')
            + confidence
            + '</span>'
        )
    elif confidence:
        review = '<span class="document-math__meta">' + confidence + '</span>'

    source_ref = source.source_ref
    attributes = [
        f'data-math-display="{source.display_mode}"',
        f'data-needs-review="{str(needs_review).lower()}"',
    ]
    if source.source_syntax:
        attributes.append(f'data-source-syntax="{escape(source.source_syntax, quote=True)}"')
    if source_ref is not None:
        attributes.append(f'data-source-format="{escape(source_ref.source_format, quote=True)}"')
        if source_ref.page_no is not None:
            attributes.append(f'data-source-page="{source_ref.page_no}"')
        if source_ref.object_id:
            attributes.append(f'data-source-object="{escape(source_ref.object_id, quote=True)}"')
    if source.source_resource_id:
        attributes.append(f'data-source-resource="{source.source_resource_id}"')
    tag = 'span' if source.display_mode == 'inline' else 'div'
    class_name = f'document-math document-math--{source.display_mode}'
    image = _fallback_image(source, resources)
    return (
        f'<{tag} class="{class_name}" {" ".join(attributes)} role="math">'
        f'<span class="document-math__content">{presentation}</span>{image}{review}</{tag}>'
    )


def _inlines(inlines, warnings, resources):
    result = []
    stack = [('inline', item) for item in reversed(inlines)]
    while stack:
        kind, item = stack.pop()
        if kind == 'literal':
            result.append(item)
        elif isinstance(item, TextRunIR):
            style = (f'font-size:{item.size_pt}pt;letter-spacing:{item.letter_spacing_pt}pt;'
                     f'font-weight:{"bold" if item.bold else "normal"};'
                     f'font-style:{"italic" if item.italic else "normal"};')
            families = [name for name in (item.font_family_en, item.font_family_ko) if name]
            if families:
                style += 'font-family:' + ','.join(json.dumps(name, ensure_ascii=True) for name in families) + ';'
            if item.color_hex:
                style += f'color:{_color(item.color_hex)};'
            if item.bg_color_hex:
                style += f'background-color:{_color(item.bg_color_hex)};'
            if item.superscript or item.subscript:
                style += f'vertical-align:{"sub" if item.subscript else "super"};'
            if item.scale_percent != 100:
                # CSS transforms scale glyphs but leave the original advance width.
                style += f'display:inline-block;transform:scaleX({item.scale_percent / 100});transform-origin:left center;'
            attrs = f' lang="{escape(item.language, quote=True)}"' if item.language else ''
            if item.scale_percent != 100:
                attrs += ' data-conversion-loss="font-scaling-layout"'
            text = escape(item.text)
            if item.underline.value != 'none':
                decoration = {'single': 'solid', 'wavy': 'wavy'}.get(item.underline.value, item.underline.value)
                text = f'<span style="text-decoration-line:underline;text-decoration-style:{decoration}">{text}</span>'
            if item.strike.value != 'none':
                decoration = 'double' if item.strike.value == 'double' else 'solid'
                text = f'<span style="text-decoration-line:line-through;text-decoration-style:{decoration}">{text}</span>'
            result.append(f'<span style="{_style(style)}"{attrs}>{text}</span>')
        elif isinstance(item, HyperlinkIR):
            # Keep dangerous schemes inert while preserving their text children.
            target = item.target
            scheme = urlsplit(target.strip()).scheme.lower()
            safe = scheme in ('', 'http', 'https', 'mailto', 'tel') and not any(ord(c) < 32 for c in target)
            if not safe:
                _unmapped(warnings, item, 'hyperlink-target')
            title = f' title="{escape(item.title, quote=True)}"' if item.title else ''
            result.append(f'<a href="{escape(target, quote=True)}"{title}>' if safe else '<span data-conversion-loss="hyperlink-target">')
            stack.append(('literal', '</a>' if safe else '</span>'))
            stack.extend(('inline', child) for child in reversed(item.inlines))
        elif isinstance(item, MathIR):
            result.append(_math(item, warnings, resources))
        elif isinstance(item, FieldIR):
            _unmapped(warnings, item, 'dynamic-field:' + item.field_type)
            result.append(f'<span data-field-type="{escape(item.field_type, quote=True)}" '
                          f'data-conversion-loss="dynamic-field">{escape(item.cached_text or "")}</span>')
        elif isinstance(item, TabIR):
            if item.position_pt is not None:
                _unmapped(warnings, item, 'explicit-tab-stop')
            result.append('&#9;')
        elif isinstance(item, LineBreakIR):
            result.append('<br>')
        else:
            _unmapped(warnings, item, type(item).__name__)
    return ''.join(result)


def _paragraph(source, warnings, resources):
    if source.list_type is not None or source.list_level is not None:
        _unmapped(warnings, source, 'list-numbering')
    alignment = 'justify' if source.align.value == 'distribute' else source.align.value
    style = (f'white-space:pre-wrap;text-align:{alignment};'
             f'line-height:{source.line_spacing_percent / 100};'
             f'margin:{source.space_before_pt}pt 0 {source.space_after_pt}pt {source.indent_pt}pt;'
             f'text-indent:{-source.hanging_pt}pt;')
    if source.align.value == 'distribute':
        style += 'text-align-last:justify;text-justify:inter-character;'
    if source.page_break_before:
        style += 'break-before:page;page-break-before:always;'
    if source.keep_with_next:
        style += 'break-after:avoid;page-break-after:avoid;'
    if source.keep_lines_together:
        style += 'break-inside:avoid;page-break-inside:avoid;'
    tag = f'h{source.heading_level}' if source.heading_level in range(1, 7) else 'p'
    return f'<{tag} style="{_style(style)}">{_inlines(source.inlines, warnings, resources)}</{tag}>'


def _cell(source, warnings):
    alignment = 'middle' if source.vertical_align.value == 'center' else source.vertical_align.value
    style = f'vertical-align:{alignment};white-space:pre-wrap;position:relative;text-align:left;font-weight:normal;'
    style += 'padding:' + ' '.join(f'{value}pt' for value in source.padding_pt) + ';'
    if source.width_pt is not None:
        style += f'width:{source.width_pt}pt;'
    minimum_width = max(72.0, min(360.0, (source.width_pt or 72.0)))
    style += f'min-width:{minimum_width}pt;max-width:36rem;word-break:normal;overflow-wrap:break-word;'
    if source.height_pt is not None:
        style += f'height:{source.height_pt}pt;'
    if source.bg_color_hex:
        style += f'background-color:{_color(source.bg_color_hex)};'
    diagonals = []
    for side, border in source.borders.items():
        border_style = 'dashed' if border.style.value == 'dash_dot' else border.style.value
        if side in ('top', 'right', 'bottom', 'left', 'start', 'end'):
            if border.style.value == 'dash_dot':
                _unmapped(warnings, source, 'dash-dot-cell-border')
            css_side = {'start': 'inline-start', 'end': 'inline-end'}.get(side, side)
            style += f'border-{css_side}:{border.width_pt}pt {border_style} {_color(border.color_hex)};'
        elif side in ('slash', 'backslash', 'diagonal_up', 'diagonal_down', 'tr2bl', 'tl2br'):
            if border.style.value == 'none' or border.width_pt <= 0:
                continue
            up = side in ('slash', 'diagonal_up', 'tr2bl')
            dash = {'dotted': '1 2', 'dashed': '5 3', 'dash_dot': '5 3 1 3'}.get(border.style.value)
            attrs = f' stroke-dasharray="{dash}"' if dash else ''
            # SVG gives a real corner-to-corner stroke at any cell aspect ratio.
            # Double diagonals are currently rendered as one stroke and marked.
            loss = ' data-conversion-loss="double-diagonal-border"' if border.style.value == 'double' else ''
            if loss:
                _unmapped(warnings, source, 'double-diagonal-border')
            diagonals.append(
                f'<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true"{loss} '
                'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none" '
                'viewBox="0 0 100 100" preserveAspectRatio="none">'
                f'<line x1="0" y1="{100 if up else 0}" x2="100" y2="{0 if up else 100}" '
                f'stroke="{_color(border.color_hex)}" stroke-width="{border.width_pt * 96 / 72}" '
                f'vector-effect="non-scaling-stroke"{attrs}/></svg>')
        else:
            _unmapped(warnings, source, 'cell-border:' + side)
    return style, ''.join(diagonals)


class HtmlRenderer:
    # Pagination/repeating page furniture and exact horizontal scaling cannot
    # be guaranteed by a standalone HTML document across browser print engines.
    capabilities = TargetCapabilities(
        supports_nested_tables=True, supports_rowspan=True, supports_colspan=True,
        supports_letter_spacing=True,
    )

    def render(self, document, output_path):
        result = ['<!doctype html><html><head><meta charset="utf-8"><style>'
                  'html,body{max-width:100%;overflow-x:hidden}body{margin:0;min-width:0}'
                  'section,section>div{min-width:0;max-width:100%}'
                  'thead{display:table-header-group}tfoot{display:table-footer-group}'
                  'table{border-collapse:collapse}'
                  '.document-table-scroll{box-sizing:border-box;display:block;max-width:100%;overflow-x:auto;'
                  'overflow-y:hidden;overscroll-behavior-inline:contain;-webkit-overflow-scrolling:touch}'
                  '.document-table{table-layout:auto;min-width:100%}'
                  '.document-table__cell{word-break:normal;overflow-wrap:break-word}'
                  '.document-table__cell>p{min-width:0;max-width:100%}'
                  '.document-math{box-sizing:border-box;max-width:100%;gap:.45rem;align-items:center;'
                  'font-family:"Cambria Math","STIX Two Math","Noto Sans Math",serif;vertical-align:middle}'
                  '.document-math--inline{display:inline-flex;margin-inline:.12em}'
                  '.document-math--display{display:flex;width:100%;margin:.65rem 0;padding:.5rem;flex-wrap:wrap}'
                  '.document-math__content{display:inline-flex;min-width:0;max-width:100%;overflow-x:auto;overflow-y:hidden}'
                  '.document-math__latex,.document-math__source{box-sizing:border-box;display:inline-block;'
                  'max-width:100%;overflow-x:auto;white-space:nowrap;word-break:normal;overflow-wrap:normal;'
                  'font:inherit;background:transparent;border:0;padding:.1em .2em}'
                  '.document-math__mathml{display:inline-block;max-width:100%;overflow-x:auto}'
                  '.document-math__fallback-image{display:block;max-width:min(100%,36rem);height:auto;object-fit:contain}'
                  '.document-math__review{display:inline-flex;max-width:100%;flex-wrap:wrap;gap:.25rem .45rem;'
                  'align-items:center;padding:.25rem .45rem;border:1px solid #d97706;border-radius:.4rem;'
                  'background:#fffbeb;color:#92400e;font:600 .75rem/1.35 system-ui,sans-serif}'
                  '.document-math__confidence,.document-math__meta{white-space:nowrap}'
                  '@media print{section+section{break-before:page}}'
                  '@media(max-width:640px){.document-math--display{align-items:flex-start;flex-direction:column}'
                  '.document-table__cell{min-width:72pt!important;max-width:28rem}.document-math__review{font-size:.7rem}}'
                  '</style></head><body>']
        stack = []
        for section in reversed(document.sections):
            style = 'box-sizing:border-box;'
            if section.page_width_pt is not None:
                style += f'width:{section.page_width_pt}pt;max-width:100%;'
            style += ('padding:' + ' '.join(f'{value}pt' for value in (
                section.margin_top_pt, section.margin_right_pt,
                section.margin_bottom_pt, section.margin_left_pt)) + ';')
            stack.append(('literal', '</section>'))
            if section.footer is not None:
                stack.append(('literal', '</footer>'))
                stack.extend(('block', b) for b in reversed(section.footer.elements))
                stack.append(('literal', f'<footer data-conversion-loss="repeating-footer" style="margin-top:{section.footer_distance_pt}pt">'))
            stack.append(('literal', '</div>'))
            stack.extend(('block', b) for b in reversed(section.elements))
            stack.append(('literal', f'<div style="column-count:{section.column_count};column-gap:{section.column_gap_pt}pt">'))
            if section.header is not None:
                stack.append(('literal', '</header>'))
                stack.extend(('block', b) for b in reversed(section.header.elements))
                stack.append(('literal', f'<header data-conversion-loss="repeating-header" style="margin-bottom:{section.header_distance_pt}pt">'))
            stack.append(('literal', f'<section style="{_style(style)}">'))
        while stack:
            kind, value = stack.pop()
            if kind == 'literal':
                result.append(value)
            elif isinstance(value, ParagraphIR):
                result.append(_paragraph(value, document.warnings, document.resources))
            elif isinstance(value, MathIR):
                result.append(_math(value, document.warnings, document.resources))
            elif isinstance(value, TableIR):
                style = 'border-collapse:collapse;table-layout:auto;min-width:100%;'
                width = value.total_width_pt or sum(value.column_widths_pt)
                if width:
                    style += f'width:{width}pt;'
                style += {'left': 'margin-right:auto;', 'center': 'margin-left:auto;margin-right:auto;',
                          'right': 'margin-left:auto;'}[value.alignment.value]
                result.append(
                    '<div class="document-table-scroll" role="region" tabindex="0" '
                    'aria-label="가로로 스크롤 가능한 문서 표" '
                    'style="max-width:100%;overflow-x:auto;overflow-y:hidden">'
                    f'<table class="document-table" style="{_style(style)}">'
                )
                if value.caption is not None:
                    result.append('<caption>' + _paragraph(
                        value.caption, document.warnings, document.resources
                    ) + '</caption>')
                if value.column_widths_pt:
                    result.append('<colgroup>' + ''.join(f'<col style="width:{w}pt">' for w in value.column_widths_pt) + '</colgroup>')
                tasks = []
                header_count = min(max(0, value.repeat_header_rows), len(value.rows))
                # HTML forbids a rowspan crossing row-group boundaries.
                crossing = any(c.row_index < header_count < c.row_index + c.row_span
                               for row in value.rows for c in row)
                if crossing:
                    _unmapped(document.warnings, value, 'repeat-header-rowspan-crossing')
                    header_count = 0
                for start, end, group in ((0, header_count, 'thead'), (header_count, len(value.rows), 'tbody')):
                    if start == end:
                        continue
                    tasks.append(('literal', f'<{group}>'))
                    for row in value.rows[start:end]:
                        row_style = 'break-inside:avoid;page-break-inside:avoid;' if value.cant_split else ''
                        tasks.append(('literal', f'<tr style="{row_style}">'))
                        for cell in sorted(row, key=lambda c: c.col_index):
                            cell_style, diagonals = _cell(cell, document.warnings)
                            tag = 'th' if group == 'thead' else 'td'
                            tasks.append(('literal', f'<{tag} class="document-table__cell" rowspan="{cell.row_span}" colspan="{cell.col_span}" style="{_style(cell_style)}">' + diagonals))
                            tasks.extend(('block', child) for child in cell.content)
                            tasks.append(('literal', f'</{tag}>'))
                        tasks.append(('literal', '</tr>'))
                    tasks.append(('literal', f'</{group}>'))
                if crossing:
                    tasks.append(('literal', '<!-- conversion-loss: repeat-header-rowspan-crossing -->'))
                tasks.append(('literal', '</table></div>'))
                stack.extend(reversed(tasks))
            elif isinstance(value, ImageIR):
                if value.opacity != 1 or value.rotation_deg != 0:
                    _unmapped(document.warnings, value, 'image-opacity-or-rotation')
                encoded = base64.b64encode(value.image_bytes).decode('ascii')
                result.append(f'<img alt="" src="data:{escape(value.mime_type, quote=True)};base64,{encoded}" style="width:{value.width_pt}pt;height:{value.height_pt}pt">')
                if value.caption is not None:
                    result.append(_paragraph(value.caption, document.warnings, document.resources))
            else:
                _unmapped(document.warnings, value, type(value).__name__)
                result.append('<aside data-conversion-loss="unsupported">Unsupported source object</aside>')
        result.append('</body></html>')
        output_path.write_text(''.join(result), encoding='utf-8')
        return output_path
