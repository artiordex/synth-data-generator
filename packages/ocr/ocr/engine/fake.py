# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: fake.py
# 경로: packages/ocr/ocr/engine/fake.py
# 목적: 테스트 및 모의 실험용 Fake OCR 엔진을 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Deterministic OCR backend for routing and metric tests."""

from __future__ import annotations

from collections.abc import Callable

from .base import OCRBackend
from ..pipeline.models import (
    BoundingBox,
    LowConfidenceRegion,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessedImage,
    confidence_stats,
)
from ..text.normalization import normalize_ocr_text


class FakeOCRBackend(OCRBackend):
    """Fake backend that returns profile-dependent text and confidence."""

    name = "fake"

    # FakeOCRBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, recognizer: Callable[[PreprocessedImage], tuple[str, float]]):
        self._recognizer = recognizer

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image: PreprocessedImage, *, page_no: int = 1) -> OCRPageResult:
        text, confidence = self._recognizer(image)
        words = _words_from_text(text, confidence)
        mean_confidence, median_confidence = confidence_stats(words)
        low_regions = tuple(
            LowConfidenceRegion(page_no=page_no, bbox=word.bbox, text=word.text, confidence=word.confidence)
            for word in words
            if word.confidence < 0.70
        )
        return OCRPageResult(
            page_no=page_no,
            raw_text=text,
            normalized_text=normalize_ocr_text(text),
            words=words,
            mean_confidence=mean_confidence,
            median_confidence=median_confidence,
            low_confidence_regions=low_regions,
            engine=self.name,
            profile=image.config.profile,
            psm=image.config.psm,
            status=OCRStatus.SUCCESS if text else OCRStatus.REVIEW_REQUIRED,
            coordinate_width_px=image.width_px,
            coordinate_height_px=image.height_px,
        )

    # recognize region 작업을 수행함
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        return self.recognize_page(image, page_no=page_no)


# words from 텍스트 작업을 수행함
def _words_from_text(text: str, confidence: float) -> tuple[OCRWord, ...]:
    tokens = text.split() or ([text] if text else [])
    return tuple(
        OCRWord(
            text=token,
            confidence=max(0.0, min(1.0, confidence)),
            bbox=BoundingBox(10 + index * 40, 10, 30, 12),
        )
        for index, token in enumerate(tokens)
    )
