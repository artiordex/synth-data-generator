# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: baseline.py
# 경로: packages/ocr/ocr/dataset/baseline.py
# 목적: 로컬 OCR 샘플 말뭉치에 대한 기준선 분석 및 오류 분류를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Reproducible baseline analysis for the local OCR sample corpus.

This module is evaluation-only.  It does not alter OCR output, preprocessing,
model selection, or the source dataset.  A prediction may cover several source
annotations; those annotations are represented as one match group while their
stable sequence and vendor ids remain attached to every error record.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math
import re
from typing import Any, Iterable, Mapping

from rapidfuzz.distance import Levenshtein

from ..pipeline.models import BoundingBox, OCRPageResult, OCRWord
from .models import OCRSample, SampleAnnotation
from .rules import intersection_over_union, order_annotations, preserve_source_text, scale_bbox


ERROR_TYPES = (
    "missing_text",
    "extra_text",
    "character_substitution",
    "character_deletion",
    "character_insertion",
    "whitespace_error",
    "digit_error",
    "date_error",
    "amount_error",
    "special_character_error",
    "bbox_mismatch",
    "reading_order_error",
    "high_confidence_wrong",
    "ocr_runtime_error",
)

DATE_RE = re.compile(r"\d{2,4}[./-]\d{1,2}[./-]\d{1,2}")
AMOUNT_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)\s*(?:원|KRW|₩|￦)")
SPECIAL_RE = re.compile(r"[\[\](){}/\\:;,\.\-_%+#@*=<>!?|·~]")


@dataclass(frozen=True)
class BaselineConfig:
    """Evaluation thresholds; no OCR behavior is controlled here."""

    confidence_threshold: float = 0.85
    bbox_iou_threshold: float = 0.85
    matching_iou_threshold: float = 0.05
    one_to_one_iou_threshold: float = 0.50
    top_n: int = 20

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        for name in (
            "confidence_threshold",
            "bbox_iou_threshold",
            "matching_iou_threshold",
            "one_to_one_iou_threshold",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.top_n < 1:
            raise ValueError("top_n must be at least one")


@dataclass(frozen=True)
class MatchGroup:
    """One OCR word matched to zero or more source annotations."""

    sample_id: str
    prediction_index: int | None
    annotation_indices: tuple[int, ...]
    annotation_sequences: tuple[int, ...]
    annotation_ids: tuple[Any, ...]
    ground_truth: str
    prediction: str
    confidence: float
    bbox_gt: BoundingBox | None
    bbox_pred: BoundingBox | None
    iou: float
    cer: float
    edit_distance: int
    error_types: tuple[str, ...]
    runtime_error: str | None = None

    # matched 여부 및 유효성을 판별함
    @property
    def is_matched(self) -> bool:
        return bool(self.annotation_indices and self.prediction_index is not None)

    # dict 형식으로 변환하여 반환함
    def to_dict(self, sample: OCRSample) -> dict[str, Any]:
        first_id = self.annotation_ids[0] if self.annotation_ids else None
        return {
            "sample_id": self.sample_id,
            "annotation_id": first_id,
            "annotation_ids": list(self.annotation_ids),
            "annotation_sequences": list(self.annotation_sequences),
            "image": str(sample.image_path) if sample.image_path else None,
            "ground_truth": self.ground_truth,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "bbox_gt": _box_to_list(self.bbox_gt),
            "bbox_pred": _box_to_list(self.bbox_pred),
            "iou": self.iou,
            "cer": self.cer,
            "edit_distance": self.edit_distance,
            "error_types": list(self.error_types),
            "runtime_error": self.runtime_error,
        }


@dataclass
class _Accumulator:
    sample_count: int = 0
    annotation_count: int = 0
    processed_sample_count: int = 0
    failed_sample_count: int = 0
    error_sample_count: int = 0
    total_gt_chars: int = 0
    total_edit_distance: int = 0
    matched_annotation_count: int = 0
    predicted_count: int = 0
    matched_group_count: int = 0
    one_to_one_match_count: int = 0
    one_to_one_ious: list[float] = field(default_factory=list)
    exact_group_count: int = 0
    bbox_ious: list[float] = field(default_factory=list)
    error_counts: Counter[str] = field(default_factory=Counter)
    error_sample_counts: Counter[str] = field(default_factory=Counter)
    high_confidence_count: int = 0
    high_confidence_wrong_count: int = 0
    format_stats: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"total": 0, "correct": 0}))
    dimension_stats: dict[str, dict[str, dict[str, int]]] = field(default_factory=lambda: defaultdict(dict))
    groups: list[MatchGroup] = field(default_factory=list)
    sample_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


