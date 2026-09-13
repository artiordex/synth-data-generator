# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: rapidocr_korean.py
# 경로: packages/ocr/ocr/engine/rapidocr_korean.py
# 목적: RapidOCR 한국어 특화 모델 기반 텍스트 인식을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""RapidOCR PP-OCRv5 Korean backend running locally with ONNX Runtime."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Iterable, Sequence
from math import ceil, floor, isfinite
import os
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np

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
from ..text.layout import cluster_words_into_lines, merge_touching_fragments, render_lines
from ..text.normalization import normalize_ocr_text, normalize_structured_token


class RapidOCRKoreanBackend(OCRBackend):
    """Recognize Korean and English with the free PP-OCRv5 Korean model."""

    name = "rapidocr_korean_ppocrv5"

    # RapidOCRKoreanBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(
        self,
        model_root_directory: str | Path | None = None,
        *,
        reader: Any = None,
        review_threshold: float = 0.85,
        det_box_thresh: float | None = None,
        det_text_thresh: float | None = None,
        det_unclip_ratio: float | None = None,
        det_limit_side_len: int | None = None,
        input_padding: int | None = None,
    ) -> None:
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")
        self.model_root_directory = (
            Path(model_root_directory).resolve() if model_root_directory else None
        )
        if self.model_root_directory is not None:
            self.model_root_directory.mkdir(parents=True, exist_ok=True)
        self.review_threshold = review_threshold
        self.det_box_thresh = _bounded_float_env("OCR_DET_BOX_THRESH", det_box_thresh, 0.35, 0.0, 1.0)
        self.det_text_thresh = _bounded_float_env("OCR_DET_TEXT_THRESH", det_text_thresh, 0.18, 0.0, 1.0)
        self.det_unclip_ratio = _bounded_float_env("OCR_DET_UNCLIP_RATIO", det_unclip_ratio, 1.30, 1.0, 3.0)
        self.det_limit_side_len = _positive_int_env("OCR_DET_LIMIT_SIDE_LEN", det_limit_side_len, 960)
        # Injected readers in unit tests return coordinates for the supplied
        # array and must retain the historical no-padding contract.  The
        # production reader receives adaptive context padding by default.
        self.input_padding = _positive_int_env(
            "OCR_INPUT_PADDING", input_padding, 16 if reader is None else 0
        )
        self._reader = reader
        self._reader_lock = Lock()

    # reader 정보를 조회하여 반환함
    def _get_reader(self):
        if self._reader is not None:
            return self._reader
        with self._reader_lock:
            if self._reader is not None:
                return self._reader
            self._reader = self._create_reader()
            return self._reader

    # reader 데이터를 신규 생성함
    def _create_reader(self):
        try:
            from rapidocr import (
                EngineType,
                LangDet,
                LangRec,
                ModelType,
                OCRVersion,
                RapidOCR,
            )
        except ImportError as exc:
            raise OCREngineUnavailable("rapidocr is not installed") from exc

        params: dict[str, object] = {
            "Global.log_level": "warning",
            "EngineConfig.onnxruntime.use_cuda": False,
            "EngineConfig.onnxruntime.use_dml": False,
            "EngineConfig.onnxruntime.enable_cpu_mem_arena": False,
            "EngineConfig.onnxruntime.intra_op_num_threads": 1,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            # DB post-processing thresholds.  These are deliberately explicit
            # so the benchmark can reproduce a tuning run without code edits.
            "Global.text_score": self.det_text_thresh,
            "Det.thresh": self.det_text_thresh,
            "Det.box_thresh": self.det_box_thresh,
            "Det.unclip_ratio": self.det_unclip_ratio,
            "Det.limit_side_len": self.det_limit_side_len,
            "Det.limit_type": "min",
            "Global.max_side_len": 2400,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH,
            "Det.model_type": ModelType.MOBILE,
            "Det.ocr_version": OCRVersion.PPOCRV5,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type": LangRec.KOREAN,
            "Rec.model_type": ModelType.MOBILE,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
        }
        if self.model_root_directory is not None:
            params["Global.model_root_dir"] = str(self.model_root_directory)
        try:
            return RapidOCR(params=params)
        except (OSError, RuntimeError, ValueError) as exc:
            where = (
                f" under {self.model_root_directory}"
                if self.model_root_directory is not None
                else ""
            )
            raise OCREngineUnavailable(
                "RapidOCR Korean PP-OCRv5 could not initialize local ONNX models"
                f"{where}"
            ) from exc

    # recognize 페이지 작업을 수행함
    def recognize_page(
        self, image: PreprocessedImage, *, page_no: int = 1
    ) -> OCRPageResult:
        return self._recognize_array(image.image, image=image, page_no=page_no)

    # recognize region 작업을 수행함
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        return self._recognize_array(
            crop_region(image, bbox),
            image=image,
            page_no=page_no,
            offset=(max(0, bbox[0]), max(0, bbox[1])),
        )

    # recognize array 작업을 수행함
    def _recognize_array(
        self,
        pixels,
        *,
        image: PreprocessedImage,
        page_no: int,
        offset: tuple[int, int] = (0, 0),
    ) -> OCRPageResult:
        source_height, source_width = pixels.shape[:2]
        padded = _pad_image(pixels, self.input_padding)
        try:
            output = self._get_reader()(padded)
        except OCREngineUnavailable:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise OCREngineUnavailable("RapidOCR inference failed") from exc

        words: list[OCRWord] = []
        height, width = padded.shape[:2]
        for polygon, value, score in _iter_detections(output):
            bbox = _polygon_to_bbox(
                polygon,
                source_width,
                source_height,
                offset,
                input_origin=(self.input_padding, self.input_padding),
            )
            if bbox is None:
                continue
            text = normalize_ocr_text(str(value))
            if not text.strip():
                continue
            words.append(
                OCRWord(
                    text=text,
                    confidence=_normalize_confidence(score),
                    bbox=bbox,
                )
            )

        lines = merge_touching_fragments(cluster_words_into_lines(words))
        ordered = tuple(word for line in lines for word in line)
        raw_text = render_lines(lines)
        normalized_text = normalize_ocr_text(
            render_lines(
                [
                    [replace(word, text=normalize_structured_token(word.text)) for word in line]
                    for line in lines
                ]
            )
        )
        mean, median = confidence_stats(ordered)
        low_regions = tuple(
            LowConfidenceRegion(
                page_no=page_no,
                bbox=word.bbox,
                text=word.text,
                confidence=word.confidence,
            )
            for word in ordered
            if word.confidence < self.review_threshold
        )
        issues: list[ErrorCode] = []
        if not raw_text:
            issues.append(ErrorCode.OCR_EMPTY_RESULT)
        elif low_regions:
            issues.append(ErrorCode.OCR_LOW_CONFIDENCE)
        return OCRPageResult(
            page_no=page_no,
            raw_text=raw_text,
            normalized_text=normalized_text,
            words=ordered,
            mean_confidence=mean,
            median_confidence=median,
            low_confidence_regions=low_regions,
            engine=self.name,
            profile=image.config.profile,
            psm=image.config.psm,
            status=OCRStatus.REVIEW_REQUIRED if issues else OCRStatus.SUCCESS,
            issues=tuple(issues),
            coordinate_width_px=image.width_px,
            coordinate_height_px=image.height_px,
        )


