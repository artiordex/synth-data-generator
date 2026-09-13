# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_baseline_benchmark.py
# 경로: tests/ocr/test_baseline_benchmark.py
# 목적: OCR 베이스라인 벤치마크 및 오류 분류 체계를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Tests for baseline metrics and error taxonomy."""

from __future__ import annotations

from pathlib import Path

from ocr.dataset.baseline import (
    BaselineConfig,
    analyze_sample_page,
    build_baseline_report,
    classify_text_errors,
    render_baseline_markdown,
)
from ocr.dataset.models import OCRSample, SampleAnnotation
from ocr.pipeline.models import (
    BoundingBox,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessingProfile,
)


# sample 작업을 수행함
def _sample(*texts: str) -> OCRSample:
    annotations = tuple(
        SampleAnnotation(index, index, text, BoundingBox(10 + index * 60, 10, 50, 20), "rectangle", "textType1")
        for index, text in enumerate(texts)
    )
    return OCRSample("sample-1", Path("sample.json"), Path("sample.jpg"), "sample.jpg", 200, 100, {}, annotations)


# 페이지 작업을 수행함
def _page(*words: tuple[str, float, tuple[int, int, int, int]]) -> OCRPageResult:
    records = tuple(OCRWord(text, confidence, BoundingBox(*bbox)) for text, confidence, bbox in words)
    return OCRPageResult(
        page_no=1,
        raw_text=" ".join(word.text for word in records),
        normalized_text=" ".join(word.text for word in records),
        words=records,
        mean_confidence=sum(word.confidence for word in records) / len(records) if records else 0.0,
        median_confidence=0.0,
        engine="fake",
        profile=PreprocessingProfile.STANDARD,
        status=OCRStatus.SUCCESS,
    )


# error taxonomy detects format whitespace and 인식 신뢰도 errors 기능의 정상 동작 및 제약조건을 테스트함
def test_error_taxonomy_detects_format_whitespace_and_confidence_errors():
    errors = classify_text_errors(
        "2026-09-11 금액 1,000원 [A-01]",
        "2026-09-12 금액 1,00O원 [A01]",
        confidence=0.98,
    )

    assert "digit_error" in errors
    assert "date_error" in errors
    assert "amount_error" in errors
    assert "special_character_error" in errors
    assert "high_confidence_wrong" in errors


# 문자 edit types and whitespace are separate 기능의 정상 동작 및 제약조건을 테스트함
def test_character_edit_types_and_whitespace_are_separate():
    errors = classify_text_errors("가 나", "가  낙")

    assert "character_substitution" in errors
    assert "whitespace_error" in errors
    assert "character_insertion" in classify_text_errors("가", "가나")
    assert "character_deletion" in classify_text_errors("가나", "가")


# empty prediction creates missing 텍스트 error and 분석 리포트 sections 기능의 정상 동작 및 제약조건을 테스트함
def test_empty_prediction_creates_missing_text_error_and_report_sections():
    sample = _sample("가", "2026-09-11")
    row, groups = analyze_sample_page(sample, _page())
    report, errors = build_baseline_report(((sample, row, groups),), config=BaselineConfig())
    markdown = render_baseline_markdown(report)

    assert row["detection_match_rate"] == 0.0
    assert all("missing_text" in group.error_types for group in groups)
    assert len(errors) == 2
    assert report["metrics"]["cer"] == 1.0
    assert list(report["per_file"]) == ["sample.json"]
    assert list(report["per_image"]) == ["sample.jpg"]
    assert len(report["per_annotation"]) == 2
    assert "## Numeric / Date / Amount Accuracy" in markdown
    assert "## Improvement Priorities" in markdown


# exact match has zero cer and 바운딩 박스 match 기능의 정상 동작 및 제약조건을 테스트함
def test_exact_match_has_zero_cer_and_bbox_match():
    sample = _sample("가")
    row, groups = analyze_sample_page(sample, _page(("가", 0.99, (10, 10, 50, 20))))

    assert row["character_accuracy"] == 1.0
    assert row["cer"] == 0.0
    assert row["recognition_accuracy"] == 1.0
    assert row["bbox_iou"] == 1.0
    assert groups[0].error_types == ()


# aspect 재시도 기하 좌표 can be evaluated in transformed space 기능의 정상 동작 및 제약조건을 테스트함
def test_aspect_retry_coordinates_can_be_evaluated_in_transformed_space():
    sample = _sample("가")
    page = _page(("가", 0.99, (12, 10, 63, 20)))
    row, groups = analyze_sample_page(sample, page, source_image_size=(250, 100))

    assert row["recognition_accuracy"] == 1.0
    assert row["bbox_iou"] > 0.95
    assert groups[0].error_types == ()


# grouped coverage is separate from one to one detection 품질 지표 기능의 정상 동작 및 제약조건을 테스트함
def test_grouped_coverage_is_separate_from_one_to_one_detection_metrics():
    sample = _sample("가", "나")
    page = _page(("가나", 0.95, (10, 10, 110, 20)))

    row, groups = analyze_sample_page(sample, page)
    report, _ = build_baseline_report(((sample, row, groups),))
    metrics = report["metrics"]

    assert row["annotation_coverage"] == 1.0
    assert row["detection_match_rate"] == 1.0
    assert row["one_to_one_detection_recall"] == 0.0
    assert metrics["annotation_coverage"] == 1.0
    assert metrics["one_to_one_detection_f1"] == 0.0
    assert "grouped annotation coverage" in render_baseline_markdown(report)


# one to one detection 품질 지표 require unique boxes 기능의 정상 동작 및 제약조건을 테스트함
def test_one_to_one_detection_metrics_require_unique_boxes():
    sample = _sample("가", "나")
    page = _page(
        ("가", 0.95, (10, 10, 50, 20)),
        ("나", 0.95, (70, 10, 50, 20)),
    )

    row, _ = analyze_sample_page(sample, page)

    assert row["one_to_one_match_count"] == 2
    assert row["one_to_one_detection_precision"] == 1.0
    assert row["one_to_one_detection_recall"] == 1.0
    assert row["one_to_one_detection_f1"] == 1.0
    assert row["one_to_one_bbox_iou"] == 1.0
