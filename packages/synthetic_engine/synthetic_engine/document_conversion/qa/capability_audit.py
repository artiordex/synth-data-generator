# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: capability_audit.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/qa/capability_audit.py
# 목적: 포맷 변환 간 기능 손실 및 충실도 감사를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Source-addressed target capability checks before rendering."""
from ..core.capabilities import TargetCapabilities
from ..core.enums import ImagePlacement
from ..core.ir import (
    ConversionWarning, DocumentIR, DrawingIR, ImageIR, ParagraphIR,
    TableIR, TextRunIR, HyperlinkIR, UnsupportedRecordIR,
)


# capability warnings 작업을 수행함
def capability_warnings(document: DocumentIR, capabilities: TargetCapabilities) -> list[ConversionWarning]:
    """Inspect required features without mutating or flattening the IR."""
    warnings: list[ConversionWarning] = []

    # require 작업을 수행함
    def require(name: str, source_ref) -> None:
        if not getattr(capabilities, name):
            warnings.append(ConversionWarning('TARGET_CAPABILITY_LOSS',
                f'Target has no native mapping for {name}.', source_ref=source_ref, feature=name))

    for section in document.sections:
        if section.page_width_pt is not None:
            require('supports_pages', section.source_ref)
        if section.header:
            require('supports_headers', section.header.source_ref or section.source_ref)
        if section.footer:
            require('supports_footers', section.footer.source_ref or section.source_ref)
    for block in document.iter_blocks():
        if isinstance(block, TableIR):
            for row in block.rows:
                for cell in row:
                    ref = cell.source_ref or block.source_ref
                    if cell.row_span > 1:
                        require('supports_rowspan', ref)
                    if cell.col_span > 1:
                        require('supports_colspan', ref)
                    if any(isinstance(b, TableIR) for b in cell.content):
                        require('supports_nested_tables', ref)
                    if any(key in cell.borders for key in ('slash', 'backslash')):
                        require('supports_diagonal_borders', ref)
        elif isinstance(block, ImageIR) and block.placement != ImagePlacement.INLINE:
            require('supports_floating_images', block.source_ref)
        elif isinstance(block, DrawingIR):
            require('supports_text_boxes', block.source_ref)
            warnings.append(ConversionWarning('DRAWING_MAPPING_PARTIAL',
                'Drawing geometry needs renderer-specific fidelity review.', source_ref=block.source_ref, feature='drawings'))
        elif isinstance(block, UnsupportedRecordIR):
            warnings.append(ConversionWarning('UNSUPPORTED_RECORD',
                f'Raw source record {block.tag_id} has no native target mapping.',
                source_ref=block.source_ref, feature='raw_records', support_status=block.support_status))
        elif isinstance(block, ParagraphIR):
            stack = list(reversed(block.inlines))
            while stack:
                inline = stack.pop()
                if isinstance(inline, HyperlinkIR):
                    stack.extend(reversed(inline.inlines))
                elif isinstance(inline, TextRunIR):
                    if inline.letter_spacing_pt:
                        require('supports_letter_spacing', inline.source_ref or block.source_ref)
                    if inline.scale_percent != 100:
                        require('supports_font_scaling', inline.source_ref or block.source_ref)
    return warnings
