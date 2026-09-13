# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_quality_measurement_contract.py
# 경로: tests/ocr/test_quality_measurement_contract.py
# 목적: OCR 품질 측정 규격 및 계약 조건 준수 여부를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.ocr_quality_report import (
    PageQualityFixture,
    build_page_quality_record,
    damage_metrics,
    summarize_page_quality,
)
from benchmarks.ocr_synthetic_benchmark import _summarize
from ocr.evaluation.metrics import text_metrics


# 페이지 품질 record contains required operational 품질 지표 기능의 정상 동작 및 제약조건을 테스트함
def test_page_quality_record_contains_required_operational_metrics() -> None:
    record = build_page_quality_record(
        PageQualityFixture(
            page_no=2,
            reference_text="접수일자: 2026-09-11\n수수료: 12,300원\n□ 미선택 / ■ 선택",
            recognized_text="접수일자: 2026-09-11\n수수료: 12,300원\n□ 미선택 / ■ 선택",
            confidence=0.91,
            processing_time_ms=184.321,
            expected_cell_count=12,
            recognized_cell_count=12,
            expected_image_count=1,
            recognized_image_count=1,
            rotation_deg=-0.4,
            expected_merged_ranges=("A1:D1",),
            recognized_merged_ranges=("A1:D1",),
            expected_column_widths_pt=(72.0, 120.0, 96.0, 96.0),
            recognized_column_widths_pt=(72.0, 120.0, 96.0, 96.0),
            expected_relationship_ids=("rIdSeal",),
            recognized_relationship_ids=("rIdSeal",),
        )
    )

    assert record["page_no"] == 2
    assert record["confidence"] == 0.91
    assert record["confidence_is_accuracy"] is False
    assert record["text_length"] > 0
    assert record["cell_count"] == 12
    assert record["image_count"] == 1
    assert record["processing_time_ms"] == 184.32
    assert record["rotation_deg"] == -0.4
    assert record["empty_result_error"] is False
    assert record["numeric_damage_count"] == 0
    assert record["date_damage_count"] == 0
    assert record["amount_damage_count"] == 0
    assert record["special_character_damage_count"] == 0
    assert record["meets_text_target_95"] is True
    assert record["meets_structure_target_95"] is True
    assert record["meets_visual_target_95"] is True


# high 인식 신뢰도 does not hide numeric date amount or symbol damage 기능의 정상 동작 및 제약조건을 테스트함
def test_high_confidence_does_not_hide_numeric_date_amount_or_symbol_damage() -> None:
    record = build_page_quality_record(
        PageQualityFixture(
            page_no=1,
            reference_text="허가번호: MFDS-2026-09\n시험일자: 2026-09-11\n금액: 10,000원\n[✓]",
            recognized_text="허가번호: MFDS-2O26-O9\n시험일자: 2026-O9-l1\n금액: 1O,OOO원\n[ ]",
            confidence=0.99,
            processing_time_ms=72.0,
            expected_cell_count=8,
            recognized_cell_count=8,
            expected_image_count=0,
            recognized_image_count=0,
        )
    )

    assert record["confidence"] == 0.99
    assert record["confidence_is_accuracy"] is False
    assert record["numeric_damage_count"] > 0
    assert record["date_damage_count"] > 0
    assert record["amount_damage_count"] > 0
    assert record["special_character_damage_count"] > 0
    assert record["suspect_numeric_character_count"] > 0
    assert record["meets_text_target_95"] is False
    assert record["review_required"] is True
    assert "numeric_date_amount_or_symbol_damage" in record["review_reasons"]


# empty OCR 인식 결과 is a measurable 페이지 error 기능의 정상 동작 및 제약조건을 테스트함
def test_empty_ocr_result_is_a_measurable_page_error() -> None:
    record = build_page_quality_record(
        PageQualityFixture(
            page_no=3,
            reference_text="빈 결과가 아니어야 하는 본문",
            recognized_text="",
            confidence=0.0,
            processing_time_ms=41.0,
            expected_cell_count=4,
            recognized_cell_count=0,
            expected_image_count=0,
            recognized_image_count=0,
        )
    )

    assert record["text_length"] == 0
    assert record["empty_result_error"] is True
    assert record["cell_count_fidelity"] == 0.0
    assert record["review_required"] is True
    assert {"empty_result", "low_confidence", "structure_fidelity_below_95"} <= set(record["review_reasons"])


# 95 percent goal is 분할 into 텍스트 structure and visual targets 기능의 정상 동작 및 제약조건을 테스트함
def test_95_percent_goal_is_split_into_text_structure_and_visual_targets() -> None:
    page = PageQualityFixture(
        page_no=4,
        reference_text="식약처 문서 변환",
        recognized_text="식약처 문서 변환",
        confidence=0.88,
        processing_time_ms=63.0,
        expected_cell_count=10,
        recognized_cell_count=9,
        expected_image_count=2,
        recognized_image_count=2,
        expected_merged_ranges=("A1:C1", "A2:A3"),
        recognized_merged_ranges=("A1:C1",),
        expected_column_widths_pt=(60.0, 120.0, 120.0),
        recognized_column_widths_pt=(60.0, 120.0, 90.0),
        expected_relationship_ids=("rIdLogo", "rIdSeal"),
        recognized_relationship_ids=("rIdLogo",),
    )
    record = build_page_quality_record(page)

    assert record["text_fidelity"] == 1.0
    assert record["structure_fidelity"] == 0.9
    assert record["visual_fidelity"] < 0.95
    assert record["meets_text_target_95"] is True
    assert record["meets_structure_target_95"] is False
    assert record["meets_visual_target_95"] is False
    assert {"structure_fidelity_below_95", "visual_fidelity_below_95"} <= set(record["review_reasons"])


