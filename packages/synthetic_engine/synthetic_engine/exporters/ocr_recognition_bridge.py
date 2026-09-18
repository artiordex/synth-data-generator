# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_recognition_bridge.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_recognition_bridge.py
# 목적: OCR 엔진 인식 결과를 문서 IR 구조와 연결 매핑함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Bridge from the shared OCR backend to document reconstruction words."""

from __future__ import annotations

import logging
import os
import unicodedata
from dataclasses import dataclass
from typing import Callable, Any

import cv2
import numpy as np
from ocr.engine.base import OCREngineUnavailable
from ocr.pipeline.models import PreprocessedImage, PreprocessingConfig, PreprocessingProfile
from ocr.text.korean_quality import is_ocr_noise_text, ocr_result_quality


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecognizedWord:
    """OCR word in coordinates of the image passed to ``recognize_page_words``."""

    text: str
    bbox: tuple[int, int, int, int]
    confidence: float

    # center 작업을 수행함
    @property
    def center(self) -> tuple[float, float]:
        """
            @description center 작업을 수행함
            @returns {tuple[float, float]} - 메서드 실행 결과를 반환함
        """
        return ((self.bbox[0] + self.bbox[2]) / 2.0, (self.bbox[1] + self.bbox[3]) / 2.0)


# recognize 페이지 words 작업을 수행함
def recognize_page_words(
    image: np.ndarray,
    *,
    backend_factory: Callable[[], Any],
) -> list[RecognizedWord]:
    """Run OCR attempts and map every bbox back to input-image coordinates.

    Internally upscaled attempts are never allowed to leak their coordinate
    space to callers. In document reconstruction the input is the deskewed page,
    so returned boxes share a pixel space with detected tables and cells.
    """

    if image is None or image.size == 0:
        return []

    height, width = image.shape[:2]
    attempts: list[tuple[str, np.ndarray, float]] = [
        ("legacy_table_reconstructor_bridge", image, 1.0)
    ]
    scale = _small_text_scale(image)
    if scale > 1.0:
        attempts.append((
            f"legacy_table_reconstructor_bridge_upscale:{scale:g}",
            cv2.resize(
                image,
                dsize=None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_LANCZOS4,
            ),
            scale,
        ))

    best_words: list[RecognizedWord] = []
    best_score = -1.0
    for step, pixels, word_scale in attempts:
        attempt_height, attempt_width = pixels.shape[:2]
        prepared = PreprocessedImage(
            image=pixels,
            config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
            width_px=attempt_width,
            height_px=attempt_height,
            applied_steps=(step,),
            original_width_px=width,
            original_height_px=height,
            ocr_width_px=attempt_width,
            ocr_height_px=attempt_height,
        )
        try:
            result = backend_factory().recognize_page(prepared, page_no=1)
        except (OCREngineUnavailable, OSError, RuntimeError, ValueError) as exc:
            logger.warning("Local OCR failed for table reconstruction: %s", exc)
            continue
        words = _words_from_backend_result(
            result,
            scale=word_scale,
            original_size=(width, height),
        )
        score = ocr_result_quality(words)
        if score > best_score:
            best_words = words
            best_score = score
    return best_words


# words from backend 결과 작업을 수행함
def _words_from_backend_result(
    result: Any,
    *,
    scale: float = 1.0,
    original_size: tuple[int, int] | None = None,
) -> list[RecognizedWord]:
    words: list[RecognizedWord] = []
    for item in getattr(result, "words", ()):
        text = unicodedata.normalize("NFC", str(item.text))
        if is_ocr_noise_text(text):
            continue
        box = item.bbox
        if box.width <= 0 or box.height <= 0:
            continue
        x0 = int(round(box.x / scale))
        y0 = int(round(box.y / scale))
        x1 = int(round((box.x + box.width) / scale))
        y1 = int(round((box.y + box.height) / scale))
        if original_size is not None:
            width, height = original_size
            x0, x1 = max(0, min(width, x0)), max(0, min(width, x1))
            y0, y1 = max(0, min(height, y0)), max(0, min(height, y1))
        if x1 <= x0 or y1 <= y0:
            continue
        words.append(
            RecognizedWord(
                text=text,
                bbox=(x0, y0, x1, y1),
                confidence=float(item.confidence),
            )
        )
    return sorted(words, key=lambda word: (word.center[1], word.bbox[0]))


# small 텍스트 scale 작업을 수행함
def _small_text_scale(image: np.ndarray) -> float:
    gray = image if image.ndim == 2 else cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    short_side = min(gray.shape[:2])
    line_height = _estimate_text_line_height(gray)
    if short_side < 700 or (line_height and line_height < 14):
        try:
            configured = float(os.getenv("OCR_SMALL_IMAGE_UPSCALE", "2.5"))
        except ValueError:
            configured = 2.5
        return max(1.0, min(3.0, configured))
    return 1.0


# 텍스트 line 높이 수치를 추정하여 반환함
def _estimate_text_line_height(gray: np.ndarray) -> float:
    threshold = cv2.threshold(
        cv2.GaussianBlur(gray, (3, 3), 0),
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]
    count, _, stats, _ = cv2.connectedComponentsWithStats(threshold, 8)
    heights = [
        float(stats[index, cv2.CC_STAT_HEIGHT])
        for index in range(1, count)
        if stats[index, cv2.CC_STAT_AREA] >= 3
        and 2 <= stats[index, cv2.CC_STAT_HEIGHT] <= max(3, gray.shape[0] // 3)
    ]
    return float(np.median(heights)) if heights else 0.0
