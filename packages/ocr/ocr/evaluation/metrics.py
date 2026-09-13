# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: metrics.py
# 경로: packages/ocr/ocr/evaluation/metrics.py
# 목적: CER, WER 등 문자 및 단어 수준 OCR 인식 평가 지표를 계산함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Ground-truth and proxy OCR quality metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

from ..pipeline.models import OCRPageResult


KOREAN_RE = re.compile(r"[가-힣]")
UNKNOWN_RE = re.compile(r"[�□▯]")
INVALID_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


@dataclass(frozen=True)
class OCRMetrics:
    """Metric result. Accuracy is only populated when ground truth exists."""

    cer: float | None
    wer: float | None
    character_accuracy: float | None
    word_accuracy: float | None
    mean_confidence: float
    median_confidence: float
    text_coverage: float
    korean_character_ratio: float
    invalid_character_ratio: float
    unknown_character_ratio: float
    repeated_character_ratio: float
    low_confidence_region_ratio: float
    quality_score: float


# 텍스트 품질 지표 작업을 수행함
def text_metrics(ground_truth: str, recognized_text: str) -> dict[str, float]:
    """Calculate CER/WER without trimming significant characters."""

    if ground_truth == "":
        cer = 0.0 if recognized_text == "" else 1.0
        char_accuracy = 1.0 if recognized_text == "" else 0.0
    else:
        distance = Levenshtein.distance(ground_truth, recognized_text)
        cer = distance / len(ground_truth)
        char_accuracy = 1.0 - cer

    gt_words = ground_truth.split()
    rec_words = recognized_text.split()
    if not gt_words:
        wer = 0.0 if not rec_words else 1.0
        word_accuracy = 1.0 if not rec_words else 0.0
    else:
        wer = Levenshtein.distance(gt_words, rec_words) / len(gt_words)
        word_accuracy = 1.0 - wer

    return {
        "cer": cer,
        "wer": wer,
        "character_accuracy": char_accuracy,
        "word_accuracy": word_accuracy,
    }


# OCR 인식 페이지 품질 및 지표를 평가함
def evaluate_ocr_page(page: OCRPageResult, *, ground_truth: str | None = None, image_area: int | None = None) -> OCRMetrics:
    """Evaluate one page and keep confidence separate from true accuracy."""

    text = page.raw_text
    char_count = len(text)
    unknown = len(UNKNOWN_RE.findall(text))
    invalid = len(INVALID_RE.findall(text))
    korean = len(KOREAN_RE.findall(text))
    repeated = _repeated_character_count(text)
    word_area = sum(word.bbox.area for word in page.words)
    coverage = min(1.0, word_area / image_area) if image_area and image_area > 0 else min(1.0, char_count / 1000.0)
    low_ratio = len(page.low_confidence_regions) / len(page.words) if page.words else 1.0
    exact = text_metrics(ground_truth, text) if ground_truth is not None else {
        "cer": None,
        "wer": None,
        "character_accuracy": None,
        "word_accuracy": None,
    }
    invalid_ratio = invalid / char_count if char_count else 1.0
    unknown_ratio = unknown / char_count if char_count else 1.0
    korean_ratio = korean / char_count if char_count else 0.0
    repeated_ratio = repeated / char_count if char_count else 0.0
    proxy = (
        page.mean_confidence * 0.45
        + coverage * 0.20
        + (1.0 - invalid_ratio) * 0.15
        + (1.0 - unknown_ratio) * 0.10
        + (1.0 - low_ratio) * 0.10
    )
    quality = exact["character_accuracy"] if exact["character_accuracy"] is not None else max(0.0, min(1.0, proxy))
    return OCRMetrics(
        cer=exact["cer"],
        wer=exact["wer"],
        character_accuracy=exact["character_accuracy"],
        word_accuracy=exact["word_accuracy"],
        mean_confidence=page.mean_confidence,
        median_confidence=page.median_confidence,
        text_coverage=coverage,
        korean_character_ratio=korean_ratio,
        invalid_character_ratio=invalid_ratio,
        unknown_character_ratio=unknown_ratio,
        repeated_character_ratio=repeated_ratio,
        low_confidence_region_ratio=low_ratio,
        quality_score=quality,
    )


# repeated 문자 count 작업을 수행함
def _repeated_character_count(text: str) -> int:
    count = 0
    previous = ""
    streak = 0
    for character in text:
        if character == previous:
            streak += 1
            if streak >= 3:
                count += 1
        else:
            previous = character
            streak = 1
    return count