# iter detections 작업을 수행함
def _iter_detections(output: Any) -> Iterable[tuple[Any, Any, Any]]:
    """Yield RapidOCR detections across the 3.x object and legacy list forms."""

    if output is None:
        return ()

    boxes = getattr(output, "boxes", None)
    texts = getattr(output, "txts", None)
    scores = getattr(output, "scores", None)
    if boxes is not None and texts is not None:
        if scores is None:
            scores = [1.0] * len(texts)
        return zip(boxes, texts, scores)

    if isinstance(output, tuple) and output:
        first = output[0]
        if _looks_like_detection_sequence(first):
            return _iter_sequence_detections(first)

    if _looks_like_detection_sequence(output):
        return _iter_sequence_detections(output)

    return ()


# looks like detection sequence 작업을 수행함
def _looks_like_detection_sequence(value: Any) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    return isinstance(value, Sequence) or (
        hasattr(value, "__iter__") and not isinstance(value, dict)
    )


# iter sequence detections 작업을 수행함
def _iter_sequence_detections(value: Any) -> Iterable[tuple[Any, Any, Any]]:
    for item in value:
        if isinstance(item, dict):
            box = item.get("box") or item.get("bbox") or item.get("points")
            text = item.get("text") or item.get("txt") or item.get("transcription")
            score = item.get("score")
            if score is None:
                score = item.get("confidence")
            if score is None:
                score = item.get("conf")
            if box is not None and text is not None:
                yield box, text, 1.0 if score is None else score
            continue
        if _is_detection_record(item):
            box = item[0]
            text = item[1]
            score = item[2] if len(item) >= 3 else 1.0
            yield box, text, score


