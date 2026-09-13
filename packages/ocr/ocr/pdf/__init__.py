# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/pdf/__init__.py
# 목적: PDF 문서 OCR 인식 및 파이프라인 진입점을 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PDF OCR pipeline package with no image-pipeline coupling."""

from .classification import classify_pdf
from .inspection import inspect_pdf_pages
from .pipeline import plan_pdf_ocr, run_pdf_ocr

__all__ = ["classify_pdf", "inspect_pdf_pages", "plan_pdf_ocr", "run_pdf_ocr"]
