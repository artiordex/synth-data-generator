# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: docx_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/docx_parser.py
# 목적: DOCX 워드 문서를 분석하여 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Read Word paragraphs and logical table anchors through safe package XML."""
from dataclasses import replace
from contextlib import nullcontext
from pathlib import PurePosixPath
from lxml import etree

from .package import DocumentPackage
from .common import check_table_size, image_from_bytes, table_source_refs
from ..core.ir import DocumentIR, SectionIR, ParagraphIR, TextRunIR, TabIR, LineBreakIR, TableIR, TableCellIR, ConversionWarning, UnsupportedRecordIR, FieldIR, HeaderFooterIR, HyperlinkIR, BorderIR
from ..core.source_ref import SourceRef
from ..core.enums import BorderStyle, ImagePlacement, UnderlineStyle
from ..geometry.table_geometry import validate_spans

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


# val 작업을 수행함
def val(node, tag, default=None):
    child = node.find(f'{{{W}}}{tag}') if node is not None else None
    return child.get(f'{{{W}}}val', default) if child is not None else default


# twips 작업을 수행함
def _twips(node, default=None):
    if node is None:
        return default
    value = node.get(f'{{{W}}}w')
    try:
        return float(value) / 20 if value is not None else default
    except ValueError:
        return default


# 셀 borders 작업을 수행함
def _cell_borders(props):
    if props is None:
        return {}
    container = props.find(f'{{{W}}}tcBorders')
    if container is None:
        return {}
    names = {'top', 'bottom', 'left', 'right', 'start', 'end', 'insideH', 'insideV',
             'tr2bl', 'tl2br'}
    styles = {'nil': BorderStyle.NONE, 'none': BorderStyle.NONE,
              'single': BorderStyle.SOLID, 'double': BorderStyle.DOUBLE,
              'dotted': BorderStyle.DOTTED, 'dashed': BorderStyle.DASHED,
              'dotDash': BorderStyle.DASH_DOT}
    borders = {}
    for child in container:
        if not isinstance(child.tag, str):
            continue
        name = child.tag.removeprefix('{' + W + '}')
        if name not in names:
            continue
        style = styles.get(child.get(f'{{{W}}}val', 'single'), BorderStyle.SOLID)
        try:
            width = float(child.get(f'{{{W}}}sz', 0)) / 8
        except ValueError:
            width = 0.0
        borders[name] = BorderIR(style, width, child.get(f'{{{W}}}color', '000000'))
    return borders


# 셀 padding 작업을 수행함
def _cell_padding(props):
    if props is None:
        return (0, 0, 0, 0)
    margins = props.find(f'{{{W}}}tcMar')
    if margins is None:
        return (0, 0, 0, 0)
    return tuple(_twips(margins.find(f'{{{W}}}{side}'), 0) or 0 for side in ('top', 'right', 'bottom', 'left'))


# cached 텍스트 작업을 수행함
def _cached_text(items):
    return ''.join(item.text if isinstance(item, TextRunIR) else '\t' if isinstance(item, TabIR)
                   else '\n' if isinstance(item, LineBreakIR) else item.cached_text or ''
                   if isinstance(item, FieldIR) else _cached_text(item.inlines)
                   if isinstance(item, HyperlinkIR) else '' for item in items)


# field 작업을 수행함
def _field(instruction, cached, ref):
    command = instruction.strip().split()
    return FieldIR(command[0].upper() if command else 'UNKNOWN', instruction=instruction,
                   cached_text=_cached_text(cached), source_ref=ref)


# fields 작업을 수행함
def _fields(items, document, ref):
    """Pair complex Word field controls while retaining cached presentation."""
    result, stack = [], []
    for item in items:
        if isinstance(item, tuple) and item[0] == 'field':
            kind, value = item[1:]
            if kind == 'begin':
                stack.append(['', [], False])
            elif stack and kind == 'instruction':
                stack[-1][0] += value
            elif stack and kind == 'separate':
                stack[-1][2] = True
            elif stack and kind == 'end':
                instruction, cached, _ = stack.pop()
                field = _field(instruction, cached, ref)
                (stack[-1][1] if stack else result).append(field)
            else:
                document.warnings.append(ConversionWarning('DOCX_FIELD_UNBALANCED',
                    'Unpaired field control retained in source XML.', source_ref=ref))
        elif stack:
            if stack[-1][2]:
                stack[-1][1].append(item)
        else:
            result.append(item)
    if stack:
        document.warnings.append(ConversionWarning('DOCX_FIELD_UNBALANCED',
            'Field crosses an unsupported boundary; cached text is retained.', source_ref=ref))
        for _, cached, _ in stack:
            result.extend(cached)
    return result


