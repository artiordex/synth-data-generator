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

from importlib import import_module

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

_PDF_EXPORTS = {
    "classify_pdf": "classify_pdf",
    "inspect_pdf_pages": "inspect_pdf_pages",
    "plan_pdf_ocr": "plan_pdf_ocr",
    "run_pdf_ocr": "run_pdf_ocr",
}

__all__ = [
    "ErrorCode",
    "FileType",
    "ImageIssue",
    "OCRDocumentResult",
    "OCRStatus",
    "PdfType",
    "PreprocessingProfile",
    "classify_pdf",
    "inspect_pdf_pages",
    "plan_pdf_ocr",
    "run_pdf_ocr",
    "run_image_ocr",
]


def __getattr__(name: str):
    """Load the PDF pipeline only when a PDF entry point is requested."""
    attribute = _PDF_EXPORTS.get(name)
    if attribute is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".pdf", __name__)
    value = getattr(module, attribute)
    globals()[name] = value
    return value
