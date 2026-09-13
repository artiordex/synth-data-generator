# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ensemble.py
# 경로: packages/ocr/ocr/engine/ensemble.py
# 목적: 다중 OCR 엔진 앙상블 및 인식 결과 결합 처리를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Confidence-gated local OCR ensemble."""

from __future__ import annotations

import math

import cv2
import numpy as np

from .base import OCRBackend, OCREngineUnavailable
from ..pipeline.models import (
    BoundingBox,
    ErrorCode,
    LowConfidenceRegion,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessedImage,
    confidence_stats,
)
from ..text.korean_quality import (
    needs_secondary_check,
    ocr_candidate_score,
    special_character_ratio,
)
from ..text.layout import cluster_words_into_lines, merge_touching_fragments, render_lines
from ..text.normalization import normalize_ocr_text


class ConfidenceEnsembleBackend(OCRBackend):
    """Use secondary engines only for uncertain primary detections."""

    name = "local_confidence_ensemble"

    # ConfidenceEnsembleBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(
        self,
        primary: OCRBackend,
        secondary: OCRBackend | None = None,
        tiebreaker: OCRBackend | None = None,
        *,
        review_threshold: float = 0.85,
        replacement_margin: float = 0.03,
        crop_padding: int = 8,
        supplemental_detection: bool = True,
        uncovered_component_ratio: float = 0.20,
        supplemental_min_confidence: float = 0.55,
    ) -> None:
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")
        if not 0.0 <= replacement_margin <= 1.0:
            raise ValueError("replacement_margin must be between 0 and 1")
        if not 0.0 <= uncovered_component_ratio <= 1.0:
            raise ValueError("uncovered_component_ratio must be between 0 and 1")
        if not 0.0 <= supplemental_min_confidence <= 1.0:
            raise ValueError("supplemental_min_confidence must be between 0 and 1")
        self.primary = primary
        self.secondary = secondary
        self.tiebreaker = tiebreaker
        self.review_threshold = review_threshold
        self.replacement_margin = replacement_margin
        self.crop_padding = max(0, crop_padding)
        self.supplemental_detection = bool(supplemental_detection)
        self.uncovered_component_ratio = uncovered_component_ratio
        self.supplemental_min_confidence = supplemental_min_confidence

    # recognize 페이지 작업을 수행함
    def recognize_page(
        self, image: PreprocessedImage, *, page_no: int = 1
    ) -> OCRPageResult:
        base = self._recognize_with_fallback(image, page_no=page_no)
        if not base.words or self.secondary is None:
            return base
        if base.engine == self.secondary.name:
            return base

        words: list[OCRWord] = []
        engines = {base.engine}
        region_cache: dict[tuple[str, tuple[int, int, int, int]], OCRPageResult | None] = {}
        for word in base.words:
            if (
                word.confidence >= self.review_threshold
                and not _needs_secondary_check(word)
            ):
                words.append(word)
                continue
            candidates = [word]
            region = self._expanded_bbox(word, image)
            for backend in (self.secondary, self.tiebreaker):
                if backend is None:
                    continue
                result = self._recognize_region_once(
                    backend, image, region, page_no, region_cache
                )
                if result is None:
                    continue
                engines.add(result.engine)
                candidate = _single_candidate(result, word)
                if candidate is not None:
                    candidates.append(candidate)
            _, winner = max(
                enumerate(candidates),
                key=lambda item: (_candidate_score(item[1]), -item[0]),
            )
            replacement_margin = (
                0.0 if _needs_secondary_check(word) else self.replacement_margin
            )
            if (
                winner is not word
                and _candidate_score(winner)
                >= _candidate_score(word) + replacement_margin
            ):
                winner = OCRWord(winner.text, winner.confidence, word.bbox)
            else:
                winner = word
            words.append(winner)

        if (
            self.supplemental_detection
            and self.secondary is not None
            and _uncovered_text_component_ratio(image, tuple(words))
            >= self.uncovered_component_ratio
        ):
            try:
                supplemental = self.secondary.recognize_page(image, page_no=page_no)
            except (OCREngineUnavailable, OSError, RuntimeError, ValueError):
                supplemental = None
            if supplemental is not None:
                additions = _novel_supplemental_words(
                    tuple(words),
                    supplemental.words,
                    min_confidence=self.supplemental_min_confidence,
                )
                if additions:
                    words.extend(additions)
                    engines.add(supplemental.engine)
        return self._build_result(tuple(words), image, page_no, engines)

    # recognize region 작업을 수행함
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        try:
            return self.primary.recognize_region(image, bbox, page_no=page_no)
        except (OCREngineUnavailable, OSError, RuntimeError, ValueError):
            if self.secondary is None:
                raise
            return self.secondary.recognize_region(image, bbox, page_no=page_no)

    # recognize region once 작업을 수행함
    def _recognize_region_once(
        self,
        backend: OCRBackend,
        image: PreprocessedImage,
        region: tuple[int, int, int, int],
        page_no: int,
        cache: dict[tuple[str, tuple[int, int, int, int]], OCRPageResult | None],
    ) -> OCRPageResult | None:
        key = (backend.name, region)
        if key not in cache:
            try:
                cache[key] = backend.recognize_region(image, region, page_no=page_no)
            except (OCREngineUnavailable, OSError, RuntimeError, ValueError):
                cache[key] = None
        return cache[key]

    # recognize with 폴백 작업을 수행함
    def _recognize_with_fallback(
        self, image: PreprocessedImage, *, page_no: int
    ) -> OCRPageResult:
        try:
            result = self.primary.recognize_page(image, page_no=page_no)
            if result.words:
                return result
        except (OCREngineUnavailable, OSError, RuntimeError, ValueError):
            result = None
        if self.secondary is not None:
            return self.secondary.recognize_page(image, page_no=page_no)
        if result is not None:
            return result
        raise OCREngineUnavailable("No local OCR backend could process the page")

    # expanded 바운딩 박스 작업을 수행함
    def _expanded_bbox(
        self, word: OCRWord, image: PreprocessedImage
    ) -> tuple[int, int, int, int]:
        box = word.bbox
        x = max(0, box.x - self.crop_padding)
        y = max(0, box.y - self.crop_padding)
        right = min(image.width_px, box.x + box.width + self.crop_padding)
        bottom = min(image.height_px, box.y + box.height + self.crop_padding)
        return x, y, right - x, bottom - y

    # 결과 구조를 생성 및 조립함
    def _build_result(
        self,
        words: tuple[OCRWord, ...],
        image: PreprocessedImage,
        page_no: int,
        engines: set[str],
    ) -> OCRPageResult:
        # Keep ensemble candidates one-to-one with the primary detections;
        # fragment merging belongs to the primary detector and merging here
        # would collapse duplicate low-confidence regions before cache gating.
        lines = cluster_words_into_lines(words)
        ordered = tuple(word for line in lines for word in line)
        raw_text = render_lines(lines)
        mean, median = confidence_stats(ordered)
        low = tuple(
            LowConfidenceRegion(page_no, word.bbox, word.text, word.confidence)
            for word in ordered
            if word.confidence < self.review_threshold
        )
        issues: list[ErrorCode] = []
        if not raw_text:
            issues.append(ErrorCode.OCR_EMPTY_RESULT)
        elif low:
            issues.append(ErrorCode.OCR_LOW_CONFIDENCE)
        return OCRPageResult(
            page_no=page_no,
            raw_text=raw_text,
            normalized_text=normalize_ocr_text(raw_text),
            words=ordered,
            mean_confidence=mean,
            median_confidence=median,
            low_confidence_regions=low,
            engine="+".join(sorted(engines)),
            profile=image.config.profile,
            psm=image.config.psm,
            status=OCRStatus.REVIEW_REQUIRED if issues else OCRStatus.SUCCESS,
            issues=tuple(issues),
            coordinate_width_px=image.width_px,
            coordinate_height_px=image.height_px,
        )


