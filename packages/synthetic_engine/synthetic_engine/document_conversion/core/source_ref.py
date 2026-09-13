# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: source_ref.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/source_ref.py
# 목적: 원본 문서 위치 및 페이지/영역 추적 참조 모델을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Source object identity and original page geometry."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SourceRef:
    """Page/section numbers are one-based; row/column indices zero-based."""
    source_format: str
    page_no: int | None = None
    section_no: int | None = None
    xml_path: str | None = None
    record_offset: int | None = None
    object_id: str | None = None
    table_id: str | None = None
    row_index: int | None = None
    col_index: int | None = None

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        for name in ("page_no", "section_no"):
            value = getattr(self, name)
            if value is not None:
                _validate_index(name, value, minimum=1)
        for name in ("record_offset", "row_index", "col_index"):
            value = getattr(self, name)
            if value is not None:
                _validate_index(name, value, minimum=0)


@dataclass(frozen=True)
class BoundingBoxIR:
    """Page-space rectangle in points."""
    x0: float
    y0: float
    x1: float
    y1: float
    page_no: int

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        if not all(_is_finite_number(v) for v in (self.x0, self.y0, self.x1, self.y1)):
            raise ValueError("Bounding box coordinates must be finite")
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("Bounding box endpoints must be ordered")
        if not all(isfinite(v) for v in (self.x1 - self.x0, self.y1 - self.y0)):
            raise ValueError("Bounding box extents must be finite")
        _validate_index("page_no (one-based)", self.page_no, minimum=1)

    # 너비 pt 작업을 수행함
    @property
    def width_pt(self) -> float:
        """Return horizontal extent."""
        return self.x1 - self.x0

    # 높이 pt 작업을 수행함
    @property
    def height_pt(self) -> float:
        """Return vertical extent."""
        return self.y1 - self.y0


# index 유효성 및 제약조건을 검증함
def _validate_index(name: str, value: int, *, minimum: int) -> None:
    """Indices exclude booleans and fractional coordinates."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


# finite number 여부 및 유효성을 판별함
def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False
