# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: comparison.py
# 경로: packages/ocr/ocr/dataset/comparison.py
# 목적: OCR 벤치마크 실행 전후의 성능 지표 비교 및 검증을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Before/after comparison for OCR benchmark runs."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping


TARGETS = OrderedDict(
    (
        ("bbox_iou", ("minimum", 0.85)),
        ("detection_match_rate", ("minimum", 0.95)),
        ("whitespace_preservation_accuracy", ("minimum", 0.80)),
        ("date_accuracy", ("minimum", 0.85)),
        ("character_deletion_reduction", ("reduction", 0.50)),
        ("missing_text_reduction", ("reduction", 0.50)),
    )
)


# phase2 comparison 구조를 생성 및 조립함
def build_phase2_comparison(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Build a serializable metric/error delta report without altering inputs."""

    before_metrics = before.get("metrics", {})
    after_metrics = after.get("metrics", {})
    before_format = before.get("numeric_date_amount_accuracy", {})
    after_format = after.get("numeric_date_amount_accuracy", {})
    before_errors = before.get("error_distribution", {}).get("counts", {})
    after_errors = after.get("error_distribution", {}).get("counts", {})
    metric_names = (
        "exact_text_match_rate", "character_accuracy", "cer", "bbox_iou",
        "detection_match_rate", "annotation_coverage", "detection_precision",
        "one_to_one_detection_precision", "one_to_one_detection_recall",
        "one_to_one_detection_f1", "one_to_one_bbox_iou",
        "recognition_accuracy", "high_confidence_wrong_rate",
    )
    metrics: dict[str, dict[str, float]] = {}
    for name in metric_names:
        old, new = _number(before_metrics.get(name)), _number(after_metrics.get(name))
        metrics[name] = {"before": old, "after": new, "delta": new - old}
    for name in ("digit", "date", "amount"):
        old = _number(before_format.get(name, {}).get("accuracy"))
        new = _number(after_format.get(name, {}).get("accuracy"))
        metrics[f"{name}_accuracy"] = {"before": old, "after": new, "delta": new - old}
    old = _number(before.get("whitespace_preservation_accuracy", {}).get("accuracy"))
    new = _number(after.get("whitespace_preservation_accuracy", {}).get("accuracy"))
    metrics["whitespace_preservation_accuracy"] = {"before": old, "after": new, "delta": new - old}

    errors: dict[str, dict[str, float | int]] = {}
    for name in sorted(set(before_errors) | set(after_errors)):
        old, new = int(before_errors.get(name, 0)), int(after_errors.get(name, 0))
        reduction = old - new
        errors[name] = {"before": old, "after": new, "delta": new - old,
                        "reduction": reduction, "reduction_rate": reduction / old if old else 0.0}
    status = {
        "bbox_iou": metrics["bbox_iou"]["after"] >= 0.85,
        "detection_match_rate": metrics["detection_match_rate"]["after"] >= 0.95,
        "whitespace_preservation_accuracy": metrics["whitespace_preservation_accuracy"]["after"] >= 0.80,
        "date_accuracy": metrics["date_accuracy"]["after"] >= 0.85,
        "character_deletion_reduction": _reduction_meets(errors.get("character_deletion", {}), 0.50),
        "missing_text_reduction": _reduction_meets(errors.get("missing_text", {}), 0.50),
    }
    return {
        "before": {"dataset": before.get("dataset", {}), "metrics": before_metrics},
        "after": {"dataset": after.get("dataset", {}), "metrics": after_metrics},
        "metrics": metrics,
        "error_distribution": errors,
        "targets": {name: {"target": TARGETS[name][1], "status": status[name]} for name in TARGETS},
        "improvement_priorities": _priorities(metrics, errors),
    }


# phase2 comparison 마크다운 데이터를 타깃 포맷으로 렌더링함
def render_phase2_comparison_markdown(comparison: Mapping[str, Any]) -> str:
    """Render a human-readable Before vs After report."""

    lines = [
        "# OCR Phase 2 Before vs After", "",
        "## Dataset", "",
        "Metrics are computed from the same paired sample population; source labels are not modified.", "",
        "## Overall Metrics", "", "| Metric | Before | After | Delta |", "|---|---:|---:|---:|",
    ]
    for name, values in comparison.get("metrics", {}).items():
        lines.append(f"| `{name}` | {_pct(values.get('before'))} | {_pct(values.get('after'))} | {_signed_pct(values.get('delta'))} |")
    lines += ["", "## Error Distribution", "", "| Error | Before | After | Reduction |", "|---|---:|---:|---:|"]
    for name, values in sorted(comparison.get("error_distribution", {}).items(), key=lambda item: (-int(item[1].get("before", 0)), item[0])):
        lines.append(f"| `{name}` | {values.get('before', 0)} | {values.get('after', 0)} | {_pct(values.get('reduction_rate'))} |")
    lines += ["", "## Target Status", "", "| Target | Required | Result |", "|---|---:|---:|"]
    for name, values in comparison.get("targets", {}).items():
        result = "PASS" if values.get("status") else "PARTIAL"
        lines.append(f"| `{name}` | {values.get('target')} | **{result}** |")
    lines += ["", "## Improvement Priorities", ""]
    for index, item in enumerate(comparison.get("improvement_priorities", []), start=1):
        lines.append(f"{index}. {item}")
    lines.append("")
    return "\n".join(lines)


# number 작업을 수행함
def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# reduction meets 작업을 수행함
def _reduction_meets(values: Mapping[str, Any], target: float) -> bool:
    return _number(values.get("reduction_rate")) >= target


# priorities 작업을 수행함
def _priorities(metrics: Mapping[str, Mapping[str, float]], errors: Mapping[str, Mapping[str, float | int]]) -> list[str]:
    priorities: list[tuple[float, str]] = []
    for key, label, target in (
        ("bbox_iou", "bbox geometry", 0.85), ("detection_match_rate", "detection recall", 0.95),
        ("whitespace_preservation_accuracy", "whitespace", 0.80), ("date_accuracy", "date formatting", 0.85),
    ):
        value = _number(metrics.get(key, {}).get("after"))
        if value < target:
            priorities.append((1.0 - value, f"{label} remains below the Phase 2 target ({value:.2%})."))
    for key, label in (("character_deletion", "character deletion"), ("missing_text", "missing text")):
        reduction = _number(errors.get(key, {}).get("reduction_rate"))
        if reduction < 0.50:
            priorities.append((1.0 - reduction, f"{label} reduction is {reduction:.2%}; detector recall needs further tuning."))
    return [message for _, message in sorted(priorities, reverse=True)] or [
        "All configured Phase 2 targets were met; validate on a held-out corpus before deployment."
    ]


# pct 작업을 수행함
def _pct(value: Any) -> str:
    return f"{_number(value):.2%}"


# signed pct 작업을 수행함
def _signed_pct(value: Any) -> str:
    return f"{_number(value):+.2%}"
