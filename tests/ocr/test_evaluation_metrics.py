# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_evaluation_metrics.py
# 경로: tests/ocr/test_evaluation_metrics.py
# 목적: CER, WER 등 OCR 평가 지표 계산 정합성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from ocr.evaluation.metrics import evaluate_ocr_page, text_metrics
from ocr.pipeline.models import BoundingBox, OCRPageResult, OCRStatus, OCRWord, PreprocessingProfile, confidence_stats


# 문자 정확도 uses cer not 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_character_accuracy_uses_cer_not_confidence():
    metrics = text_metrics("식약처 OCR 123", "식약처 OGR 123")

    assert metrics["cer"] > 0
    assert metrics["character_accuracy"] == 1 - metrics["cer"]


# insertions can exceed reference length 기능의 정상 동작 및 제약조건을 테스트함
def test_insertions_can_exceed_reference_length():
    metrics = text_metrics("a", "a b c d")
    assert metrics["cer"] == 6.0
    assert metrics["character_accuracy"] == -5.0
    assert metrics["word_accuracy"] == 1 - metrics["wer"]


# raw and normalized 텍스트 are evaluated separately 기능의 정상 동작 및 제약조건을 테스트함
def test_raw_and_normalized_text_are_evaluated_separately():
    words = (OCRWord("식약처", 0.99, BoundingBox(0, 0, 50, 20)),)
    mean, med = confidence_stats(words)
    page = OCRPageResult(
        page_no=1,
        raw_text="식약처\u0007 OCR",
        normalized_text="식약처 OCR",
        words=words,
        mean_confidence=mean,
        median_confidence=med,
        profile=PreprocessingProfile.STANDARD,
        status=OCRStatus.SUCCESS,
    )

    metrics = evaluate_ocr_page(page)

    assert page.raw_text != page.normalized_text
    assert metrics.character_accuracy is None
    assert metrics.mean_confidence == 0.99
    assert metrics.invalid_character_ratio > 0
