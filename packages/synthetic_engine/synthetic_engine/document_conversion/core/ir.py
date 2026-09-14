# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ir.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/ir.py
# 목적: 문서 중간 표현(IR) 노드 트리 및 요소 데이터 모델을 정의함
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-14
# =============================================================================
"""Universal document objects. Dimensions are points; text remains verbatim.

Table rows contain logical anchors, not duplicates for covered merge slots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Literal, TypeAlias
from uuid import uuid4

from .enums import (
    BorderStyle, ImagePlacement, PageOrientation, ParagraphAlign, Severity,
    StrikeStyle, SupportStatus, TableAlign, UnderlineStyle, VerticalAlign,
)
from .resources import ResourceStore
from .source_ref import BoundingBoxIR, SourceRef, _is_finite_number


@dataclass
class ConversionWarning:
    """A source-addressable diagnostic."""
    code: str
    message: str
    severity: Severity = Severity.WARNING
    source_ref: SourceRef | None = None
    feature: str | None = None
    support_status: SupportStatus = SupportStatus.PARTIALLY_SUPPORTED


@dataclass
class TextRunIR:
    """Unchanged Unicode text and character formatting."""
    text: str
    font_family_ko: str | None = None
    font_family_en: str | None = None
    size_pt: float = 10.0
    bold: bool = False
    italic: bool = False
    underline: UnderlineStyle = UnderlineStyle.NONE
    strike: StrikeStyle = StrikeStyle.NONE
    color_hex: str | None = None
    bg_color_hex: str | None = None
    letter_spacing_pt: float = 0.0
    scale_percent: float = 100.0
    superscript: bool = False
    subscript: bool = False
    language: str | None = None
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None


@dataclass
class LineBreakIR:
    """An inline break; a paragraph break is a separate ParagraphIR."""
    kind: Literal["soft", "hard"] = "soft"
    source_ref: SourceRef | None = None

    # 줄바꿈 종류 유효성을 검증함
    def __post_init__(self) -> None:
        if self.kind not in ("soft", "hard"):
            raise ValueError("Line break kind must be soft or hard")


@dataclass
class TabIR:
    """A tab control with optional explicit stop."""
    position_pt: float | None = None
    source_ref: SourceRef | None = None


@dataclass
class MathIR:
    """A preserved mathematical expression without claiming calculation correctness.

    ``latex`` and ``mathml`` are renderer-ready only when a parser can map the
    source structure without guessing. Source expressions and resources remain
    available for review and loss-aware fallback when that mapping is partial.
    """

    source_ref: SourceRef | None = None
    display_mode: Literal["inline", "display"] = "inline"
    latex: str | None = None
    mathml: str | None = None
    source_expression: str | None = None
    source_syntax: str | None = None
    source_resource_id: str | None = None
    fallback_image_resource_id: str | None = None
    confidence: float | None = None
    needs_review: bool = False
    failure_reason: str | None = None
    ocr_candidates: list[str] = field(default_factory=list)
    bbox: BoundingBoxIR | None = None

    # 수식 데이터 필드 및 신뢰도 유효성을 검증함
    def __post_init__(self) -> None:
        if self.display_mode not in ("inline", "display"):
            raise ValueError("Math display mode must be inline or display")
        _validate_confidence(self.confidence)
        for name in ("latex", "mathml", "source_expression", "source_syntax", "failure_reason"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or value == ""):
                raise ValueError(f"Math {name} must be a non-empty string when provided")
        if not all(isinstance(candidate, str) and candidate for candidate in self.ocr_candidates):
            raise ValueError("Math OCR candidates must be non-empty strings")
        for name in ("source_resource_id", "fallback_image_resource_id"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(f"Math {name} must be a lowercase SHA-256 resource identifier")
        if not any((
            self.latex,
            self.mathml,
            self.source_expression,
            self.source_resource_id,
            self.fallback_image_resource_id,
            self.ocr_candidates,
        )):
            raise ValueError("MathIR requires recognized or preserved source evidence")
        if self.needs_review and self.failure_reason is None:
            raise ValueError("MathIR requiring review must include a failure reason")


@dataclass
class HyperlinkIR:
    """Link target is data only and must not be fetched implicitly."""
    target: str
    inlines: list[InlineIR] = field(default_factory=list)
    title: str | None = None
    source_ref: SourceRef | None = None


@dataclass
class FieldIR:
    """Dynamic field with separately retained cached presentation."""
    field_type: str
    instruction: str | None = None
    cached_text: str | None = None
    source_ref: SourceRef | None = None


InlineIR: TypeAlias = TextRunIR | LineBreakIR | TabIR | MathIR | HyperlinkIR | FieldIR


@dataclass
class ParagraphIR:
    """Paragraph boundary, inline controls and formatting."""
    inlines: list[InlineIR] = field(default_factory=list)
    align: ParagraphAlign = ParagraphAlign.LEFT
    line_spacing_percent: float = 100.0
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    indent_pt: float = 0.0
    hanging_pt: float = 0.0
    heading_level: int | None = None
    page_break_before: bool = False
    keep_with_next: bool = False
    keep_lines_together: bool = False
    list_level: int | None = None
    list_type: str | None = None
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None


@dataclass
class BorderIR:
    """One explicit border, including an explicit NONE style."""
    style: BorderStyle = BorderStyle.NONE
    width_pt: float = 0.0
    color_hex: str = "000000"


@dataclass
class TableCellIR:
    """Logical anchor with arbitrarily nested block content."""
    row_index: int
    col_index: int
    row_span: int = 1
    col_span: int = 1
    width_pt: float | None = None
    height_pt: float | None = None
    bg_color_hex: str | None = None
    borders: dict[str, BorderIR] = field(default_factory=dict)
    padding_pt: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    vertical_align: VerticalAlign = VerticalAlign.TOP
    content: list[BlockIR] = field(default_factory=list)
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None
    cell_confidence: float | None = None
    support_status: SupportStatus = SupportStatus.SUPPORTED
    formula: str | None = None
    cached_value: str | float | int | bool | None = None
    number_format: str | None = None

    # 셀 신뢰도 유효성을 검증함
    def __post_init__(self) -> None:
        _validate_confidence(self.cell_confidence)


@dataclass
class TableIR:
    """Logical table anchors; physical merge expansion belongs to geometry."""
    table_id: str = field(default_factory=lambda: str(uuid4()))
    depth: int = 0
    rows: list[list[TableCellIR]] = field(default_factory=list)
    column_widths_pt: list[float] = field(default_factory=list)
    total_width_pt: float = 0.0
    alignment: TableAlign = TableAlign.LEFT
    is_floating: bool = False
    repeat_header_rows: int = 0
    cant_split: bool = False
    caption: ParagraphIR | None = None
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None
    table_confidence: float | None = None
    support_status: SupportStatus = SupportStatus.SUPPORTED

    # 표 신뢰도 유효성을 검증함
    def __post_init__(self) -> None:
        _validate_confidence(self.table_confidence)


@dataclass
class ImageIR:
    """Original payload and independent placement; DocumentIR interns bytes."""
    image_bytes: bytes
    mime_type: str
    format: str
    width_pt: float
    height_pt: float
    original_width_px: int | None = None
    original_height_px: int | None = None
    aspect_ratio: float | None = None
    placement: ImagePlacement = ImagePlacement.INLINE
    opacity: float = 1.0
    rotation_deg: float = 0.0
    caption: ParagraphIR | None = None
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None
    resource_id: str | None = None

    # 이미지 바이너리 데이터 유효성을 검증함
    def __post_init__(self) -> None:
        if not isinstance(self.image_bytes, bytes):
            raise TypeError("Image data must be immutable bytes")
        if not all(_is_finite_number(v) and v >= 0 for v in (self.width_pt, self.height_pt)):
            raise ValueError("Image dimensions must be finite and nonnegative")
        for dimension in (self.original_width_px, self.original_height_px):
            if dimension is not None and (not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0):
                raise ValueError("Original image pixel dimensions must be positive integers")
        if self.aspect_ratio is None:
            if self.original_width_px is not None and self.original_height_px is not None:
                self.aspect_ratio = self.original_width_px / self.original_height_px
            elif self.width_pt > 0 and self.height_pt > 0:
                self.aspect_ratio = self.width_pt / self.height_pt
            else:
                raise ValueError("Image aspect ratio requires original or display dimensions")
        if not _is_finite_number(self.aspect_ratio) or self.aspect_ratio <= 0:
            raise ValueError("Image aspect ratio must be finite and positive")
        if not _is_finite_number(self.opacity) or not 0 <= self.opacity <= 1:
            raise ValueError("Image opacity must be between zero and one")
        if not _is_finite_number(self.rotation_deg):
            raise ValueError("Image rotation must be finite")


@dataclass
class DrawingIR:
    """Drawing geometry and text independent of source drawing syntax."""
    drawing_type: str
    x_pt: float = 0.0
    y_pt: float = 0.0
    width_pt: float = 0.0
    height_pt: float = 0.0
    z_index: int = 0
    line_color_hex: str | None = None
    fill_color_hex: str | None = None
    text_content: list[ParagraphIR] = field(default_factory=list)
    source_ref: SourceRef | None = None
    bbox: BoundingBoxIR | None = None
    support_status: SupportStatus = SupportStatus.SUPPORTED
    resource_id: str | None = None


@dataclass
class UnsupportedRecordIR:
    """Uninterpreted source record retained verbatim for audit or adapters."""
    tag_id: int
    level: int
    raw_bytes: bytes
    source_ref: SourceRef | None = None
    support_status: SupportStatus = SupportStatus.UNSUPPORTED


BlockIR: TypeAlias = ParagraphIR | TableIR | ImageIR | DrawingIR | MathIR | UnsupportedRecordIR


@dataclass
class HeaderFooterIR:
    """Header/footer sequence with dynamic fields inside paragraphs."""
    elements: list[BlockIR] = field(default_factory=list)
    source_ref: SourceRef | None = None


@dataclass
class SectionIR:
    """Absent page dimensions remain unknown instead of invented layout."""
    page_width_pt: float | None = None
    page_height_pt: float | None = None
    orientation: PageOrientation = PageOrientation.PORTRAIT
    margin_top_pt: float = 0.0
    margin_bottom_pt: float = 0.0
    margin_left_pt: float = 0.0
    margin_right_pt: float = 0.0
    header_distance_pt: float = 0.0
    footer_distance_pt: float = 0.0
    column_count: int = 1
    column_gap_pt: float = 0.0
    header: HeaderFooterIR | None = None
    footer: HeaderFooterIR | None = None
    elements: list[BlockIR] = field(default_factory=list)
    source_ref: SourceRef | None = None


@dataclass
class DocumentMetadata:
    """Metadata strings retained without rewriting names or timestamps."""
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    description: str | None = None
    language: str | None = None
    created: str | None = None
    modified: str | None = None
    keywords: list[str] = field(default_factory=list)
    custom: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentIR:
    """Document root and deduplicated resources without conversion side effects."""
    document_id: str = field(default_factory=lambda: str(uuid4()))
    source_format: str = ""
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    sections: list[SectionIR] = field(default_factory=list)
    resources: ResourceStore = field(default_factory=ResourceStore)
    warnings: list[ConversionWarning] = field(default_factory=list)
    source_path: str | None = None

    # 문서 생성 후 리소스 내부 캐시를 동기화함
    def __post_init__(self) -> None:
        self.intern_resources()

    # 순환 참조 없이 문서 내 블록 요소를 순회함
    def iter_blocks(self) -> Iterator[BlockIR]:
        """Visit blocks, rejecting block and paragraph-inline cycles before yield.

        Validation is lazy and also applies after tree mutations. Reused
        acyclic blocks and inlines remain distinct occurrences.
        """
        roots: list[BlockIR] = []
        for section in self.sections:
            if section.header is not None:
                roots.extend(section.header.elements)
            roots.extend(section.elements)
            if section.footer is not None:
                roots.extend(section.footer.elements)
        stack: list[tuple[BlockIR, bool]] = [(block, False) for block in reversed(roots)]
        active: set[int] = set()
        while stack:
            block, leaving = stack.pop()
            identity = id(block)
            if leaving:
                active.remove(identity)
                continue
            if identity in active:
                raise ValueError("Document block graph contains a cycle")
            active.add(identity)
            stack.append((block, True))
            if isinstance(block, ParagraphIR):
                _validate_inline_cycles(block.inlines)
            yield block
            children: list[BlockIR] = []
            if isinstance(block, TableIR):
                if block.caption is not None:
                    children.append(block.caption)
                children.extend(child for row in block.rows for cell in row for child in cell.content)
            elif isinstance(block, ImageIR) and block.caption is not None:
                children.append(block.caption)
            elif isinstance(block, DrawingIR):
                children.extend(block.text_content)
            stack.extend((child, False) for child in reversed(children))

    # 문서 내 이미지 바이너리 리소스를 인턴 처리하여 메모리를 절약함
    def intern_resources(self) -> None:
        """Share image payloads after construction or later tree mutations."""
        for block in self.iter_blocks():
            if isinstance(block, ImageIR):
                block.resource_id = self.resources.add(block.image_bytes, block.mime_type)
                block.image_bytes = self.resources.get(block.resource_id)


# 하이퍼링크 순환 참조 유효성을 검증함
def _validate_inline_cycles(inlines: list[InlineIR]) -> None:
    """Check hyperlink ancestry without recursion or rejecting shared subgraphs."""
    active: set[int] = set()
    complete: set[int] = set()
    stack = [(inline, False) for inline in reversed(inlines)
             if isinstance(inline, HyperlinkIR)]
    while stack:
        inline, leaving = stack.pop()
        identity = id(inline)
        if leaving:
            active.remove(identity)
            complete.add(identity)
            continue
        if identity in active:
            raise ValueError("Document inline graph contains a cycle")
        if identity in complete:
            continue
        active.add(identity)
        stack.append((inline, True))
        stack.extend((child, False) for child in reversed(inline.inlines)
                     if isinstance(child, HyperlinkIR))


# 인식 신뢰도 점수의 범위 및 유효성을 검증함
def _validate_confidence(value: float | None) -> None:
    """Validate an inferred score without inventing confidence for source facts."""
    if value is not None and (not _is_finite_number(value) or not 0 <= value <= 1):
        raise ValueError("Confidence must be finite and between zero and one")