class DocxParser:
    # parse 작업을 수행함
    def parse(self, path, *, _part='word/document.xml', _root_tag='document', _package=None):
        document = DocumentIR(source_format='docx', source_path=str(path), sections=[SectionIR()])
        with (DocumentPackage(path) if _package is None else nullcontext(_package)) as package:
            root = package.xml(_part)
            if root.tag != f'{{{W}}}{_root_tag}':
                raise ValueError('Not a WordprocessingML document')
            for name in sorted(package.names) if _root_tag == 'document' else ():
                if not name.endswith('/'):
                    document.resources.add(package.read(name))
            relationships = {}
            part_path = PurePosixPath(_part)
            rels_path = str(part_path.parent / '_rels' / (part_path.name + '.rels'))
            if rels_path in package.names:
                for relation in package.xml(rels_path).findall(f'{{{REL}}}Relationship'):
                    identifier = relation.get('Id')
                    if not identifier or identifier in relationships:
                        raise ValueError('Missing or duplicate Word relationship identifier')
                    relationships[identifier] = relation
            document.sections[0].source_ref = SourceRef('docx', section_no=1, xml_path=_part)
            mapped = {}
            for node in reversed(list(root.iter())):
                if not isinstance(node.tag, str):
                    continue
                tag = node.tag.removeprefix('{' + W + '}')
                children = [v for child in node for v in mapped.get(child, [])]
                ref = SourceRef('docx', section_no=1, xml_path=_part + ':' + root.getroottree().getpath(node))
                if tag == 'r':
                    props = node.find(f'{{{W}}}rPr')
                    options = {'size_pt': float(val(props, 'sz', 20))/2,
                               'bold': val(props, 'b', 'missing') not in {'missing', '0', 'false'},
                               'italic': val(props, 'i', 'missing') not in {'missing', '0', 'false'},
                               'superscript': val(props, 'vertAlign') == 'superscript',
                               'subscript': val(props, 'vertAlign') == 'subscript'}
                    underline = val(props, 'u', 'none')
                    underline = {'dash': 'dashed', 'wave': 'wavy'}.get(underline, underline)
                    options['underline'] = (UnderlineStyle(underline) if underline in UnderlineStyle._value2member_map_
                                            else UnderlineStyle.SINGLE)
                    # Empty b/i elements mean true.
                    for key, xml in [('bold', 'b'), ('italic', 'i')]:
                        if props is not None and props.find(f'{{{W}}}{xml}') is not None:
                            options[key] = val(props, xml, '1') not in {'0', 'false'}
                    values = []
                    for child in node:
                        if not isinstance(child.tag, str):
                            continue
                        child_ref = replace(ref, xml_path=_part + ':' + root.getroottree().getpath(child))
                        if child.tag == f'{{{W}}}t':
                            values.append(TextRunIR(child.text or '', source_ref=child_ref, **options))
                        elif child.tag == f'{{{W}}}tab':
                            values.append(TabIR(source_ref=child_ref))
                        elif child.tag in {f'{{{W}}}br', f'{{{W}}}cr'}:
                            values.append(LineBreakIR(source_ref=child_ref))
                        elif child.tag == f'{{{W}}}noBreakHyphen':
                            values.append(TextRunIR('\u2011', source_ref=child_ref, **options))
                        elif child.tag == f'{{{W}}}softHyphen':
                            values.append(TextRunIR('\u00ad', source_ref=child_ref, **options))
                        elif child.tag == f'{{{W}}}fldChar':
                            values.append(('field', child.get(f'{{{W}}}fldCharType'), ''))
                        elif child.tag == f'{{{W}}}instrText':
                            values.append(('field', 'instruction', child.text or ''))
                        else:
                            values.extend(mapped.get(child, []))
                    mapped[node] = values
                elif tag == 'p':
                    blocks, inline = [], []
                    for child in _fields(children, document, ref):
                        if isinstance(child, (TextRunIR, TabIR, LineBreakIR, FieldIR, HyperlinkIR)):
                            inline.append(child)
                        else:
                            if inline:
                                blocks.append(ParagraphIR(inlines=inline, source_ref=ref))
                                inline = []
                            blocks.append(child)
                    if inline or not blocks:
                        blocks.append(ParagraphIR(inlines=inline, source_ref=ref))
                    mapped[node] = blocks
                elif tag == 'fldSimple':
                    mapped[node] = [_field(node.get(f'{{{W}}}instr', ''), children, ref)]
                elif tag == 'hyperlink':
                    relationship_id = node.get(f'{{{R}}}id')
                    anchor = node.get(f'{{{W}}}anchor')
                    target = None
                    if relationship_id:
                        relation = relationships.get(relationship_id)
                        if relation is None or relation.get('Type') != R + '/hyperlink':
                            document.warnings.append(ConversionWarning('DOCX_HYPERLINK_UNRESOLVED',
                                'Hyperlink relationship is missing or invalid; link text is retained.', source_ref=ref))
                        else:
                            target = relation.get('Target', '')
                    elif anchor:
                        target = '#' + anchor
                    if target:
                        mapped[node] = [HyperlinkIR(target, [
                            child for child in children
                            if isinstance(child, (TextRunIR, TabIR, LineBreakIR, FieldIR, HyperlinkIR))
                        ], title=node.get(f'{{{W}}}tooltip'), source_ref=ref)]
                    else:
                        mapped[node] = children
                elif tag == 'drawing':
                    try:
                        blips = node.findall(f'.//{{{A}}}blip')
                        if len(blips) != 1:
                            raise ValueError('Unsupported drawing composition')
                        relation = relationships.get(blips[0].get(f'{{{R}}}embed'))
                        if (relation is None or relation.get('TargetMode', 'Internal') != 'Internal'
                                or relation.get('Type') != R + '/image'):
                            raise ValueError('Embedded image relationship is missing')
                        resource = package.resolve(_part, relation.get('Target', ''))
                        extent = node.find(f'.//{{{WP}}}extent')
                        if extent is None:
                            raise ValueError('Image extent is missing')
                        image = image_from_bytes(package.read(resource), float(extent.get('cx')) / 12700,
                                                 float(extent.get('cy')) / 12700, ref)
                        anchor = node.find(f'{{{WP}}}anchor')
                        if anchor is not None:
                            image.placement = (ImagePlacement.BEHIND if anchor.get('behindDoc') in {'1', 'true'}
                                               else ImagePlacement.SQUARE if anchor.find(f'{{{WP}}}wrapSquare') is not None
                                               else ImagePlacement.IN_FRONT)
                        mapped[node] = [image]
                    except (OSError, ValueError, TypeError):
                        mapped[node] = [UnsupportedRecordIR(0, 0, etree.tostring(node), source_ref=ref)]
                        document.warnings.append(ConversionWarning('DOCX_IMAGE_UNRESOLVED',
                            'Drawing reference, format or dimensions are unsupported; source XML is retained.', source_ref=ref))
                elif tag in {'pict', 'object'}:
                    mapped[node] = [UnsupportedRecordIR(0, 0, etree.tostring(node), source_ref=ref)]
                    document.warnings.append(ConversionWarning('DOCX_DRAWING_UNSUPPORTED',
                        'Legacy drawing or embedded object retained without execution.', source_ref=ref))
                elif tag == 'tc':
                    props = node.find(f'{{{W}}}tcPr')
                    merge = props.find(f'{{{W}}}vMerge') if props is not None else None
                    width = _twips(props.find(f'{{{W}}}tcW') if props is not None else None)
                    mapped[node] = [(TableCellIR(0, 0, col_span=int(val(props, 'gridSpan', 1)),
                                     width_pt=width, borders=_cell_borders(props), padding_pt=_cell_padding(props),
                                     content=children, source_ref=ref),
                                     merge.get(f'{{{W}}}val', 'continue') if merge is not None else None)]
                elif tag == 'tr':
                    before = int(val(node.find(f'{{{W}}}trPr'), 'gridBefore', 0))
                    if before < 0:
                        raise ValueError('Invalid Word grid offset')
                    mapped[node] = [(before, [c for c in children if isinstance(c, tuple)])]
                elif tag == 'tbl':
                    rows, active = [], {}
                    raw_rows = [c for c in children if isinstance(c, tuple)]
                    grid = node.find(f'{{{W}}}tblGrid')
                    grid_columns = len(grid.findall(f'{{{W}}}gridCol')) if grid is not None else 0
                    check_table_size(len(raw_rows), grid_columns)
                    column_widths = []
                    if grid is not None:
                        column_widths = [
                            _twips(column, 0) or 0
                            for column in grid.findall(f'{{{W}}}gridCol')
                        ]
                    for r, (before, raw_row) in enumerate(raw_rows):
                        row, column, next_active = [], before, {}
                        for cell, merge in raw_row:
                            if cell.col_span < 1:
                                raise ValueError('Invalid Word grid span')
                            check_table_size(len(raw_rows), max(grid_columns, column + cell.col_span))
                            if grid_columns and column + cell.col_span > grid_columns:
                                raise ValueError('Word cell exceeds declared grid')
                            if merge == 'continue':
                                anchor = active.get(column)
                                if anchor is None or anchor.col_span != cell.col_span:
                                    raise ValueError('Invalid Word vertical merge')
                                anchor.row_span += 1
                                anchor.content.extend(cell.content)
                                next_active[column] = anchor
                            else:
                                cell.row_index, cell.col_index = r, column
                                row.append(cell)
                                if merge == 'restart':
                                    next_active[column] = cell
                            column += cell.col_span
                        rows.append(row)
                        active = next_active
                    if any(width <= 0 for width in column_widths):
                        column_widths = []
                    table = TableIR(rows=rows, column_widths_pt=column_widths,
                                    total_width_pt=sum(column_widths), source_ref=ref)
                    table_source_refs(table, node, f'{{{W}}}tbl')
                    validate_spans(table)
                    mapped[node] = [table]
                elif tag.endswith('Pr') or tag in {'tblGrid', 'gridCol'}:
                    mapped[node] = []
                else:
                    mapped[node] = children
            document.sections[0].elements = mapped[root]
            if _root_tag == 'document':
                section = document.sections[0]
                section.elements = []
                body = root.find(f'{{{W}}}body')
                if body is None:
                    raise ValueError('Word document body is missing')
                for child in body:
                    section.elements.extend(mapped.get(child, []))
                    properties = child if child.tag == f'{{{W}}}sectPr' else child.find(f'{{{W}}}pPr/{{{W}}}sectPr')
                    if properties is not None:
                        self._section_properties(section, properties, relationships, package, path, document, _part)
                        if child.tag != f'{{{W}}}sectPr':
                            section = SectionIR(source_ref=SourceRef('docx', section_no=len(document.sections) + 1,
                                                                    xml_path=_part))
                            document.sections.append(section)
        document.warnings.append(ConversionWarning('DOCX_PARTIAL', 'Advanced styles, image transforms and section controls are retained in source resources but are not fully mapped.'))
        document.intern_resources()
        return document

    # section properties 작업을 수행함
    def _section_properties(self, section, properties, relationships, package, path, document, part):
        for kind, root_tag in [('header', 'hdr'), ('footer', 'ftr')]:
            references = properties.findall(f'{{{W}}}{kind}Reference')
            for reference in references:
                if reference.get(f'{{{W}}}type', 'default') != 'default':
                    document.warnings.append(ConversionWarning('DOCX_HEADER_FOOTER_VARIANT',
                        'First/even page header/footer variant retained in source resources.', source_ref=section.source_ref))
                    continue
                relation = relationships.get(reference.get(f'{{{R}}}id'))
                if (relation is None or relation.get('TargetMode', 'Internal') != 'Internal'
                        or relation.get('Type') != R + '/' + kind):
                    raise ValueError('Invalid Word header/footer relationship')
                target = package.resolve(part, relation.get('Target', ''))
                parsed = self.parse(path, _part=target, _root_tag=root_tag, _package=package)
                setattr(section, kind, HeaderFooterIR(parsed.sections[0].elements,
                        source_ref=SourceRef('docx', section_no=section.source_ref.section_no, xml_path=target)))
                document.warnings.extend(w for w in parsed.warnings if w.code != 'DOCX_PARTIAL')