# single candidate 작업을 수행함
def _single_candidate(result: OCRPageResult, original: OCRWord) -> OCRWord | None:
    text = result.raw_text.strip()
    if not text:
        return None
    confidence = (
        sum(word.confidence for word in result.words) / len(result.words)
        if result.words
        else 0.0
    )
    return OCRWord(text=text, confidence=confidence, bbox=original.bbox)


# candidate score 작업을 수행함
def _candidate_score(word: OCRWord) -> float:
    return ocr_candidate_score(word.text, word.confidence)


# needs secondary check 작업을 수행함
def _needs_secondary_check(word: OCRWord) -> bool:
    return needs_secondary_check(word.text, word.confidence)


# special 문자 ratio 작업을 수행함
def _special_character_ratio(text: str) -> float:
    return special_character_ratio(text)


# novel supplemental words 작업을 수행함
def _novel_supplemental_words(
    primary_words: tuple[OCRWord, ...],
    candidates: tuple[OCRWord, ...],
    *,
    min_confidence: float,
) -> list[OCRWord]:
    """Return secondary detections that add geometry not covered by primary."""
    accepted: list[OCRWord] = []
    occupied = list(primary_words)
    for candidate in candidates:
        if (
            candidate.confidence < min_confidence
            or not candidate.text.strip()
            or candidate.bbox.width <= 0
            or candidate.bbox.height <= 0
            or _candidate_score(candidate) < min_confidence
        ):
            continue
        if any(_substantial_box_overlap(candidate.bbox, word.bbox) for word in occupied):
            continue
        accepted.append(candidate)
        occupied.append(candidate)
    return accepted