# classify 텍스트 errors 작업을 수행함
def classify_text_errors(
    ground_truth: str,
    prediction: str,
    *,
    confidence: float = 0.0,
    confidence_threshold: float = 0.85,
    iou: float | None = None,
    bbox_iou_threshold: float = 0.85,
) -> tuple[str, ...]:
    """Classify independent error dimensions without changing either string."""

    expected = preserve_source_text(ground_truth)
    actual = preserve_source_text(prediction)
    errors: set[str] = set()
    if expected and not actual:
        errors.add("missing_text")
    if actual and not expected:
        errors.add("extra_text")
    for operation in Levenshtein.editops(expected, actual):
        if operation.tag == "replace":
            errors.add("character_substitution")
        elif operation.tag == "delete":
            errors.add("character_deletion")
        elif operation.tag == "insert":
            errors.add("character_insertion")
    if _whitespace_signature(expected) != _whitespace_signature(actual):
        errors.add("whitespace_error")
    if _digits(expected) != _digits(actual) and _digits(expected):
        errors.add("digit_error")
    if _tokens(expected, DATE_RE) != _tokens(actual, DATE_RE) and _tokens(expected, DATE_RE):
        errors.add("date_error")
    if _tokens(expected, AMOUNT_RE) != _tokens(actual, AMOUNT_RE) and _tokens(expected, AMOUNT_RE):
        errors.add("amount_error")
    if _tokens(expected, SPECIAL_RE) != _tokens(actual, SPECIAL_RE) and _tokens(expected, SPECIAL_RE):
        errors.add("special_character_error")
    if iou is not None and iou < bbox_iou_threshold:
        errors.add("bbox_mismatch")
    if expected != actual and confidence >= confidence_threshold:
        errors.add("high_confidence_wrong")
    return tuple(error for error in ERROR_TYPES if error in errors)


