# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: classification.py
# 경로: packages/ocr/ocr/pdf/classification.py
# 목적: PDF 문서의 디지털 텍스트 포함 여부 및 스캔본 유형을 분류함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PDF file inspection and type classification."""

from __future__ import annotations

from pathlib import Path

from ..pipeline.models import PdfType


# classify PDF 문서 작업을 수행함
def classify_pdf(source: str | Path, *, max_pages_to_check: int = 5) -> PdfType:
    """Classify a PDF before deciding whether OCR is required."""

    import pymupdf

    path = Path(source)
    try:
        with pymupdf.open(path) as document:
            if document.needs_pass or document.is_encrypted:
                return PdfType.ENCRYPTED_PDF
            pages_to_check = min(len(document), max_pages_to_check)
            if pages_to_check == 0:
                return PdfType.CORRUPTED_PDF
            text_pages = 0
            image_or_empty_pages = 0
            for index in range(pages_to_check):
                try:
                    page = document[index]
                    text = page.get_text("text")
                    images = page.get_images(full=True)
                except Exception:
                    image_or_empty_pages += 1
                    continue
                has_valid_text = _text_layer_looks_valid(text)
                if has_valid_text:
                    text_pages += 1
                if len(images) > 0 or not has_valid_text:
                    image_or_empty_pages += 1
            if text_pages == pages_to_check and image_or_empty_pages == 0:
                return PdfType.TEXT_PDF
            if text_pages == 0:
                return PdfType.IMAGE_ONLY_PDF
            return PdfType.MIXED_PDF
    except Exception:
        return PdfType.CORRUPTED_PDF


# 텍스트 layer looks valid 작업을 수행함
def _text_layer_looks_valid(text: str) -> bool:
    if len(text) < 10:
        return False
    control_chars = sum(1 for character in text if ord(character) < 32 and character not in "\n\r\t")
    broken_chars = text.count("�") + text.count("□")
    return control_chars / max(1, len(text)) < 0.02 and broken_chars / max(1, len(text)) < 0.02
