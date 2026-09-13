# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/engine/__init__.py
# 목적: OCR 엔진 인터페이스 및 구현체 팩토리를 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""OCR backend adapters."""

from .base import OCRBackend, OCREngineUnavailable
from .easyocr import EasyOCRBackend
from .ensemble import ConfidenceEnsembleBackend
from .factory import build_local_ocr_backend
from .fake import FakeOCRBackend
from .rapidocr_korean import RapidOCRKoreanBackend
from .tesseract import TesseractBackend

__all__ = [
    "ConfidenceEnsembleBackend",
    "EasyOCRBackend",
    "FakeOCRBackend",
    "OCRBackend",
    "OCREngineUnavailable",
    "RapidOCRKoreanBackend",
    "TesseractBackend",
    "build_local_ocr_backend",
]
