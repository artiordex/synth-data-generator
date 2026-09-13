# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: pipeline.py
# 경로: packages/ocr/ocr/pdf/pipeline.py
# 목적: 다중 페이지 PDF 문서 변환 및 OCR 파이프라인 처리를 총괄함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PDF OCR routing plan. OCR execution is deliberately separate."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path

from ..engine.base import OCRBackend
from ..pipeline.models import ErrorCode, OCRStatus, PdfType
from ..pipeline.models import OCRPageResult
from ..text.normalization import normalize_ocr_text
from .inspection import PdfInspectionResult, inspect_pdf_pages
from .rendering import DEFAULT_MAX_PIXELS, MAX_DPI, render_page_for_ocr


@dataclass(frozen=True)
class PdfPageOCRDecision:
    """Per-page route: native text or OCR fallback."""

    page_no: int
    use_native_text: bool
    ocr_required: bool
    status: OCRStatus
    issues: tuple[ErrorCode, ...]


@dataclass(frozen=True)
class PdfOCRPlan:
    """PDF routing plan before invoking OCR engines."""

    source: Path
    pdf_type: PdfType
    page_count: int
    decisions: tuple[PdfPageOCRDecision, ...]
    ocr_pages: tuple[int, ...]
    native_text_pages: tuple[int, ...]
    status: OCRStatus
    issues: tuple[ErrorCode, ...]
    inspection: PdfInspectionResult


@dataclass(frozen=True)
class PdfOCRAttempt:
    """Page-local attempt and requested DPI, including failed renders.

    quality_score is a confidence proxy, never ground-truth accuracy.
    """

    page_no: int
    attempt_no: int
    dpi: int
    page_result: OCRPageResult
    quality_score: float


@dataclass(frozen=True)
class PdfOCRExecutionResult:
    """PDF OCR execution result with native and OCR pages kept separate."""

    plan: PdfOCRPlan
    pages: tuple[OCRPageResult, ...]
    status: OCRStatus
    issues: tuple[ErrorCode, ...]
    attempts: tuple[PdfOCRAttempt, ...] = ()
    best_attempts: tuple[PdfOCRAttempt, ...] = ()


# plan PDF 문서 OCR 인식 작업을 수행함
def plan_pdf_ocr(source: str | Path) -> PdfOCRPlan:
    """Build a page-level OCR plan without running OCR."""

    inspection = inspect_pdf_pages(Path(source).expanduser().resolve())
    if inspection.issues:
        return PdfOCRPlan(
            source=inspection.path,
            pdf_type=inspection.pdf_type,
            page_count=inspection.page_count,
            decisions=(),
            ocr_pages=(),
            native_text_pages=(),
            status=OCRStatus.FAILED,
            issues=inspection.issues,
            inspection=inspection,
        )
    decisions = tuple(
        PdfPageOCRDecision(
            page_no=page.page_no,
            use_native_text=not page.ocr_required,
            ocr_required=page.ocr_required,
            status=OCRStatus.READY if page.ocr_required else OCRStatus.NOT_REQUIRED,
            issues=page.issues,
        )
        for page in inspection.pages
    )
    ocr_pages = tuple(decision.page_no for decision in decisions if decision.ocr_required)
    native_pages = tuple(decision.page_no for decision in decisions if decision.use_native_text)
    status = OCRStatus.READY if ocr_pages else OCRStatus.NOT_REQUIRED
    if inspection.pdf_type == PdfType.MIXED_PDF:
        status = OCRStatus.PARTIAL_SUCCESS if native_pages and ocr_pages else status
    return PdfOCRPlan(
        source=inspection.path,
        pdf_type=inspection.pdf_type,
        page_count=inspection.page_count,
        decisions=decisions,
        ocr_pages=ocr_pages,
        native_text_pages=native_pages,
        status=status,
        issues=tuple(sorted({issue for decision in decisions for issue in decision.issues}, key=lambda item: item.value)),
        inspection=inspection,
    )


