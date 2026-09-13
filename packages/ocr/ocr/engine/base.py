# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: base.py
# 경로: packages/ocr/ocr/engine/base.py
# 목적: OCR 인식 엔진의 공통 추상 베이스 클래스를 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Common OCR backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..pipeline.models import OCRPageResult, PreprocessedImage


class OCREngineUnavailable(RuntimeError):
    """Raised when an optional OCR engine is not installed or configured."""


class OCRBackend(ABC):
    """Abstract OCR backend. Pipelines depend on this interface only."""

    name: str = "base"

    # recognize 페이지 작업을 수행함
    @abstractmethod
    def recognize_page(self, image: PreprocessedImage, *, page_no: int = 1) -> OCRPageResult:
        """Recognize one full page image."""

        raise NotImplementedError("OCR backend must implement recognize_page")

    # recognize region 작업을 수행함
    @abstractmethod
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        """Recognize one image region."""

        raise NotImplementedError("OCR backend must implement recognize_region")

    # word data 정보를 조회하여 반환함
    def get_word_data(self, result: OCRPageResult):
        """Return OCR word records."""

        return result.words

    # 인식 신뢰도 정보를 조회하여 반환함
    def get_confidence(self, result: OCRPageResult) -> float:
        """Return page-level mean confidence."""

        return result.mean_confidence

    # boxes 정보를 조회하여 반환함
    def get_boxes(self, result: OCRPageResult):
        """Return word bounding boxes."""

        return tuple(word.bbox for word in result.words)


# 자르기 region 작업을 수행함
def crop_region(image: PreprocessedImage, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """Crop a pixel region from a preprocessed image."""

    x, y, width, height = bbox
    if width <= 0 or height <= 0:
        raise ValueError("Region width and height must be positive")
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(image.width_px, x + width), min(image.height_px, y + height)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Region does not intersect the image")
    return image.image[y0:y1, x0:x1]
