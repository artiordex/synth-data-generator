# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: hwpx_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/hwpx_parser.py
# 목적: HWPX 한글 표준 문서를 분석하여 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Namespace-based HWPX parsing with explicit preservation of unsupported XML."""
from dataclasses import replace
from pathlib import Path
from zipfile import BadZipFile
import re
from lxml import etree

from .package import DocumentPackage
from .common import check_table_size, image_from_bytes, table_source_refs
from ..core.ir import (
    DocumentIR, SectionIR, ParagraphIR, TextRunIR, TabIR, LineBreakIR,
    TableIR, TableCellIR, ImageIR, MathIR, UnsupportedRecordIR, ConversionWarning,
)
from ..core.source_ref import SourceRef
from ..core.enums import ParagraphAlign
from ..geometry.table_geometry import validate_spans
from ..exceptions import DocumentConversionError

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
HH = 'http://www.hancom.co.kr/hwpml/2011/head'
HS = 'http://www.hancom.co.kr/hwpml/2011/section'


def number(node, key, default=0):
    return float(node.get(key, default))


def _hwpx_equation(node, ref, document, package, binaries, source_resource_id):
    """Preserve a native EqEdit expression without relabeling it as LaTeX."""
    script = node.find(f'{{{HP}}}script')
    source_expression = script.text if script is not None and script.text else None
    position = node.find(f'{{{HP}}}pos')
    treat_as_char = position.get('treatAsChar') if position is not None else None
    line_mode = node.get('lineMode')
    if treat_as_char in {'0', 'false'} or line_mode == 'LINE':
        display_mode = 'display'
    else:
        display_mode = 'inline'

    fallback_image_resource_id = None
    image = next((item for item in node.iter() if item.get('binaryItemIDRef')), None)
    resource = binaries.get(image.get('binaryItemIDRef')) if image is not None else None
    image_suffixes = {'.bmp', '.emf', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.wmf'}
    if resource and Path(resource).suffix.lower() in image_suffixes:
        try:
            fallback_image_resource_id = document.resources.add(
                package.read(resource), 'application/octet-stream'
            )
        except (OSError, ValueError):
            fallback_image_resource_id = None

    failure_reason = (
        'Hancom equation script is preserved, but LaTeX/MathML conversion is not implemented.'
        if source_expression is not None
        else 'Hancom equation XML has no non-empty script.'
    )
    document.warnings.append(ConversionWarning(
        'HWPX_MATH_REVIEW',
        failure_reason + ' Original section XML is retained.',
        source_ref=ref,
        feature='math',
    ))
    return MathIR(
        source_ref=ref,
        display_mode=display_mode,
        source_expression=source_expression,
        source_syntax=(
            'hancom-equation-script' if source_expression is not None else 'hwpx-equation-xml'
        ),
        source_resource_id=source_resource_id,
        fallback_image_resource_id=fallback_image_resource_id,
        needs_review=True,
        failure_reason=failure_reason,
    )


class HwpxParser:
    def can_parse(self, path: Path) -> bool:
        try:
            with DocumentPackage(path) as package:
                return 'Contents/header.xml' in package.names and any(
                    re.fullmatch(r'Contents/section\d+\.xml', name) for name in package.names)
        except (OSError, ValueError, BadZipFile, etree.XMLSyntaxError):
            return False

    def parse(self, path: Path) -> DocumentIR:
        document = DocumentIR(source_format='hwpx', source_path=str(path))
        with DocumentPackage(path) as package:
            header = package.xml('Contents/header.xml')
            if etree.QName(header).namespace != HH:
                raise DocumentConversionError('Not an HWPX header')
            # Retain all source records and binary resources, not only interpreted nodes.
            for name in sorted(package.names):
                if not name.endswith('/'):
                    document.resources.add(package.read(name))
            styles = {node.get('id'): node for node in header.iter(f'{{{HH}}}charPr')}
            binaries = {}
            if 'Contents/content.hpf' in package.names:
                for item in package.xml('Contents/content.hpf').iter():
                    if item.get('id') and item.get('href'):
                        href = item.get('href')
                        try:
                            resolved = package.resolve('Contents/content.hpf', href)
                        except DocumentConversionError:
                            # Some producers use package-root paths without a slash.
                            try:
                                resolved = package.resolve('content.hpf', href)
                            except DocumentConversionError:
                                continue
                        if item.get('id') in binaries:
                            raise DocumentConversionError('Duplicate HWPX binary identifier')
                        binaries[item.get('id')] = resolved
            fonts = {}
            for face in header.iter(f'{{{HH}}}fontface'):
                fonts[face.get('lang')] = {f.get('id'): f.get('face') for f in face}
            paragraphs = {node.get('id'): node for node in header.iter(f'{{{HH}}}paraPr')}
            names = sorted((n for n in package.names if re.fullmatch(r'Contents/section\d+\.xml', n)),
                           key=lambda n: int(re.search(r'(\d+)\.xml$', n).group(1)))
            if not names:
                raise DocumentConversionError('HWPX sections are missing')
            for section_no, name in enumerate(names, 1):
                source_resource_id = document.resources.add(package.read(name), 'application/xml')
                root = package.xml(name)
                if etree.QName(root).namespace != HS:
                    raise DocumentConversionError('Not an HWPX section')
                section = SectionIR(source_ref=SourceRef('hwpx', section_no=section_no, xml_path=name))
                document.sections.append(section)
                mapped = {}
                for node in reversed(list(root.iter())):
                    if not isinstance(node.tag, str):
                        continue
                    qname = etree.QName(node)
                    tag = qname.localname if qname.namespace in {HP, HS} else 'unknown'
                    ref = SourceRef('hwpx', section_no=section_no,
                                    xml_path=name + ':' + root.getroottree().getpath(node),
                                    object_id=node.get('id'))
                    children = [item for child in node for item in mapped.get(child, [])]
                    inside_equation = any(
                        isinstance(parent.tag, str)
                        and etree.QName(parent).namespace == HP
                        and etree.QName(parent).localname == 'equation'
                        for parent in node.iterancestors()
                    )
                    if inside_equation:
                        # The equation owner reads the entire native subtree once.
                        mapped[node] = []
                    elif tag == 'equation':
                        mapped[node] = [_hwpx_equation(
                            node, ref, document, package, binaries, source_resource_id
                        )]
                    elif tag == 't':
                        values = [TextRunIR(node.text, source_ref=ref)] if node.text is not None else []
                        for child in node:
                            values.extend(mapped.get(child, []))
                            if child.tail is not None:
                                values.append(TextRunIR(child.tail, source_ref=ref))
                        mapped[node] = values
                    elif tag in {'tab', 'lineBreak'}:
                        mapped[node] = [TabIR(source_ref=ref) if tag == 'tab' else LineBreakIR(source_ref=ref)]
                    elif tag == 'run':
                        style = styles.get(node.get('charPrIDRef'))
                        if style is not None:
                            options = dict(size_pt=number(style, 'height', 1000) / 100,
                                           bold=style.find(f'{{{HH}}}bold') is not None,
                                           italic=style.find(f'{{{HH}}}italic') is not None,
                                           color_hex=style.get('textColor', '#000000').lstrip('#'))
                            font_ref = style.find(f'{{{HH}}}fontRef')
                            if font_ref is not None:
                                options['font_family_ko'] = fonts.get('HANGUL', {}).get(font_ref.get('hangul'))
                                options['font_family_en'] = fonts.get('LATIN', {}).get(font_ref.get('latin'))
                            children = [replace(item, **options) if isinstance(item, TextRunIR) else item
                                        for item in children]
                        mapped[node] = children
                    elif tag == 'p':
                        result, inline = [], []
                        style = paragraphs.get(node.get('paraPrIDRef'))
                        align = style.find(f'{{{HH}}}align') if style is not None else None
                        alignment = align.get('horizontal', 'LEFT').lower() if align is not None else 'left'
                        alignment = ParagraphAlign(alignment) if alignment in ParagraphAlign._value2member_map_ else ParagraphAlign.LEFT
                        for child in children:
                            if isinstance(child, (TextRunIR, TabIR, LineBreakIR, MathIR)) and not (
                                isinstance(child, MathIR) and child.display_mode == 'display'
                            ):
                                inline.append(child)
                            else:
                                if inline:
                                    result.append(ParagraphIR(inlines=inline, align=alignment, source_ref=ref))
                                    inline = []
                                result.append(child)
                        if inline or not result:
                            result.append(ParagraphIR(inlines=inline, align=alignment, source_ref=ref))
                        mapped[node] = result
                    elif tag == 'tc':
                        addr = node.find(f'{{{HP}}}cellAddr')
                        if addr is None:
                            raise DocumentConversionError('HWPX cell has no logical address')
                        span = node.find(f'{{{HP}}}cellSpan')
                        size = node.find(f'{{{HP}}}cellSz')
                        margin = node.find(f'{{{HP}}}cellMargin')
                        mapped[node] = [TableCellIR(
                            row_index=int(addr.get('rowAddr')), col_index=int(addr.get('colAddr')),
                            row_span=int(span.get('rowSpan', 1)) if span is not None else 1,
                            col_span=int(span.get('colSpan', 1)) if span is not None else 1,
                            width_pt=number(size, 'width') / 100 if size is not None and size.get('width') else None,
                            padding_pt=tuple(number(margin, k) / 100 for k in ('top', 'right', 'bottom', 'left')) if margin is not None else (0, 0, 0, 0),
                            content=children, source_ref=ref,
                        )]
                    elif tag == 'tbl':
                        cells = [c for c in children if isinstance(c, TableCellIR)]
                        count = int(node.get('rowCnt', 0)) or max((c.row_index+c.row_span for c in cells), default=0)
                        columns = int(node.get('colCnt', 0)) or max((c.col_index+c.col_span for c in cells), default=0)
                        check_table_size(count, columns)
                        rows = [[] for _ in range(count)]
                        for cell in cells:
                            if (cell.row_index < 0 or cell.col_index < 0 or cell.row_span < 1
                                    or cell.col_span < 1 or cell.row_index + cell.row_span > count
                                    or cell.col_index + cell.col_span > columns):
                                raise DocumentConversionError('HWPX cell exceeds declared grid')
                            rows[cell.row_index].append(cell)
                        table = TableIR(rows=rows, source_ref=ref)
                        table_source_refs(table, node, f'{{{HP}}}tbl')
                        validate_spans(table)
                        mapped[node] = [table]
                    elif tag == 'pagePr':
                        section.page_width_pt = number(node, 'width') / 100
                        section.page_height_pt = number(node, 'height') / 100
                        mapped[node] = []
                    elif tag == 'pic':
                        image = next((n for n in node.iter() if n.get('binaryItemIDRef')), None)
                        resource = binaries.get(image.get('binaryItemIDRef')) if image is not None else None
                        size = node.find(f'{{{HP}}}sz')
                        try:
                            if not resource or size is None:
                                raise ValueError('Image reference or size is missing')
                            mapped[node] = [image_from_bytes(package.read(resource),
                                number(size, 'width') / 100, number(size, 'height') / 100, ref)]
                        except (OSError, ValueError):
                            mapped[node] = [UnsupportedRecordIR(0, 0, etree.tostring(node), source_ref=ref)]
                            document.warnings.append(ConversionWarning('HWPX_IMAGE_UNRESOLVED', 'Image reference, format or size is unsupported; source XML is retained', source_ref=ref))
                    elif tag == 'ole':
                        raw_xml = etree.tostring(node, encoding='utf-8', with_tail=False)
                        mapped[node] = [UnsupportedRecordIR(0, 0, raw_xml, source_ref=ref)]
                        document.warnings.append(ConversionWarning(
                            'HWPX_OLE_REVIEW',
                            'Embedded OLE object is not assumed to be math; source XML is retained for review.',
                            source_ref=ref,
                            feature='embedded_object',
                        ))
                    elif tag in {'cellAddr', 'cellSpan', 'cellSz', 'cellMargin', 'linesegarray', 'lineseg'}:
                        mapped[node] = []
                    elif tag in {'sec', 'subList', 'tr'}:
                        mapped[node] = children
                    else:
                        # Unknown controls are kept intact rather than silently flattened.
                        mapped[node] = [UnsupportedRecordIR(0, 0, etree.tostring(node), source_ref=ref)]
                        document.warnings.append(ConversionWarning('HWPX_UNMAPPED',
                            f'Unmapped element: {qname.localname}', source_ref=ref))
                section.elements = mapped[root]
        document.warnings.append(ConversionWarning('HWPX_PARTIAL_STYLES',
            'Font references, complex borders, drawings and header/footer controls need additional mapping; source records are retained.'))
        document.intern_resources()
        return document
