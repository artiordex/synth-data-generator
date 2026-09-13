# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: tesseract.py
# 경로: packages/ocr/ocr/engine/tesseract.py
# 목적: Tesseract OCR 엔진 연동 및 텍스트 인식을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Tesseract OCR backend adapter."""

from __future__ import annotations

import cv2
from PIL import Image

from .base import OCRBackend, OCREngineUnavailable, crop_region
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
from ..text.normalization import normalize_ocr_text


class TesseractBackend(OCRBackend):
    """pytesseract adapter using configurable language and PSM."""

    name = "tesseract"

    # TesseractBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, *, language: str = "kor+eng", timeout_seconds: float = 60.0):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.language = language
        self.timeout_seconds = timeout_seconds
        try:
            import pytesseract
        except ImportError as exc:
            raise OCREngineUnavailable("pytesseract is not installed") from exc
        self._pytesseract = pytesseract

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image: PreprocessedImage, *, page_no: int = 1) -> OCRPageResult:
        """Recognize one full page image."""

        return self._recognize_array(image.image, image=image, page_no=page_no)

    # recognize region 작업을 수행함
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        """Recognize one cropped region."""

        return self._recognize_array(
            crop_region(image, bbox), image=image, page_no=page_no,
            offset=(max(0, bbox[0]), max(0, bbox[1])),
        )

    # recognize array 작업을 수행함
    def _recognize_array(self, pixels, *, image: PreprocessedImage, page_no: int,
                         offset: tuple[int, int] = (0, 0)) -> OCRPageResult:
        rgb = cv2.cvtColor(pixels, cv2.COLOR_GRAY2RGB) if pixels.ndim == 2 else cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        data = self._pytesseract.image_to_data(
            pil_image,
            lang=image.config.language or self.language,
            config=f"--psm {image.config.psm}",
            output_type=self._pytesseract.Output.DICT,
            timeout=self.timeout_seconds,
        )
        words: list[OCRWord] = []
        raw_parts: list[str] = []
        previous_line: tuple[int, int, int] | None = None
        for idx, value in enumerate(data.get("text", [])):
            text = str(value)
            if not text:
                continue
            confidence = _parse_confidence(data.get("conf", ["-1"])[idx])
            if confidence < 0:
                continue
            line = tuple(int(data.get(key, [0] * len(data["text"]))[idx])
                         for key in ("block_num", "par_num", "line_num"))
            if previous_line is not None:
                raw_parts.append(" " if line == previous_line else "\n")
            raw_parts.append(text)
            previous_line = line
            words.append(
                OCRWord(
                    text=text,
                    confidence=confidence,
                    bbox=BoundingBox(
                        int(data["left"][idx]) + offset[0],
                        int(data["top"][idx]) + offset[1],
                        int(data["width"][idx]),
                        int(data["height"][idx]),
                    ),
                )
            )
        raw_text = "".join(raw_parts)
        mean_confidence, median_confidence = confidence_stats(tuple(words))
        low_regions = tuple(
            LowConfidenceRegion(page_no=page_no, bbox=word.bbox, text=word.text, confidence=word.confidence)
            for word in words
            if word.confidence < 0.70
        )
        issues = (ErrorCode.OCR_EMPTY_RESULT,) if not raw_text else ()
        return OCRPageResult(
            page_no=page_no,
            raw_text=raw_text,
            normalized_text=normalize_ocr_text(raw_text),
            words=tuple(words),
            mean_confidence=mean_confidence,
            median_confidence=median_confidence,
            low_confidence_regions=low_regions,
            engine=self.name,
            profile=image.config.profile,
            psm=image.config.psm,
            status=OCRStatus.REVIEW_REQUIRED if issues else OCRStatus.SUCCESS,
            issues=issues,
            coordinate_width_px=image.width_px,
            coordinate_height_px=image.height_px,
        )


# 인식 신뢰도 데이터를 분석하여 파싱함
def _parse_confidence(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return -1.0
    return max(-1.0, min(1.0, parsed / 100.0))
