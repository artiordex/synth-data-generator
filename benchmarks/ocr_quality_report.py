# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_quality_report.py
# 경로: benchmarks/ocr_quality_report.py
# 목적: OCR 벤치마크 결과 리포트 및 품질 지표 산출 유틸리티를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Deterministic OCR quality report helpers for local benchmark fixtures.

The helpers intentionally avoid live OCR engines. They turn fixture OCR output
and known ground truth into auditable metrics so confidence can be used as a
review signal without being mistaken for accuracy.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from statistics import mean
from typing import Iterable

from ocr.evaluation.metrics import text_metrics


DATE_RE = re.compile(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}")
AMOUNT_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)\s*(?:원|KRW)")
NUMBER_RE = re.compile(r"(?=[A-Za-z0-9,./-]*\d)[A-Za-z0-9]+(?:[.,/-][A-Za-z0-9]+)*")
SPECIAL_RE = re.compile(r"[()\[\]{}:;/%#@+\-=□■✓✔]")
SUSPECT_NUMERIC_RE = re.compile(r"(?=[A-Za-z0-9,./-]*\d)[A-Za-z0-9,./-]*[OoIlS][A-Za-z0-9,./-]*")
SUSPECT_NUMERIC_CHARACTER_RE = re.compile(r"[OoIlS]")
LENIENT_DATE_RE = re.compile(r"[0-9OoIlS]{4}[-./][0-9OoIlS]{1,2}[-./][0-9OoIlS]{1,2}")
LENIENT_AMOUNT_RE = re.compile(r"(?:[0-9OoIlS]{1,3}(?:,[0-9OoIlS]{3})+|[0-9OoIlS]+)\s*(?:원|KRW)")


@dataclass(frozen=True)
class PageQualityFixture:
    """One synthetic OCR page with expected structure and rendered metadata."""

    page_no: int
    reference_text: str
    recognized_text: str
    confidence: float
    processing_time_ms: float
    expected_cell_count: int
    recognized_cell_count: int
    expected_image_count: int
    recognized_image_count: int
    rotation_deg: float = 0.0
    expected_merged_ranges: tuple[str, ...] = ()
    recognized_merged_ranges: tuple[str, ...] = ()
    expected_column_widths_pt: tuple[float, ...] = ()
    recognized_column_widths_pt: tuple[float, ...] = ()
    expected_relationship_ids: tuple[str, ...] = ()
    recognized_relationship_ids: tuple[str, ...] = ()


# 페이지 품질 record 구조를 생성 및 조립함
def build_page_quality_record(page: PageQualityFixture) -> dict[str, object]:
    """Return a flat per-page OCR quality record for JSON/Markdown reporting."""

    text = _text_quality(page.reference_text, page.recognized_text)
    structure = _ratio(page.recognized_cell_count, page.expected_cell_count)
    image = _ratio(page.recognized_image_count, page.expected_image_count)
    merge = _set_similarity(page.expected_merged_ranges, page.recognized_merged_ranges)
    width = _width_similarity(page.expected_column_widths_pt, page.recognized_column_widths_pt)
    relationship = _set_similarity(page.expected_relationship_ids, page.recognized_relationship_ids)
    visual = mean([image, merge, width, relationship])
    damage = damage_metrics(page.reference_text, page.recognized_text)
    empty_result_error = len(page.recognized_text) == 0
    review_required = (
        empty_result_error
        or text["character_accuracy"] < 0.95
        or structure < 0.95
        or visual < 0.95
        or page.confidence < 0.85
        or any(value > 0 for value in damage.values())
    )
    return {
        "page_no": page.page_no,
        "confidence": page.confidence,
        "confidence_is_accuracy": False,
        "text_length": len(page.recognized_text),
        "cell_count": page.recognized_cell_count,
        "image_count": page.recognized_image_count,
        "processing_time_ms": round(page.processing_time_ms, 2),
        "rotation_deg": page.rotation_deg,
        "empty_result_error": empty_result_error,
        "numeric_damage_count": damage["numeric_damage_count"],
        "date_damage_count": damage["date_damage_count"],
        "amount_damage_count": damage["amount_damage_count"],
        "special_character_damage_count": damage["special_character_damage_count"],
        "suspect_numeric_character_count": damage["suspect_numeric_character_count"],
        "text_fidelity": text["character_accuracy"],
        "structure_fidelity": structure,
        "visual_fidelity": visual,
        "cell_count_fidelity": structure,
        "image_count_fidelity": image,
        "merge_fidelity": merge,
        "width_fidelity": width,
        "relationship_fidelity": relationship,
        "meets_text_target_95": text["character_accuracy"] >= 0.95,
        "meets_structure_target_95": structure >= 0.95,
        "meets_visual_target_95": visual >= 0.95,
        "review_required": review_required,
        "review_reasons": _review_reasons(
            empty_result_error=empty_result_error,
            text_fidelity=text["character_accuracy"],
            structure_fidelity=structure,
            visual_fidelity=visual,
            confidence=page.confidence,
            damage=damage,
        ),
    }


