# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: benchmark.py
# 경로: packages/ocr/ocr/dataset/benchmark.py
# 목적: 박스 단위 정답 데이터 기반 기하 인식형 OCR 벤치마크 평가를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Geometry-aware evaluation against box-level OCR ground truth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rapidfuzz.distance import Levenshtein

from ..pipeline.models import OCRPageResult, OCRWord
from .models import OCRSample, SampleAnnotation
from .rules import intersection_over_union, preserve_source_text, scale_bbox


@dataclass(frozen=True)
class SampleOCRMetrics:
    """Metrics for one OCR page against one labelled image."""

    sample_id: str
    ground_truth_annotations: int
    predicted_words: int
    matched_predictions: int
    unmatched_annotations: int
    unmatched_predictions: int
    annotation_recall: float
    bbox_mean_iou: float
    text_accuracy: float
    exact_region_accuracy: float
    protected_token_errors: int

    # dict 형식으로 변환하여 반환함
    def to_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "ground_truth_annotations": self.ground_truth_annotations,
            "predicted_words": self.predicted_words,
            "matched_predictions": self.matched_predictions,
            "unmatched_annotations": self.unmatched_annotations,
            "unmatched_predictions": self.unmatched_predictions,
            "annotation_recall": self.annotation_recall,
            "bbox_mean_iou": self.bbox_mean_iou,
            "text_accuracy": self.text_accuracy,
            "exact_region_accuracy": self.exact_region_accuracy,
            "protected_token_errors": self.protected_token_errors,
        }


# sample 페이지 품질 및 지표를 평가함
def evaluate_sample_page(
    sample: OCRSample,
    page: OCRPageResult,
    *,
    source_image_size: tuple[int, int] | None = None,
    minimum_iou: float = 0.05,
) -> SampleOCRMetrics:
    """Match OCR words to one or more source boxes without losing punctuation.

    OCR engines usually return a word spanning several source boxes.  For each
    predicted word, all unused labelled boxes whose centers lie inside it (or
    overlap it) are concatenated in source reading order.  This prevents the
    benchmark from unfairly penalizing a detector that groups characters.
    """

    gt = list(sample.annotations)
    words = list(page.words)
    if source_image_size is not None:
        output_width, output_height = source_image_size
    else:
        output_width, output_height = sample.image_width, sample.image_height
    used: set[int] = set()
    matched = 0
    ious: list[float] = []
    edit_accuracies: list[float] = []
    exact = 0
    protected_errors = 0
    for word in words:
        predicted_box = scale_bbox(
            word.bbox,
            source_width=output_width,
            source_height=output_height,
            target_width=sample.image_width,
            target_height=sample.image_height,
        )
        candidates = [
            (index, annotation)
            for index, annotation in enumerate(gt)
            if index not in used and _overlaps_or_contains(predicted_box, annotation, minimum_iou)
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda pair: (pair[1].bbox.y, pair[1].bbox.x, pair[1].sequence))
        target_text = "".join(preserve_source_text(annotation.text) for _, annotation in candidates)
        predicted_text = preserve_source_text(word.text)
        accuracy = max(0.0, 1.0 - Levenshtein.distance(target_text, predicted_text) / max(1, len(target_text)))
        edit_accuracies.append(accuracy)
        if target_text == predicted_text:
            exact += 1
        protected_errors += _protected_token_error_count(target_text, predicted_text)
        for index, annotation in candidates:
            used.add(index)
            ious.append(intersection_over_union(predicted_box, annotation.bbox))
        matched += 1
    return SampleOCRMetrics(
        sample_id=sample.sample_id,
        ground_truth_annotations=len(gt),
        predicted_words=len(words),
        matched_predictions=matched,
        unmatched_annotations=len(gt) - len(used),
        unmatched_predictions=len(words) - matched,
        annotation_recall=len(used) / len(gt) if gt else 1.0,
        bbox_mean_iou=sum(ious) / len(ious) if ious else 0.0,
        text_accuracy=sum(edit_accuracies) / len(edit_accuracies) if edit_accuracies else 0.0,
        exact_region_accuracy=exact / matched if matched else 0.0,
        protected_token_errors=protected_errors,
    )


# overlaps or contains 작업을 수행함
def _overlaps_or_contains(predicted, annotation: SampleAnnotation, minimum_iou: float) -> bool:
    if intersection_over_union(predicted, annotation.bbox) >= minimum_iou:
        return True
    center_x = annotation.bbox.x + annotation.bbox.width / 2
    center_y = annotation.bbox.y + annotation.bbox.height / 2
    return predicted.x <= center_x <= predicted.x + predicted.width and predicted.y <= center_y <= predicted.y + predicted.height


# protected 토큰 error count 작업을 수행함
def _protected_token_error_count(expected: str, actual: str) -> int:
    """Count damaged digits and format tokens as hard errors."""

    import re

    tokens = re.findall(r"(?:\d+|https?://[^\s]+|[/:.,%()\[\]{}+\-])", expected)
    return sum(1 for token in tokens if token not in actual)
