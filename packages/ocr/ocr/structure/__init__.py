# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/structure/__init__.py
# 목적: 문서 구조 분석 및 블록 분류 모듈을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Document structure recovery primitives."""

from .models import OCRCell, OCRTable
from .reconstruction_models import (
    OCRFigureBlock,
    OCRPageResult,
    OCRTableCell,
    OCRTextBlock,
    ReconstructionOCRWord,
)

__all__ = [
    "OCRCell",
    "OCRTable",
    "OCRFigureBlock",
    "OCRPageResult",
    "OCRTableCell",
    "OCRTextBlock",
    "ReconstructionOCRWord",
]
