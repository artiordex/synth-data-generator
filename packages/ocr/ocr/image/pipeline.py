# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: pipeline.py
# 경로: packages/ocr/ocr/image/pipeline.py
# 목적: 이미지 전처리 및 OCR 엔진 실행 단일 이미지 처리 파이프라인을 실행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Separated image OCR pipeline."""

from __future__ import annotations

from dataclasses import replace
import logging
import time
from pathlib import Path

from ..engine.base import OCRBackend
from ..engine.tesseract import TesseractBackend
from ..evaluation.metrics import evaluate_ocr_page
from ..pipeline.models import ErrorCode, FileType, OCRAttempt, OCRDocumentResult, OCRPageResult, OCRStatus
from ..preprocessing.opencv import preprocess_image
from ..preprocessing.profiles import build_attempt_plan
from .inspection import inspect_image

logger = logging.getLogger(__name__)


# 이미지 OCR 인식 작업을 실행함
def run_image_ocr(
    source: str | Path,
    *,
    backend: OCRBackend | None = None,
    ground_truth: str | None = None,
    max_attempts: int = 7,
    target_accuracy: float = 0.95,
    min_quality_score: float = 0.90,
) -> OCRDocumentResult:
    """Run Image -> Inspection -> OpenCV -> OCR -> Evaluation -> Best Result."""

    path = Path(source)
    inspection = inspect_image(path)
    engine = backend if backend is not None else TesseractBackend()
    attempts: list[OCRAttempt] = []

    for attempt_no, config in enumerate(build_attempt_plan(inspection, max_attempts=max_attempts), start=1):
        started = time.perf_counter()
        image_area = None
        try:
            preprocessed = preprocess_image(path, config)
            image_area = preprocessed.width_px * preprocessed.height_px
            page_result = engine.recognize_page(preprocessed, page_no=1)
        except (RuntimeError, OSError) as exc:
            logger.warning("Image OCR attempt failed: %s", exc,
                           extra={"source": str(path), "attempt_no": attempt_no})
            page_result = OCRPageResult(
                page_no=1, raw_text="", normalized_text="", words=(),
                mean_confidence=0.0, median_confidence=0.0, engine=engine.name,
                profile=config.profile, psm=config.psm,
                status=OCRStatus.FAILED, issues=(ErrorCode.OCR_FAILED,),
            )
        metrics = evaluate_ocr_page(
            page_result,
            ground_truth=ground_truth,
            image_area=image_area,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        issues = list(page_result.issues)
        if not page_result.raw_text:
            issues.append(ErrorCode.OCR_EMPTY_RESULT)
        if metrics.character_accuracy is not None and metrics.character_accuracy < target_accuracy:
            issues.append(ErrorCode.OCR_LOW_CONFIDENCE)
        elif metrics.character_accuracy is None and metrics.quality_score < min_quality_score:
            issues.append(ErrorCode.OCR_LOW_CONFIDENCE)
        status = OCRStatus.SUCCESS if not issues else OCRStatus.RETRY_REQUIRED
        if attempt_no == max_attempts and issues:
            status = OCRStatus.REVIEW_REQUIRED
        if page_result.status == OCRStatus.FAILED:
            status = OCRStatus.FAILED
        page_result = replace(page_result, status=status, issues=tuple(dict.fromkeys(issues)))
        attempts.append(
            OCRAttempt(
                attempt_no=attempt_no,
                profile=config.profile,
                psm=config.psm,
                engine=engine.name,
                page_result=page_result,
                quality_score=metrics.quality_score,
                character_accuracy=metrics.character_accuracy,
                cer=metrics.cer,
                wer=metrics.wer,
                duration_ms=duration_ms,
            )
        )
        logger.info(
            "Image OCR attempt completed",
            extra={
                "source": str(path),
                "attempt_no": attempt_no,
                "profile": config.profile.value,
                "quality_score": metrics.quality_score,
            },
        )
        if not issues and metrics.character_accuracy is not None and metrics.character_accuracy >= target_accuracy:
            break
        if not issues and metrics.character_accuracy is None and metrics.quality_score >= min_quality_score:
            break

    result = OCRDocumentResult.from_attempts(
        source=path,
        file_type=FileType.IMAGE,
        attempts=attempts,
        ground_truth_available=ground_truth is not None,
    )
    if result.status == OCRStatus.RETRY_REQUIRED:
        return replace(result, status=OCRStatus.REVIEW_REQUIRED)
    return result
