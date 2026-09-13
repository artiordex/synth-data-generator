# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: hwp5_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/hwp5_parser.py
# 목적: HWP 바이너리 문서를 pyhwp를 통해 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Bounded HWP 5 record reading with explicit partial control-tree support."""
from pathlib import Path
import struct
import zlib

from ..core.ir import DocumentIR, SectionIR, ParagraphIR, TextRunIR, TabIR, LineBreakIR, MathIR, UnsupportedRecordIR, ConversionWarning
from ..core.source_ref import SourceRef
from ..exceptions import DocumentConversionError, UnsupportedFeatureError


HWP_TAG_SHAPE_COMPONENT_OLE = 84
HWP_TAG_CTRL_EQEDIT = 88


def decompress(data: bytes, limit: int = 64 * 1024 ** 2) -> bytes:
    decoder = zlib.decompressobj(-15)
    output = decoder.decompress(data, limit + 1)
    if len(output) > limit or decoder.unconsumed_tail or not decoder.eof:
        raise DocumentConversionError('Invalid or oversized compressed HWP stream')
    return output


def records(data: bytes):
    offset = 0
    while offset < len(data):
        start = offset
        if len(data) - offset < 4:
            raise DocumentConversionError('Truncated HWP record header')
        packed, = struct.unpack_from('<I', data, offset)
        offset += 4
        tag, level, size = packed & 1023, (packed >> 10) & 1023, packed >> 20
        if size == 4095:
            if len(data) - offset < 4:
                raise DocumentConversionError('Truncated extended HWP size')
            size, = struct.unpack_from('<I', data, offset)
            offset += 4
        if size > len(data) - offset:
            raise DocumentConversionError('Truncated HWP record payload')
        yield tag, level, data[offset:offset+size], start
        offset += size


def paragraph_text(payload: bytes, ref: SourceRef) -> ParagraphIR:
    if len(payload) % 2:
        raise DocumentConversionError('Odd length HWP UTF-16 text')
    paragraph, pending = ParagraphIR(source_ref=ref), bytearray()
    offset = 0
    while offset < len(payload):
        value, = struct.unpack_from('<H', payload, offset)
        if value >= 32:
            pending.extend(payload[offset:offset+2])
            offset += 2
            continue
        if pending:
            paragraph.inlines.append(TextRunIR(pending.decode('utf-16-le'), source_ref=ref))
            pending.clear()
        if value == 9:
            paragraph.inlines.append(TabIR(source_ref=ref))
        elif value == 10:
            paragraph.inlines.append(LineBreakIR(source_ref=ref))
        # HWP inline and extended controls occupy eight UTF-16 units.
        size = 16 if value in {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23} else 2
        if offset + size > len(payload):
            raise DocumentConversionError('Truncated HWP text control')
        offset += size
    if pending:
        paragraph.inlines.append(TextRunIR(pending.decode('utf-16-le'), source_ref=ref))
    return paragraph


def _parse_eqedit_math(payload: bytes, ref: SourceRef, resources) -> MathIR:
    """Read the bounded EqEdit header/script and retain the complete raw record."""
    resource_id = resources.add(payload, 'application/x-hwp-eqedit')
    display_mode = 'inline'
    source_expression = None
    failure_reason = 'HWP EqEdit record is truncated or has an invalid UTF-16 script.'
    if len(payload) >= 6:
        flags, script_length = struct.unpack_from('<IH', payload, 0)
        display_mode = 'display' if flags & 1 else 'inline'
        script_end = 6 + script_length * 2
        if script_end <= len(payload):
            try:
                decoded = payload[6:script_end].decode('utf-16-le', errors='strict')
                if decoded:
                    source_expression = decoded
                    failure_reason = (
                        'HWP EqEdit script is preserved, but LaTeX/MathML conversion is not implemented.'
                    )
                else:
                    failure_reason = 'HWP EqEdit record contains an empty script.'
            except UnicodeDecodeError:
                pass
    return MathIR(
        source_ref=ref,
        display_mode=display_mode,
        source_expression=source_expression,
        source_syntax='hwp-eqedit-script' if source_expression is not None else 'hwp-eqedit-record',
        source_resource_id=resource_id,
        needs_review=True,
        failure_reason=failure_reason,
    )


class Hwp5Parser:
    def parse(self, path: Path) -> DocumentIR:
        import olefile
        document = DocumentIR(source_format='hwp', source_path=str(path))
        with olefile.OleFileIO(path) as archive:
            header = archive.openstream('FileHeader').read()
            if len(header) < 40 or not header.startswith(b'HWP Document File'):
                raise DocumentConversionError('Not an HWP 5 document')
            flags, = struct.unpack_from('<I', header, 36)
            if flags & 6:
                raise UnsupportedFeatureError('Encrypted/distribution HWP is unsupported')
            streams = archive.listdir()
            if len(streams) > 10000:
                raise DocumentConversionError('Too many HWP streams')
            total = 0
            for entry in streams:
                size = archive.get_size(entry)
                total += size
                if size > 64 * 1024 ** 2 or total > 256 * 1024 ** 2:
                    raise DocumentConversionError('HWP stream size limit exceeded')
                document.resources.add(archive.openstream(entry).read())
            sections = sorted((p for p in streams if len(p) == 2 and p[0] == 'BodyText' and p[1].startswith('Section')),
                              key=lambda p: int(p[1][7:]))
            if not sections:
                raise DocumentConversionError('HWP BodyText sections are missing')
            expanded_total = 0
            for index, entry in enumerate(sections, 1):
                data = archive.openstream(entry).read()
                if flags & 1:
                    data = decompress(data)
                expanded_total += len(data)
                if expanded_total > 256 * 1024 ** 2:
                    raise DocumentConversionError('Expanded HWP document exceeds size limit')
                section = SectionIR(source_ref=SourceRef('hwp', section_no=index))
                document.sections.append(section)
                for tag, level, payload, offset in records(data):
                    ref = SourceRef('hwp', section_no=index, record_offset=offset, object_id='/'.join(entry))
                    if tag == 67:
                        section.elements.append(paragraph_text(payload, ref))
                    elif tag == HWP_TAG_CTRL_EQEDIT:
                        section.elements.append(_parse_eqedit_math(payload, ref, document.resources))
                        document.warnings.append(ConversionWarning(
                            'HWP5_MATH_REVIEW',
                            'EqEdit source is retained without claiming LaTeX/MathML equivalence.',
                            source_ref=ref,
                            feature='math',
                        ))
                    else:
                        section.elements.append(UnsupportedRecordIR(tag, level, payload, source_ref=ref))
                        if tag == HWP_TAG_SHAPE_COMPONENT_OLE:
                            document.warnings.append(ConversionWarning(
                                'HWP5_OLE_REVIEW',
                                'OLE record is not assumed to be math; raw bytes are retained for review.',
                                source_ref=ref,
                                feature='embedded_object',
                            ))
        document.warnings.append(ConversionWarning('HWP5_PARTIAL_CONTROL_TREE',
            'Paragraph text and raw records are preserved. Styles, tables, images, controls and line geometry are not yet semantically mapped.'))
        return document
