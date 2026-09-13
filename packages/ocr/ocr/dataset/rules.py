# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: rules.py
# 경로: packages/ocr/ocr/dataset/rules.py
# 목적: OCR 평가 및 정규화 규칙을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Source-preserving ordering and geometry rules for OCR sample evaluation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from statistics import median
import unicodedata

from ..pipeline.models import BoundingBox
from .models import SampleAnnotation, SampleRuleConfig


# preserve source 텍스트 작업을 수행함
def preserve_source_text(value: object) -> str:
    """Apply only NFC normalization; never collapse source whitespace."""

    return unicodedata.normalize("NFC", "" if value is None else str(value))


# order annotations 작업을 수행함
def order_annotations(
    annotations: Iterable[SampleAnnotation],
    *,
    config: SampleRuleConfig | None = None,
) -> tuple[SampleAnnotation, ...]:
    """Order boxes by visual lines, then left-to-right within each line.

    The corpus contains forms where a large horizontal gap is a field layout,
    not a word separator.  Therefore this function never invents spaces.
    """

    cfg = config or SampleRuleConfig()
    items = list(annotations)
    if not items:
        return ()
    heights = [item.bbox.height for item in items if item.bbox.height > 0]
    typical_height = median(heights) if heights else 1
    lines: list[list[SampleAnnotation]] = []
    line_y: list[float] = []
    for item in sorted(items, key=lambda value: (value.bbox.y, value.bbox.x, value.sequence)):
        center = item.bbox.y + item.bbox.height / 2
        best_index: int | None = None
        best_distance = float("inf")
        for index, line in enumerate(lines):
            top = min(value.bbox.y for value in line)
            bottom = max(value.bbox.y + value.bbox.height for value in line)
            overlap = min(item.bbox.y + item.bbox.height, bottom) - max(item.bbox.y, top)
            overlap_ratio = overlap / max(1, min(item.bbox.height, bottom - top))
            distance = abs(center - line_y[index])
            if overlap_ratio >= cfg.line_overlap_ratio or distance <= typical_height * cfg.line_center_tolerance_ratio:
                if distance < best_distance:
                    best_index, best_distance = index, distance
        if best_index is None:
            lines.append([item])
            line_y.append(center)
        else:
            lines[best_index].append(item)
            line_y[best_index] = sum(
                value.bbox.y + value.bbox.height / 2 for value in lines[best_index]
            ) / len(lines[best_index])
    lines.sort(key=lambda line: (min(value.bbox.y for value in line), min(value.bbox.x for value in line)))
    return tuple(value for line in lines for value in sorted(line, key=lambda item: (item.bbox.x, item.sequence)))


# annotations to 텍스트 작업을 수행함
def annotations_to_text(
    annotations: Sequence[SampleAnnotation],
    *,
    config: SampleRuleConfig | None = None,
) -> str:
    """Build ground truth without changing punctuation or adding spaces."""

    ordered = order_annotations(annotations, config=config)
    if not ordered:
        return ""
    lines: list[list[SampleAnnotation]] = []
    cfg = config or SampleRuleConfig()
    heights = [item.bbox.height for item in ordered if item.bbox.height > 0]
    typical_height = median(heights) if heights else 1
    for item in ordered:
        center = item.bbox.y + item.bbox.height / 2
        if not lines:
            lines.append([item])
            continue
        previous = lines[-1]
        top = min(value.bbox.y for value in previous)
        bottom = max(value.bbox.y + value.bbox.height for value in previous)
        overlap = min(item.bbox.y + item.bbox.height, bottom) - max(item.bbox.y, top)
        previous_center = sum(value.bbox.y + value.bbox.height / 2 for value in previous) / len(previous)
        if overlap / max(1, min(item.bbox.height, bottom - top)) < cfg.line_overlap_ratio and abs(center - previous_center) > typical_height * cfg.line_center_tolerance_ratio:
            lines.append([item])
        else:
            previous.append(item)
    return "\n".join("".join(preserve_source_text(item.text) for item in line) for line in lines)


# intersection over union 작업을 수행함
def intersection_over_union(first: BoundingBox, second: BoundingBox) -> float:
    """Calculate IoU for pixel-space boxes."""

    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.x + first.width, second.x + second.width)
    bottom = min(first.y + first.height, second.y + second.height)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = first.area + second.area - intersection
    return intersection / union if union else 0.0


# scale 바운딩 박스 작업을 수행함
def scale_bbox(box: BoundingBox, *, source_width: int, source_height: int, target_width: int, target_height: int) -> BoundingBox:
    """Map OCR output coordinates back to the labelled image coordinate space."""

    if source_width <= 0 or source_height <= 0 or target_width <= 0 or target_height <= 0:
        raise ValueError("All image dimensions must be positive")
    sx, sy = target_width / source_width, target_height / source_height
    return BoundingBox(round(box.x * sx), round(box.y * sy), max(1, round(box.width * sx)), max(1, round(box.height * sy)))