# analyze sample 페이지 작업을 수행함
def analyze_sample_page(
    sample: OCRSample,
    page: OCRPageResult | None,
    *,
    source_image_size: tuple[int, int] | None = None,
    config: BaselineConfig | None = None,
    runtime_error: str | None = None,
) -> tuple[dict[str, Any], tuple[MatchGroup, ...]]:
    """Return one sample summary and all match groups, including failures."""

    cfg = config or BaselineConfig()
    if runtime_error:
        return (
            {
                "sample_id": sample.sample_id,
                "source": str(sample.label_path),
                "image": str(sample.image_path) if sample.image_path else None,
                "status": "OCR_RUNTIME_ERROR",
                "runtime_error": runtime_error,
                "annotation_count": len(sample.annotations),
                "predicted_count": 0,
                "matched_annotation_count": 0,
                "matched_group_count": 0,
                "exact_group_count": 0,
                "character_accuracy": 0.0,
                "cer": 1.0 if sample.annotations else 0.0,
                "bbox_iou": 0.0,
                "detection_match_rate": 0.0,
                "annotation_coverage": 0.0,
                "one_to_one_match_count": 0,
                "one_to_one_detection_precision": 0.0,
                "one_to_one_detection_recall": 0.0,
                "one_to_one_detection_f1": 0.0,
                "one_to_one_bbox_iou": 0.0,
                "recognition_accuracy": 0.0,
                "error_count": 1,
            },
            (
                MatchGroup(
                    sample.sample_id, None, (), (), (), "", "", 0.0, None, None, 0.0, 0.0, 0, ("ocr_runtime_error",), runtime_error
                ),
            ),
        )
    if page is None:
        return analyze_sample_page(sample, None, config=cfg, runtime_error="OCR produced no page result")
    output_width, output_height = source_image_size or (sample.image_width, sample.image_height)
    annotations = list(sample.annotations)
    words = list(page.words)
    predicted_boxes = [
        scale_bbox(
            word.bbox,
            source_width=output_width,
            source_height=output_height,
            target_width=sample.image_width,
            target_height=sample.image_height,
        )
        for word in words
    ]
    one_to_one_matches, one_to_one_ious = _one_to_one_detection_matches(
        predicted_boxes,
        annotations,
        minimum_iou=cfg.one_to_one_iou_threshold,
    )
    one_to_one_precision = _ratio(one_to_one_matches, len(words))
    one_to_one_recall = _ratio(one_to_one_matches, len(annotations))
    one_to_one_f1 = _f1(one_to_one_precision, one_to_one_recall)
    used: set[int] = set()
    groups: list[MatchGroup] = []
    visual_rank = {item.sequence: rank for rank, item in enumerate(order_annotations(annotations))}
    for prediction_index, (word, predicted_box) in enumerate(zip(words, predicted_boxes)):
        candidates = [
            (index, annotation)
            for index, annotation in enumerate(annotations)
            if index not in used and _overlaps_or_contains(predicted_box, annotation, cfg.matching_iou_threshold)
        ]
        candidates.sort(key=lambda pair: (pair[1].bbox.y, pair[1].bbox.x, pair[1].sequence))
        if candidates:
            indexes = tuple(index for index, _ in candidates)
            for index in indexes:
                used.add(index)
            matched_annotations = tuple(annotation for _, annotation in candidates)
            target = "".join(preserve_source_text(annotation.text) for annotation in matched_annotations)
            gt_box = _union_boxes(annotation.bbox for annotation in matched_annotations)
            iou = intersection_over_union(predicted_box, gt_box)
            edit_distance = Levenshtein.distance(target, preserve_source_text(word.text))
            errors = classify_text_errors(
                target,
                word.text,
                confidence=float(word.confidence),
                confidence_threshold=cfg.confidence_threshold,
                iou=iou,
                bbox_iou_threshold=cfg.bbox_iou_threshold,
            )
            groups.append(MatchGroup(
                sample.sample_id,
                prediction_index,
                indexes,
                tuple(annotation.sequence for annotation in matched_annotations),
                tuple(annotation.annotation_id for annotation in matched_annotations),
                target,
                preserve_source_text(word.text),
                _safe_confidence(word.confidence),
                gt_box,
                predicted_box,
                iou,
                edit_distance / max(1, len(target)),
                edit_distance,
                errors,
            ))
        else:
            groups.append(MatchGroup(
                sample.sample_id,
                prediction_index,
                (), (), (), "", preserve_source_text(word.text), _safe_confidence(word.confidence),
                None, predicted_box, 0.0, 0.0, len(word.text), ("extra_text",),
            ))
    for index, annotation in enumerate(annotations):
        if index in used:
            continue
        text = preserve_source_text(annotation.text)
        groups.append(MatchGroup(
            sample.sample_id,
            None,
            (index,),
            (annotation.sequence,),
            (annotation.annotation_id,),
            text,
            "",
            0.0,
            annotation.bbox,
            None,
            0.0,
            1.0 if text else 0.0,
            len(text),
            classify_text_errors(text, ""),
        ))
    matched = [group for group in groups if group.is_matched]
    for position, group in enumerate(matched):
        if position and _group_rank(group, visual_rank) < _group_rank(matched[position - 1], visual_rank):
            for group_index, candidate in enumerate(groups):
                if candidate is group:
                    groups[group_index] = _with_error(group, "reading_order_error")
                    break
    matched = [group for group in groups if group.is_matched]
    total_chars = sum(len(group.ground_truth) for group in groups if group.annotation_indices)
    total_edits = sum(group.edit_distance for group in groups if group.annotation_indices)
    exact = sum(group.ground_truth == group.prediction for group in matched)
    matched_annotations = sum(len(group.annotation_indices) for group in matched)
    return (
        {
            "sample_id": sample.sample_id,
            "source": str(sample.label_path),
            "image": str(sample.image_path) if sample.image_path else None,
            "status": page.status.value,
            "engine": page.engine,
            "confidence": _safe_confidence(page.mean_confidence),
            "annotation_count": len(annotations),
            "predicted_count": len(words),
            "matched_annotation_count": matched_annotations,
            "matched_group_count": len(matched),
            "exact_group_count": exact,
            "character_accuracy": max(0.0, 1.0 - total_edits / max(1, total_chars)),
            "cer": total_edits / max(1, total_chars),
            "bbox_iou": sum(group.iou for group in matched) / len(matched) if matched else 0.0,
            "detection_match_rate": matched_annotations / len(annotations) if annotations else 1.0,
            "annotation_coverage": matched_annotations / len(annotations) if annotations else 1.0,
            "one_to_one_match_count": one_to_one_matches,
            "one_to_one_detection_precision": one_to_one_precision,
            "one_to_one_detection_recall": one_to_one_recall,
            "one_to_one_detection_f1": one_to_one_f1,
            "one_to_one_bbox_iou": _mean(one_to_one_ious),
            "one_to_one_ious": one_to_one_ious,
            "recognition_accuracy": exact / len(matched) if matched else 0.0,
            "error_count": sum(bool(group.error_types) for group in groups),
        },
        tuple(groups),
    )


