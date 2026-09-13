# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: inspection.py
# 경로: packages/ocr/ocr/pdf/inspection.py
# 목적: PDF 페이지 구조 및 메타데이터 품질 검사를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Page-level PDF inspection before OCR routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..pipeline.models import ErrorCode, PdfType
from .classification import classify_pdf
from .text_layer import PdfTextLayerQuality, evaluate_text_layer


@dataclass(frozen=True)
class PdfPageInspection:
    """Signals collected from one PDF page."""

    page_no: int
    width_pt: float
    height_pt: float
    text: str
    image_count: int
    image_coverage_ratio: float
    text_quality: PdfTextLayerQuality
    ocr_required: bool
    issues: tuple[ErrorCode, ...]


@dataclass(frozen=True)
class PdfInspectionResult:
    """PDF-level inspection result."""

    path: Path
    pdf_type: PdfType
    page_count: int
    pages: tuple[PdfPageInspection, ...]
    issues: tuple[ErrorCode, ...] = ()


# inspect PDF 문서 페이지 목록 작업을 수행함
def inspect_pdf_pages(source: str | Path) -> PdfInspectionResult:
    """Inspect all pages and decide which pages require OCR."""

    import pymupdf

    path = Path(source).expanduser().resolve()
    pdf_type = classify_pdf(path)
    if pdf_type == PdfType.CORRUPTED_PDF:
        return PdfInspectionResult(path=path, pdf_type=pdf_type, page_count=0, pages=(), issues=(ErrorCode.PDF_CORRUPTED,))
    if pdf_type == PdfType.ENCRYPTED_PDF:
        return PdfInspectionResult(path=path, pdf_type=pdf_type, page_count=0, pages=(), issues=(ErrorCode.PDF_ENCRYPTED,))

    pages: list[PdfPageInspection] = []
    with pymupdf.open(path) as document:
        for index in range(1, len(document) + 1):
            try:
                page = document[index - 1]
                text = page.get_text("text")
                image_infos = page.get_images(full=True)
                coverage = _image_coverage_ratio(page, image_infos)
                width, height = float(page.rect.width), float(page.rect.height)
            except Exception:
                pages.append(PdfPageInspection(
                    page_no=index, width_pt=0.0, height_pt=0.0, text="",
                    image_count=0, image_coverage_ratio=0.0,
                    text_quality=evaluate_text_layer(""), ocr_required=True,
                    issues=(ErrorCode.PDF_TEXT_LAYER_INVALID, ErrorCode.OCR_REQUIRED),
                ))
                continue
            quality = evaluate_text_layer(text)
            ocr_required = not quality.valid
            if coverage > 0.75 and quality.char_count < 30:
                ocr_required = True
            issues = list(quality.issues)
            if ocr_required and ErrorCode.OCR_REQUIRED not in issues:
                issues.append(ErrorCode.OCR_REQUIRED)
            pages.append(
                PdfPageInspection(
                    page_no=index,
                    width_pt=width,
                    height_pt=height,
                    text=text,
                    image_count=len(image_infos),
                    image_coverage_ratio=coverage,
                    text_quality=quality,
                    ocr_required=ocr_required,
                    issues=tuple(dict.fromkeys(issues)),
                )
            )
    return PdfInspectionResult(path=path, pdf_type=pdf_type, page_count=len(pages), pages=tuple(pages))


# 이미지 coverage ratio 작업을 수행함
def _image_coverage_ratio(page, image_infos: list[tuple]) -> float:
    page_area = float(page.rect.width * page.rect.height)
    if page_area <= 0 or not image_infos:
        return 0.0
    coverage = 0.0
    for info in image_infos:
        xref = info[0]
        for rect in page.get_image_rects(xref):
            coverage += float(rect.width * rect.height)
    return min(1.0, coverage / page_area)