# PDF 문서 OCR 인식 작업을 실행함
def run_pdf_ocr(
    source: str | Path,
    *,
    backend: OCRBackend,
    dpi: int = 300,
    max_attempts: int = 3,
    dpi_step: int = 100,
    min_confidence: float = 0.85,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> PdfOCRExecutionResult:
    """Run up to three increasing-DPI attempts per OCR page, capped at 600 DPI.

    Selection uses nonempty text, status and confidence, without ground truth.
    Pixel-budget rejection stops the page's retries before raster allocation.
    """

    import pymupdf

    if type(dpi) is not int or not 1 <= dpi <= MAX_DPI:
        raise ValueError(f"dpi must be an integer between 1 and {MAX_DPI}")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("max_attempts must be between 1 and 3")
    if type(dpi_step) is not int or dpi_step <= 0:
        raise ValueError("dpi_step must be a positive integer")
    if not math.isfinite(min_confidence) or not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1")
    if type(max_pixels) is not int or max_pixels <= 0:
        raise ValueError("max_pixels must be a positive integer")
    dpis = tuple(dict.fromkeys(min(MAX_DPI, dpi + i * dpi_step) for i in range(max_attempts)))
    plan = plan_pdf_ocr(source)
    if plan.status == OCRStatus.FAILED:
        return PdfOCRExecutionResult(plan=plan, pages=(), status=OCRStatus.FAILED, issues=plan.issues)

    results: list[OCRPageResult] = []
    attempts: list[PdfOCRAttempt] = []
    best_attempts: list[PdfOCRAttempt] = []
    with pymupdf.open(plan.source) as document:
        for page_inspection in plan.inspection.pages:
            if not page_inspection.ocr_required:
                results.append(
                    OCRPageResult(
                        page_no=page_inspection.page_no,
                        raw_text=page_inspection.text,
                        normalized_text=normalize_ocr_text(page_inspection.text),
                        words=(),
                        mean_confidence=0.0,
                        median_confidence=0.0,
                        engine="native_pdf_text",
                        status=OCRStatus.NOT_REQUIRED,
                    )
                )
                continue
            page_attempts = []
            for attempt_no, attempt_dpi in enumerate(dpis, start=1):
                error = ErrorCode.PDF_RENDER_FAILED
                try:
                    page = document[page_inspection.page_no - 1]
                    rendered = render_page_for_ocr(page, dpi=attempt_dpi, max_pixels=max_pixels)
                    error = ErrorCode.OCR_FAILED
                    result = backend.recognize_page(rendered, page_no=page_inspection.page_no)
                    issues = list(result.issues)
                    if not result.normalized_text.strip():
                        issues.append(ErrorCode.OCR_EMPTY_RESULT)
                    confidence = result.mean_confidence
                    if not math.isfinite(confidence) or confidence < min_confidence:
                        issues.append(ErrorCode.OCR_LOW_CONFIDENCE)
                    if result.status not in (OCRStatus.SUCCESS, OCRStatus.NOT_REQUIRED) and not issues:
                        issues.append(ErrorCode.OCR_FAILED)
                    result = replace(result, page_no=page_inspection.page_no,
                                     status=OCRStatus.FAILED if result.status == OCRStatus.FAILED else (
                                         OCRStatus.REVIEW_REQUIRED if issues else OCRStatus.SUCCESS),
                                     issues=tuple(dict.fromkeys(issues)))
                    score = max(0.0, min(1.0, confidence)) if math.isfinite(confidence) and result.normalized_text.strip() else 0.0
                except Exception:
                    result = OCRPageResult(
                        page_no=page_inspection.page_no, raw_text="", normalized_text="", words=(),
                        mean_confidence=0.0, median_confidence=0.0,
                        engine=backend.name, status=OCRStatus.FAILED, issues=(error,),
                    )
                    score = 0.0
                attempt = PdfOCRAttempt(page_inspection.page_no, attempt_no, attempt_dpi, result, score)
                page_attempts.append(attempt)
                attempts.append(attempt)
                if result.status == OCRStatus.SUCCESS or error == ErrorCode.PDF_RENDER_FAILED:
                    # Increasing DPI cannot fix an allocation or page-loading failure.
                    break
            best = max(page_attempts, key=lambda item: (
                item.page_result.status == OCRStatus.SUCCESS,
                item.page_result.status != OCRStatus.FAILED,
                bool(item.page_result.normalized_text.strip()), item.quality_score,
            ))
            best_attempts.append(best)
            results.append(best.page_result)

    issues = tuple(dict.fromkeys(issue for result in results for issue in result.issues))
    if results and all(result.status == OCRStatus.FAILED for result in results):
        status = OCRStatus.FAILED
    elif any(result.status not in (OCRStatus.SUCCESS, OCRStatus.NOT_REQUIRED) for result in results):
        status = OCRStatus.PARTIAL_SUCCESS if any(result.status in (OCRStatus.SUCCESS, OCRStatus.NOT_REQUIRED) for result in results) else OCRStatus.REVIEW_REQUIRED
    else:
        status = OCRStatus.SUCCESS if plan.ocr_pages else OCRStatus.NOT_REQUIRED
    return PdfOCRExecutionResult(plan=plan, pages=tuple(results), status=status, issues=issues,
                                 attempts=tuple(attempts), best_attempts=tuple(best_attempts))