# baseline 분석 리포트 구조를 생성 및 조립함
def build_baseline_report(
    sample_results: Iterable[tuple[OCRSample, Mapping[str, Any], Iterable[MatchGroup]]],
    *,
    dataset_audit: Mapping[str, Any] | None = None,
    config: BaselineConfig | None = None,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Aggregate sample analyses and return report JSON plus error JSONL rows."""

    cfg = config or BaselineConfig()
    acc = _Accumulator()
    for sample, row, groups in sample_results:
        acc.sample_count += 1
        acc.processed_sample_count += 1
        acc.annotation_count += int(row.get("annotation_count", len(sample.annotations)))
        if row.get("status") == "OCR_RUNTIME_ERROR":
            acc.failed_sample_count += 1
        group_list = tuple(groups)
        if any(group.error_types for group in group_list):
            acc.error_sample_count += 1
        acc.predicted_count += int(row.get("predicted_count", 0))
        acc.one_to_one_match_count += int(row.get("one_to_one_match_count", 0))
        acc.one_to_one_ious.extend(float(value) for value in row.get("one_to_one_ious", ()))
        sample_error_types: set[str] = set()
        for group in group_list:
            acc.groups.append(group)
            if group.annotation_indices:
                acc.total_gt_chars += len(group.ground_truth)
                acc.total_edit_distance += group.edit_distance
            for error in group.error_types:
                acc.error_counts[error] += 1
                sample_error_types.add(error)
            if group.is_matched:
                acc.matched_group_count += 1
                acc.matched_annotation_count += len(group.annotation_indices)
                acc.bbox_ious.append(group.iou)
                if group.ground_truth == group.prediction:
                    acc.exact_group_count += 1
                if group.confidence >= cfg.confidence_threshold:
                    acc.high_confidence_count += 1
                    if group.ground_truth != group.prediction:
                        acc.high_confidence_wrong_count += 1
                _add_format_stats(acc.format_stats, group.ground_truth, group.prediction)
                _add_dimension_stats(acc.dimension_stats, group)
            if group.error_types:
                error_row = group.to_dict(sample)
                if error_row["error_types"]:
                    acc.errors.append(error_row)
        for error in sample_error_types:
            acc.error_sample_counts[error] += 1
        row_copy = dict(row)
        row_copy["error_types"] = sorted({error for group in group_list for error in group.error_types})
        acc.sample_rows.append(row_copy)
    error_rows = tuple(acc.errors)
    report = {
        "dataset": dict(dataset_audit or {}),
        "configuration": {
            "confidence_threshold": cfg.confidence_threshold,
            "bbox_iou_threshold": cfg.bbox_iou_threshold,
            "matching_iou_threshold": cfg.matching_iou_threshold,
            "one_to_one_iou_threshold": cfg.one_to_one_iou_threshold,
            "top_n": cfg.top_n,
        },
        "metrics": {
            "sample_count": acc.sample_count,
            "processed_sample_count": acc.processed_sample_count,
            "annotation_count": acc.annotation_count,
            "predicted_count": acc.predicted_count,
            "failed_sample_count": acc.failed_sample_count,
            "error_sample_count": acc.error_sample_count,
            "exact_text_match_rate": _ratio(acc.exact_group_count, acc.matched_group_count),
            "character_accuracy": max(0.0, 1.0 - acc.total_edit_distance / max(1, acc.total_gt_chars)),
            "cer": acc.total_edit_distance / max(1, acc.total_gt_chars),
            "bbox_iou": _mean(acc.bbox_ious),
            "detection_match_rate": _ratio(acc.matched_annotation_count, acc.annotation_count),
            "annotation_coverage": _ratio(acc.matched_annotation_count, acc.annotation_count),
            "detection_precision": _ratio(acc.matched_group_count, acc.predicted_count),
            "one_to_one_detection_precision": _ratio(acc.one_to_one_match_count, acc.predicted_count),
            "one_to_one_detection_recall": _ratio(acc.one_to_one_match_count, acc.annotation_count),
            "one_to_one_detection_f1": _f1(
                _ratio(acc.one_to_one_match_count, acc.predicted_count),
                _ratio(acc.one_to_one_match_count, acc.annotation_count),
            ),
            "one_to_one_bbox_iou": _mean(acc.one_to_one_ious),
            "recognition_accuracy": _ratio(acc.exact_group_count, acc.matched_group_count),
            "high_confidence_prediction_count": acc.high_confidence_count,
            "high_confidence_wrong_count": acc.high_confidence_wrong_count,
            "high_confidence_wrong_rate": _ratio(acc.high_confidence_wrong_count, acc.high_confidence_count),
            "format_accuracy": {name: {**values, "accuracy": _ratio(values["correct"], values["total"])} for name, values in acc.format_stats.items()},
        },
        "numeric_date_amount_accuracy": {
            name: {**values, "accuracy": _ratio(values["correct"], values["total"])}
            for name, values in acc.format_stats.items()
            if name in {"digit", "date", "amount"}
        },
        "special_character_accuracy": acc.format_stats.get("special_character", {"total": 0, "correct": 0, "accuracy": 0.0}) | {
            "accuracy": _ratio(acc.format_stats.get("special_character", {}).get("correct", 0), acc.format_stats.get("special_character", {}).get("total", 0))
        },
        "whitespace_preservation_accuracy": _format_accuracy(acc.format_stats.get("whitespace", {"total": 0, "correct": 0})),
        "error_distribution": {
            "counts": dict(acc.error_counts),
            "sample_counts": dict(acc.error_sample_counts),
        },
        "per_file": {str(row.get("source")): row for row in acc.sample_rows},
        "per_image": {str(row.get("image")): row for row in acc.sample_rows},
        "per_annotation": list(error_rows),
        "by_text_length": _dimension_output(acc.dimension_stats.get("text_length", {})),
        "by_content_type": _dimension_output(acc.dimension_stats.get("content_type", {})),
        "samples": acc.sample_rows,
        "worst_cases": _worst_cases(acc.groups, acc.sample_rows, cfg.top_n),
        "improvement_priorities": _priorities(acc, cfg),
    }
    return report, error_rows


# baseline 마크다운 데이터를 타깃 포맷으로 렌더링함
def render_baseline_markdown(report: Mapping[str, Any]) -> str:
    """Render the stable human-readable baseline report."""

    metrics = report.get("metrics", {})
    numeric = report.get("numeric_date_amount_accuracy", {})
    errors = report.get("error_distribution", {}).get("counts", {})
    lines = [
        "# OCR Baseline Benchmark",
        "",
        "## Dataset",
        "",
        f"- Samples: {metrics.get('sample_count', 0)}",
        f"- Annotations: {metrics.get('annotation_count', 0)}",
        f"- Failed/runtime samples: {metrics.get('failed_sample_count', 0)}",
        "",
        "## Overall Metrics",
        "",
        _metric_line("Exact text match rate", metrics.get("exact_text_match_rate")),
        _metric_line("Character accuracy", metrics.get("character_accuracy")),
        _metric_line("CER", metrics.get("cer")),
        "",
        "## Detection Performance",
        "",
        _metric_line("BBox IoU", metrics.get("bbox_iou")),
        _metric_line("Detection match rate", metrics.get("detection_match_rate")),
        _metric_line("Annotation coverage", metrics.get("annotation_coverage")),
        _metric_line("Detection precision", metrics.get("detection_precision")),
        _metric_line("One-to-one detection precision", metrics.get("one_to_one_detection_precision")),
        _metric_line("One-to-one detection recall", metrics.get("one_to_one_detection_recall")),
        _metric_line("One-to-one detection F1", metrics.get("one_to_one_detection_f1")),
        _metric_line("One-to-one BBox IoU", metrics.get("one_to_one_bbox_iou")),
        "- Note: detection match rate is grouped annotation coverage; one-to-one metrics expose box granularity and over-segmentation separately.",
        "",
        "## Recognition Performance",
        "",
        _metric_line("Recognition accuracy", metrics.get("recognition_accuracy")),
        _metric_line("High-confidence wrong rate", metrics.get("high_confidence_wrong_rate")),
        "",
        "## Numeric / Date / Amount Accuracy",
        "",
    ]
    for name in ("digit", "date", "amount"):
        values = numeric.get(name, {})
        lines.append(f"- {name}: {_fmt(values.get('accuracy', 0.0))} ({values.get('correct', 0)}/{values.get('total', 0)})")
    lines += ["", "## Special Character Accuracy", "", _metric_line("Special character accuracy", report.get("special_character_accuracy", {}).get("accuracy")), "", "## Confidence Reliability", "", _metric_line("High-confidence wrong rate", metrics.get("high_confidence_wrong_rate")), f"- High-confidence wrong predictions: {metrics.get('high_confidence_wrong_count', 0)}", "", "## Error Distribution", "", "| Error | Count |", "|---|---:|"]
    for name, count in sorted(errors.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{name}` | {count} |")
    lines += ["", "## Worst Cases", ""]
    for name, rows in report.get("worst_cases", {}).items():
        lines.append(f"- {name}: {len(rows)} records")
        for row in rows[:3]:
            lines.append(f"  - `{row.get('sample_id')}` GT={row.get('ground_truth', '')!r} PRED={row.get('prediction', '')!r} errors={','.join(row.get('error_types', []))}")
    lines += ["", "## Improvement Priorities", ""]
    for priority in report.get("improvement_priorities", []):
        lines.append(f"1. {priority}")
    lines.append("")
    return "\n".join(lines)


# overlaps or contains 작업을 수행함
def _overlaps_or_contains(predicted: BoundingBox, annotation: SampleAnnotation, minimum_iou: float) -> bool:
    if intersection_over_union(predicted, annotation.bbox) >= minimum_iou:
        return True
    center_x = annotation.bbox.x + annotation.bbox.width / 2
    center_y = annotation.bbox.y + annotation.bbox.height / 2
    return predicted.x <= center_x <= predicted.x + predicted.width and predicted.y <= center_y <= predicted.y + predicted.height


# one to one detection matches 작업을 수행함
def _one_to_one_detection_matches(
    predicted_boxes: Iterable[BoundingBox],
    annotations: Iterable[SampleAnnotation],
    *,
    minimum_iou: float,
) -> tuple[int, tuple[float, ...]]:
    """Greedily match unique prediction/GT pairs by descending IoU."""
    predictions = tuple(predicted_boxes)
    targets = tuple(annotations)
    pairs = sorted(
        (
            (intersection_over_union(predicted, target.bbox), pred_index, gt_index)
            for pred_index, predicted in enumerate(predictions)
            for gt_index, target in enumerate(targets)
        ),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    used_predictions: set[int] = set()
    used_targets: set[int] = set()
    matched_ious: list[float] = []
    for iou, pred_index, gt_index in pairs:
        if iou < minimum_iou:
            break
        if pred_index in used_predictions or gt_index in used_targets:
            continue
        used_predictions.add(pred_index)
        used_targets.add(gt_index)
        matched_ious.append(iou)
    return len(matched_ious), tuple(matched_ious)


# union boxes 작업을 수행함
def _union_boxes(boxes: Iterable[BoundingBox]) -> BoundingBox:
    values = tuple(boxes)
    left = min(box.x for box in values)
    top = min(box.y for box in values)
    right = max(box.x + box.width for box in values)
    bottom = max(box.y + box.height for box in values)
    return BoundingBox(left, top, right - left, bottom - top)


# with error 작업을 수행함
def _with_error(group: MatchGroup, error: str) -> MatchGroup:
    errors = tuple(error_name for error_name in ERROR_TYPES if error_name in set(group.error_types) | {error})
    return MatchGroup(group.sample_id, group.prediction_index, group.annotation_indices, group.annotation_sequences, group.annotation_ids, group.ground_truth, group.prediction, group.confidence, group.bbox_gt, group.bbox_pred, group.iou, group.cer, group.edit_distance, errors, group.runtime_error)


# group rank 작업을 수행함
def _group_rank(group: MatchGroup, visual_rank: Mapping[int, int]) -> int:
    return min((visual_rank.get(sequence, sequence) for sequence in group.annotation_sequences), default=10**9)


# tokens 작업을 수행함
def _tokens(value: str, pattern: re.Pattern[str]) -> tuple[str, ...]:
    return tuple(pattern.findall(value))


# digits 작업을 수행함
def _digits(value: str) -> str:
    return "".join(re.findall(r"\d", value))


# whitespace signature 작업을 수행함
def _whitespace_signature(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\s", value))


# safe 인식 신뢰도 작업을 수행함
def _safe_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score)) if math.isfinite(score) else 0.0


# box to list 작업을 수행함
def _box_to_list(box: BoundingBox | None) -> list[int] | None:
    return [box.x, box.y, box.width, box.height] if box else None


# ratio 작업을 수행함
def _ratio(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator if denominator else 0.0


# f1 작업을 수행함
def _f1(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


# mean 작업을 수행함
def _mean(values: Iterable[float]) -> float:
    values = tuple(values)
    return sum(values) / len(values) if values else 0.0


# format 정확도 작업을 수행함
def _format_accuracy(values: Mapping[str, int]) -> dict[str, float | int]:
    return {"total": values.get("total", 0), "correct": values.get("correct", 0), "accuracy": _ratio(values.get("correct", 0), values.get("total", 0))}


# format stats 항목을 목록에 추가함
def _add_format_stats(stats: dict[str, dict[str, int]], expected: str, actual: str) -> None:
    checks = {
        "digit": (_digits(expected), _digits(actual)),
        "date": (_tokens(expected, DATE_RE), _tokens(actual, DATE_RE)),
        "amount": (_tokens(expected, AMOUNT_RE), _tokens(actual, AMOUNT_RE)),
        "special_character": (_tokens(expected, SPECIAL_RE), _tokens(actual, SPECIAL_RE)),
        "whitespace": (_whitespace_signature(expected), _whitespace_signature(actual)),
    }
    for name, (wanted, found) in checks.items():
        if not wanted:
            continue
        stats[name]["total"] += 1
        stats[name]["correct"] += int(wanted == found)


# dimension stats 항목을 목록에 추가함
def _add_dimension_stats(stats: dict[str, dict[str, dict[str, int]]], group: MatchGroup) -> None:
    length = len(group.ground_truth)
    bucket = "0" if length == 0 else "1" if length == 1 else "2-5" if length <= 5 else "6-10" if length <= 10 else "11-20" if length <= 20 else "21+"
    _bucket_add(stats["text_length"], bucket, group)
    for name, present in (
        ("digit", bool(_digits(group.ground_truth))),
        ("date", bool(_tokens(group.ground_truth, DATE_RE))),
        ("amount", bool(_tokens(group.ground_truth, AMOUNT_RE))),
        ("special_character", bool(_tokens(group.ground_truth, SPECIAL_RE))),
    ):
        if present:
            _bucket_add(stats["content_type"], name, group)


# bucket add 작업을 수행함
def _bucket_add(target: dict[str, dict[str, int]], name: str, group: MatchGroup) -> None:
    values = target.setdefault(name, {"total": 0, "correct": 0, "characters": 0, "edit_distance": 0})
    values["total"] += 1
    values["correct"] += int(group.ground_truth == group.prediction)
    values["characters"] += len(group.ground_truth)
    values["edit_distance"] += group.edit_distance


# dimension output 작업을 수행함
def _dimension_output(values: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            **dict(row),
            "accuracy": _ratio(row.get("correct", 0), row.get("total", 0)),
            "cer": _ratio(row.get("edit_distance", 0), row.get("characters", 0)),
        }
        for name, row in values.items()
    }


# worst cases 작업을 수행함
def _worst_cases(groups: Iterable[MatchGroup], sample_rows: Iterable[Mapping[str, Any]], top_n: int) -> dict[str, list[dict[str, Any]]]:
    groups = tuple(groups)
    sample_by_id = {row.get("sample_id"): row for row in sample_rows}
    rows = []
    for group in groups:
        sample_row = sample_by_id.get(group.sample_id, {})
        row = {
            "sample_id": group.sample_id,
            "ground_truth": group.ground_truth,
            "prediction": group.prediction,
            "confidence": group.confidence,
            "cer": group.cer,
            "iou": group.iou,
            "error_types": list(group.error_types),
            "bbox_gt": _box_to_list(group.bbox_gt),
            "bbox_pred": _box_to_list(group.bbox_pred),
            "image": sample_row.get("image"),
        }
        rows.append(row)
    return {
        "highest_cer": sorted(rows, key=lambda row: (-row["cer"], row["sample_id"]))[:top_n],
        "lowest_bbox_iou": sorted(rows, key=lambda row: (row["iou"], row["sample_id"]))[:top_n],
        "high_confidence_wrong": [row for row in sorted(rows, key=lambda row: (-row["confidence"], -row["cer"])) if "high_confidence_wrong" in row["error_types"]][:top_n],
        "digit_errors": [row for row in rows if "digit_error" in row["error_types"]][:top_n],
        "date_errors": [row for row in rows if "date_error" in row["error_types"]][:top_n],
        "amount_errors": [row for row in rows if "amount_error" in row["error_types"]][:top_n],
        "special_character_errors": [row for row in rows if "special_character_error" in row["error_types"]][:top_n],
    }


# priorities 작업을 수행함
def _priorities(acc: _Accumulator, config: BaselineConfig) -> list[str]:
    priorities: list[tuple[float, str]] = []
    if acc.failed_sample_count:
        priorities.append((100.0, "OCR runtime failures must be made reproducible and isolated before accuracy tuning."))
    bbox = _mean(acc.bbox_ious)
    recognition = _ratio(acc.exact_group_count, acc.matched_group_count)
    if bbox < 0.85:
        priorities.append((90.0 - bbox, f"Detection geometry is the first bottleneck: mean bbox IoU is {_fmt(bbox)}."))
    if recognition < 0.90:
        priorities.append((80.0 - recognition, f"Recognition is the next bottleneck: exact matched-region accuracy is {_fmt(recognition)}."))
    if acc.high_confidence_wrong_count:
        priorities.append((70.0, f"Confidence calibration/review gating needs attention: {acc.high_confidence_wrong_count} high-confidence wrong predictions."))
    for name, label in (("digit_error", "digits"), ("date_error", "dates"), ("amount_error", "amounts"), ("special_character_error", "special characters"), ("whitespace_error", "whitespace")):
        if acc.error_counts[name]:
            priorities.append((60.0 - acc.error_counts[name] / max(1, acc.matched_group_count), f"Preserve {label}: {acc.error_counts[name]} {name} cases were detected."))
    if not priorities:
        priorities.append((1.0, "No measurable baseline bottleneck was found; expand the held-out sample set."))
    return [text for _, text in sorted(priorities, reverse=True)]


# fmt 작업을 수행함
def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.2%}"


# 평가 지표 line 작업을 수행함
def _metric_line(label: str, value: Any) -> str:
    return f"- {label}: {_fmt(value)}"