# substantial box overlap 작업을 수행함
def _substantial_box_overlap(left, right) -> bool:
    intersection_width = max(
        0,
        min(left.x + left.width, right.x + right.width) - max(left.x, right.x),
    )
    intersection_height = max(
        0,
        min(left.y + left.height, right.y + right.height) - max(left.y, right.y),
    )
    intersection = intersection_width * intersection_height
    if intersection <= 0:
        return False
    minimum_area = max(1, min(left.area, right.area))
    return intersection / minimum_area >= 0.45


# uncovered 텍스트 component ratio 작업을 수행함
def _uncovered_text_component_ratio(
    image: PreprocessedImage,
    words: tuple[OCRWord, ...],
) -> float:
    """Estimate text-like foreground components not explained by OCR boxes.

    This is only a routing signal.  Large frames, rules and picture regions
    are excluded so table borders do not trigger an expensive full-page retry.
    """
    pixels = np.asarray(image.image)
    if pixels.size == 0:
        return 0.0
    if pixels.ndim == 3:
        if pixels.shape[2] == 4:
            gray = cv2.cvtColor(pixels, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    elif pixels.ndim == 2:
        gray = pixels
    else:
        return 0.0
    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    foreground = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]
    count, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    height, width = gray.shape
    page_area = max(1, height * width)
    valid_area = 0
    uncovered_area = 0
    for label in range(1, count):
        x, y, component_width, component_height, area = (
            int(value) for value in stats[label]
        )
        if area < max(4, round(page_area * 0.000002)):
            continue
        if area > page_area * 0.03:
            continue
        if component_height < 3 or component_height > max(12, round(height * 0.15)):
            continue
        if component_width < 1 or component_width > max(30, round(width * 0.60)):
            continue
        aspect = component_width / max(1, component_height)
        if aspect > 25.0:
            continue
        valid_area += area
        component_box = BoundingBox(x, y, component_width, component_height)
        covered = bool(words) and any(
            _substantial_box_overlap(component_box, word.bbox) for word in words
        )
        if not covered:
            uncovered_area += area
    if valid_area <= 0:
        return 0.0
    ratio = uncovered_area / valid_area
    return ratio if math.isfinite(ratio) else 0.0


# assemble lines 작업을 수행함
def _assemble_lines(words: tuple[OCRWord, ...]) -> list[list[OCRWord]]:
    lines: list[list[OCRWord]] = []
    for word in sorted(words, key=lambda item: (item.bbox.y, item.bbox.x)):
        matches: list[tuple[float, int]] = []
        for index, line in enumerate(lines):
            anchor = line[0].bbox
            overlap = min(
                word.bbox.y + word.bbox.height, anchor.y + anchor.height
            ) - max(word.bbox.y, anchor.y)
            ratio = overlap / max(1, min(word.bbox.height, anchor.height))
            if ratio >= 0.5:
                matches.append((ratio, index))
        if matches:
            lines[max(matches)[1]].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda item: item.bbox.x) for line in lines]