# detection record 여부 및 유효성을 판별함
def _is_detection_record(value: Any) -> bool:
    if isinstance(value, (str, bytes, dict)):
        return False
    try:
        return len(value) >= 2
    except TypeError:
        return False


# 인식 신뢰도 데이터를 표준 형식으로 정규화함
def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not isfinite(confidence):
        return 0.0
    if confidence > 10.0:
        confidence /= 100.0
    return max(0.0, min(1.0, confidence))


# polygon to 바운딩 박스 작업을 수행함
def _polygon_to_bbox(
    polygon: Any,
    width: int,
    height: int,
    offset: tuple[int, int],
    input_origin: tuple[int, int] = (0, 0),
) -> BoundingBox | None:
    try:
        points = list(polygon)
    except TypeError:
        return None

    if len(points) == 4 and all(_is_number(point) for point in points):
        x, y, box_width, box_height = (float(point) for point in points)
        xs = [x, x + box_width]
        ys = [y, y + box_height]
    else:
        try:
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
        except (TypeError, ValueError, IndexError):
            return None
    if not xs or not ys or not all(isfinite(value) for value in (*xs, *ys)):
        return None
    origin_x, origin_y = input_origin
    left = max(0, min(width, floor(min(xs) - origin_x)))
    top = max(0, min(height, floor(min(ys) - origin_y)))
    right = max(0, min(width, ceil(max(xs) - origin_x)))
    bottom = max(0, min(height, ceil(max(ys) - origin_y)))
    if right <= left or bottom <= top:
        return None
    return BoundingBox(
        left + offset[0],
        top + offset[1],
        right - left,
        bottom - top,
    )


# number 여부 및 유효성을 판별함
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# pad 이미지 작업을 수행함
def _pad_image(pixels: Any, padding: int):
    if padding <= 0:
        return pixels
    if pixels.ndim == 2:
        value = 255
        return np.pad(pixels, ((padding, padding), (padding, padding)), mode="constant", constant_values=value)
    return np.pad(
        pixels,
        ((padding, padding), (padding, padding), (0, 0)),
        mode="constant",
        constant_values=255,
    )


# bounded float env 작업을 수행함
def _bounded_float_env(name: str, explicit: float | None, default: float, lower: float, upper: float) -> float:
    if explicit is not None:
        value = explicit
    else:
        try:
            value = float(os.getenv(name, str(default)))
        except ValueError:
            value = default
    return max(lower, min(upper, value))


# positive int env 작업을 수행함
def _positive_int_env(name: str, explicit: int | None, default: int) -> int:
    if explicit is not None:
        return max(0, int(explicit))
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default