# summarize 페이지 품질 작업을 수행함
def summarize_page_quality(records: Iterable[dict[str, object]]) -> dict[str, object]:
    """Summarize page records while keeping 95 percent goals dimension-specific."""

    rows = tuple(records)
    if not rows:
        return {
            "pages": 0,
            "confidence_is_accuracy": False,
            "text_fidelity": None,
            "structure_fidelity": None,
            "visual_fidelity": None,
            "meets_text_target_95": False,
            "meets_structure_target_95": False,
            "meets_visual_target_95": False,
            "review_page_count": 0,
            "empty_result_page_count": 0,
        }
    return {
        "pages": len(rows),
        "confidence_is_accuracy": False,
        "text_fidelity": round(mean(float(row["text_fidelity"]) for row in rows), 4),
        "structure_fidelity": round(mean(float(row["structure_fidelity"]) for row in rows), 4),
        "visual_fidelity": round(mean(float(row["visual_fidelity"]) for row in rows), 4),
        "meets_text_target_95": all(bool(row["meets_text_target_95"]) for row in rows),
        "meets_structure_target_95": all(bool(row["meets_structure_target_95"]) for row in rows),
        "meets_visual_target_95": all(bool(row["meets_visual_target_95"]) for row in rows),
        "review_page_count": sum(1 for row in rows if row["review_required"]),
        "empty_result_page_count": sum(1 for row in rows if row["empty_result_error"]),
        "total_numeric_damage_count": sum(int(row["numeric_damage_count"]) for row in rows),
        "total_date_damage_count": sum(int(row["date_damage_count"]) for row in rows),
        "total_amount_damage_count": sum(int(row["amount_damage_count"]) for row in rows),
        "total_special_character_damage_count": sum(int(row["special_character_damage_count"]) for row in rows),
    }


# damage 품질 지표 작업을 수행함
def damage_metrics(reference_text: str, recognized_text: str) -> dict[str, int]:
    """Count damage in fields that OCR commonly corrupts in public forms."""

    return {
        "numeric_damage_count": _numeric_damage_count(reference_text, recognized_text),
        "date_damage_count": _token_damage_count(DATE_RE, reference_text, recognized_text),
        "amount_damage_count": _token_damage_count(AMOUNT_RE, reference_text, recognized_text),
        "special_character_damage_count": _token_damage_count(SPECIAL_RE, reference_text, recognized_text),
        "suspect_numeric_character_count": sum(
            len(SUSPECT_NUMERIC_CHARACTER_RE.findall(token))
            for token in SUSPECT_NUMERIC_RE.findall(recognized_text)
        ),
    }


# 텍스트 품질 작업을 수행함
def _text_quality(reference_text: str, recognized_text: str) -> dict[str, float]:
    return {"character_accuracy": text_metrics(reference_text, recognized_text)["character_accuracy"]}


# 토큰 damage count 작업을 수행함
def _token_damage_count(pattern: re.Pattern[str], reference_text: str, recognized_text: str) -> int:
    reference = pattern.findall(reference_text)
    recognized = pattern.findall(recognized_text)
    return _ordered_token_damage_count(reference, recognized)


# numeric damage count 작업을 수행함
def _numeric_damage_count(reference_text: str, recognized_text: str) -> int:
    reference = _numeric_tokens_without_dates_or_amounts(reference_text)
    recognized = _numeric_tokens_without_dates_or_amounts(recognized_text)
    return _ordered_token_damage_count(reference, recognized)


# ordered 토큰 damage count 작업을 수행함
def _ordered_token_damage_count(reference: list[str], recognized: list[str]) -> int:
    missing = Counter(reference)
    extra = Counter(recognized)
    missing.subtract(recognized)
    extra.subtract(reference)
    return max(
        sum(count for count in missing.values() if count > 0),
        sum(count for count in extra.values() if count > 0),
    )


# numeric tokens without dates or amounts 작업을 수행함
def _numeric_tokens_without_dates_or_amounts(text: str) -> list[str]:
    excluded_spans = [
        match.span()
        for pattern in (DATE_RE, LENIENT_DATE_RE, AMOUNT_RE, LENIENT_AMOUNT_RE)
        for match in pattern.finditer(text)
    ]
    return [
        match.group(0)
        for match in NUMBER_RE.finditer(text)
        if not _overlaps_any(match.span(), excluded_spans)
    ]


# overlaps any 작업을 수행함
def _overlaps_any(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < other_end and end > other_start for other_start, other_end in spans)


# ratio 작업을 수행함
def _ratio(actual: int, expected: int) -> float:
    if expected <= 0:
        return 1.0 if actual == 0 else 0.0
    return max(0.0, min(1.0, actual / expected))


# similarity 속성 값을 설정 및 갱신함
def _set_similarity(expected: tuple[str, ...], actual: tuple[str, ...]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    expected_set = set(expected)
    actual_set = set(actual)
    return len(expected_set & actual_set) / len(expected_set)


# 너비 similarity 작업을 수행함
def _width_similarity(expected: tuple[float, ...], actual: tuple[float, ...]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    if len(expected) != len(actual):
        return 0.0
    scores = []
    for expected_width, actual_width in zip(expected, actual):
        if expected_width <= 0:
            scores.append(1.0 if actual_width == 0 else 0.0)
        else:
            scores.append(max(0.0, 1.0 - abs(expected_width - actual_width) / expected_width))
    return mean(scores)


# review reasons 작업을 수행함
def _review_reasons(
    *,
    empty_result_error: bool,
    text_fidelity: float,
    structure_fidelity: float,
    visual_fidelity: float,
    confidence: float,
    damage: dict[str, int],
) -> tuple[str, ...]:
    reasons = []
    if empty_result_error:
        reasons.append("empty_result")
    if text_fidelity < 0.95:
        reasons.append("text_fidelity_below_95")
    if structure_fidelity < 0.95:
        reasons.append("structure_fidelity_below_95")
    if visual_fidelity < 0.95:
        reasons.append("visual_fidelity_below_95")
    if confidence < 0.85:
        reasons.append("low_confidence")
    if any(value > 0 for value in damage.values()):
        reasons.append("numeric_date_amount_or_symbol_damage")
    return tuple(reasons)
