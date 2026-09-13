# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/__init__.py
# 목적: 고정밀 OCR 파이프라인 진입점 및 주요 데이터 모델을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""High-precision OCR pipelines with separated PDF and image entry points."""

from .image.pipeline import run_image_ocr
from .pipeline.models import (
    ErrorCode,
    FileType,
    ImageIssue,
    OCRDocumentResult,
    OCRStatus,
    PdfType,
    PreprocessingProfile,
)

__all__ = [
    "ErrorCode",
    "FileType",
    "ImageIssue",
    "OCRDocumentResult",
    "OCRStatus",
    "PdfType",
    "PreprocessingProfile",
    "run_image_ocr",
]