# 요약 정보 keeps review signal separate from 정확도 claim 기능의 정상 동작 및 제약조건을 테스트함
def test_summary_keeps_review_signal_separate_from_accuracy_claim() -> None:
    clean = build_page_quality_record(
        PageQualityFixture(
            page_no=1,
            reference_text="정상",
            recognized_text="정상",
            confidence=0.96,
            processing_time_ms=10.0,
            expected_cell_count=1,
            recognized_cell_count=1,
            expected_image_count=0,
            recognized_image_count=0,
        )
    )
    review = build_page_quality_record(
        PageQualityFixture(
            page_no=2,
            reference_text="2026-09-11",
            recognized_text="2O26-O9-l1",
            confidence=0.98,
            processing_time_ms=11.0,
            expected_cell_count=1,
            recognized_cell_count=1,
            expected_image_count=0,
            recognized_image_count=0,
        )
    )

    summary = summarize_page_quality([clean, review])

    assert summary["pages"] == 2
    assert summary["confidence_is_accuracy"] is False
    assert summary["review_page_count"] == 1
    assert summary["total_date_damage_count"] == 1
    assert summary["meets_text_target_95"] is False


# 텍스트 충실도 matches actual OCR 인식 텍스트 품질 지표 기능의 정상 동작 및 제약조건을 테스트함
def test_text_fidelity_matches_actual_ocr_text_metrics() -> None:
    page = PageQualityFixture(
        page_no=6,
        reference_text="a",
        recognized_text="a b c d",
        confidence=0.99,
        processing_time_ms=9.0,
        expected_cell_count=0,
        recognized_cell_count=0,
        expected_image_count=0,
        recognized_image_count=0,
    )
    record = build_page_quality_record(page)

    assert record["text_fidelity"] == text_metrics("a", "a b c d")["character_accuracy"]
    assert record["text_fidelity"] == -5.0
    assert record["meets_text_target_95"] is False


# damage 평가 지표 reports each sensitive 토큰 family 기능의 정상 동작 및 제약조건을 테스트함
def test_damage_metric_reports_each_sensitive_token_family() -> None:
    damage = damage_metrics(
        "날짜 2026-09-11 금액 10,000원 코드 A-123 [✓]",
        "날짜 2026-O9-l1 금액 1O,OOO원 코드 A-l23 [ ]",
    )

    assert damage == {
        "numeric_damage_count": 1,
        "date_damage_count": 1,
        "amount_damage_count": 1,
        "special_character_damage_count": 1,
        "suspect_numeric_character_count": 7,
    }


# damage 평가 지표 does not count unchanged tokens or double count dates and amounts 기능의 정상 동작 및 제약조건을 테스트함
def test_damage_metric_does_not_count_unchanged_tokens_or_double_count_dates_and_amounts() -> None:
    assert damage_metrics(
        "일자 2026-09-11 금액 10,000원 코드 A-123",
        "일자 2026-09-11 금액 10,000원 코드 A-123",
    ) == {
        "numeric_damage_count": 0,
        "date_damage_count": 0,
        "amount_damage_count": 0,
        "special_character_damage_count": 0,
        "suspect_numeric_character_count": 0,
    }
    damaged = damage_metrics(
        "일자 2026-09-11 금액 10,000원 코드 A-123",
        "일자 2026-O9-l1 금액 1O,OOO원 코드 A-123",
    )

    assert damaged["date_damage_count"] == 1
    assert damaged["amount_damage_count"] == 1
    assert damaged["numeric_damage_count"] == 0


# benchmark 요약 정보 does not record empty 결과 as success 기능의 정상 동작 및 제약조건을 테스트함
def test_benchmark_summary_does_not_record_empty_result_as_success() -> None:
    empty_page_quality = build_page_quality_record(
        PageQualityFixture(
            page_no=1,
            reference_text="식약처 OCR 123",
            recognized_text="",
            confidence=0.0,
            processing_time_ms=12.0,
            expected_cell_count=0,
            recognized_cell_count=0,
            expected_image_count=0,
            recognized_image_count=0,
        )
    )
    report = _summarize([
        {
            "name": "empty.png",
            "family": "Image",
            "category": "Empty Result",
            "character_accuracy": 0.0,
            "duration_ms": 12.0,
            "attempts": 5,
            "status": "REVIEW_REQUIRED",
            "routing_pass": False,
            "page_quality": empty_page_quality,
        }
    ])

    assert report["overall"]["pass_rate"] == 0.0
    assert report["overall"]["review_rate"] == 1.0
    assert report["overall"]["routing_pass_rate"] == 0.0
    assert report["quality_contract"]["empty_result_page_count"] == 1
    assert report["quality_contract"]["review_page_count"] == 1
