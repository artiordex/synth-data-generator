# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: models.py
# 경로: packages/ocr/ocr/structure/models.py
# 목적: 제목, 본문, 표 등 문서 구조 블록 데이터 모델을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Lightweight structure objects for OCR table/layout recovery."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..pipeline.models import BoundingBox, OCRWord


@dataclass(frozen=True)
class OCRCell:
    """Detected table cell with OCR words assigned by bbox."""

    row: int
    column: int
    bbox: BoundingBox
    row_span: int = 1
    col_span: int = 1
    words: tuple[OCRWord, ...] = ()

    # 텍스트 작업을 수행함
    @property
    def text(self) -> str:
        """Cell text in approximate reading order."""

        return " ".join(word.text for word in sorted(self.words, key=lambda item: (item.bbox.y, item.bbox.x)))


@dataclass(frozen=True)
class OCRTable:
    """Detected OCR table."""

    bbox: BoundingBox
    rows: int
    columns: int
    cells: tuple[OCRCell, ...] = field(default_factory=tuple)
    confidence: float = 0.0
