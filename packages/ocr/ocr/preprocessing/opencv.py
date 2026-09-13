# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: opencv.py
# 경로: packages/ocr/ocr/preprocessing/opencv.py
# 목적: OpenCV 기반 이미지 이진화, 노이즈 제거, 모폴로지 연산을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""OpenCV preprocessing operations for OCR."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..image.inspection import estimate_skew_angle
from ..pipeline.models import PreprocessedImage, PreprocessingConfig
from .transforms import CoordinateTransform, TransformMetadata


# 이미지 bgr 데이터를 파일 또는 저장소에서 로드함
def load_image_bgr(path: str | Path) -> np.ndarray:
    """Load an image with Pillow and return BGR pixels for OpenCV."""

    with Image.open(path) as image:
        rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# preprocess 이미지 작업을 수행함
def preprocess_image(path: str | Path, config: PreprocessingConfig) -> PreprocessedImage:
    """Apply a profile-driven OpenCV preprocessing pipeline."""

    image = load_image_bgr(path)
    original_height, original_width = image.shape[:2]
    transform_metadata = TransformMetadata.identity((int(original_width), int(original_height)))
    steps: list[str] = []

    if config.grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        steps.append("grayscale")

    if config.upscale > 1.0:
        interpolation = cv2.INTER_LANCZOS4 if config.interpolation == "LANCZOS4" else cv2.INTER_CUBIC
        before_height, before_width = image.shape[:2]
        image = cv2.resize(image, None, fx=config.upscale, fy=config.upscale, interpolation=interpolation)
        after_height, after_width = image.shape[:2]
        transform_metadata = transform_metadata.append(
            CoordinateTransform.scale(
                after_width / before_width,
                after_height / before_height,
                source_size=(int(before_width), int(before_height)),
                target_size=(int(after_width), int(after_height)),
                name="upscale",
                parameters={"scale": config.upscale, "interpolation": config.interpolation},
            )
        )
        steps.append(f"upscale:{config.upscale:g}")

    if config.horizontal_scale != 1.0:
        before_height, before_width = image.shape[:2]
        image = resize_horizontal(image, config.horizontal_scale, interpolation=config.interpolation)
        after_height, after_width = image.shape[:2]
        transform_metadata = transform_metadata.append(
            CoordinateTransform.scale(
                after_width / before_width,
                after_height / before_height,
                source_size=(int(before_width), int(before_height)),
                target_size=(int(after_width), int(after_height)),
                name="horizontal_scale",
                parameters={"scale": config.horizontal_scale, "interpolation": config.interpolation},
            )
        )
        steps.append(f"horizontal_scale:{config.horizontal_scale:g}")

    if config.shadow_reduction:
        image = _reduce_shadow(image)
        steps.append("shadow_reduction")

    if config.denoise != "none":
        strength = 21 if config.denoise == "strong" else 11
        image = cv2.fastNlMeansDenoising(_as_gray(image), None, h=strength, templateWindowSize=7, searchWindowSize=21)
        steps.append(f"denoise:{config.denoise}")

    if config.clahe:
        clahe = cv2.createCLAHE(clipLimit=config.clahe_clip_limit, tileGridSize=(8, 8))
        image = clahe.apply(_as_gray(image))
        steps.append("clahe")

    detected_skew = 0.0
    if config.deskew != "none":
        limit = 20.0 if config.deskew == "aggressive" else 12.0
        before_height, before_width = image.shape[:2]
        image, detected_skew, deskew_matrix = _deskew(_as_gray(image), max_angle=limit)
        if abs(detected_skew) >= 0.1:
            transform_metadata = transform_metadata.append(
                CoordinateTransform.affine(
                    deskew_matrix,
                    source_size=(int(before_width), int(before_height)),
                    target_size=(int(image.shape[1]), int(image.shape[0])),
                    name="deskew",
                    parameters={"angle_deg": detected_skew, "max_angle_deg": limit},
                )
            )
            steps.append(f"deskew:{detected_skew:.2f}")

    if config.threshold == "OTSU":
        image = cv2.threshold(_as_gray(image), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        steps.append("threshold:otsu")
    elif config.threshold == "ADAPTIVE_GAUSSIAN":
        image = cv2.adaptiveThreshold(_as_gray(image), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
        steps.append("threshold:adaptive_gaussian")
    elif config.threshold == "NONE":
        image = _as_gray(image)
    else:
        raise ValueError(f"Unsupported threshold mode: {config.threshold}")

    if config.morphology != "none":
        image = _apply_morphology(image, config.morphology)
        steps.append(f"morphology:{config.morphology}")

    if config.remove_border:
        image = _remove_border(image)
        steps.append("remove_border")

    return PreprocessedImage(
        image=image,
        config=config,
        width_px=int(image.shape[1]),
        height_px=int(image.shape[0]),
        applied_steps=tuple(steps),
        detected_skew_deg=detected_skew,
        original_width_px=int(original_width),
        original_height_px=int(original_height),
        ocr_width_px=int(image.shape[1]),
        ocr_height_px=int(image.shape[0]),
        transform_metadata=TransformMetadata(
            original_size=(int(original_width), int(original_height)),
            ocr_size=(int(image.shape[1]), int(image.shape[0])),
            transforms=transform_metadata.transforms,
        ),
    )


# as gray 작업을 수행함
def _as_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


# resize horizontal 작업을 수행함
def resize_horizontal(
    image: np.ndarray,
    scale: float,
    *,
    interpolation: str = "CUBIC",
) -> np.ndarray:
    """Resize only the x axis while preserving the y sampling.

    This is a controlled OCR retry transform, not a document-layout rewrite.
    The caller records the resulting dimensions and maps detections back to
    the source coordinate space during evaluation/export.
    """

    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("horizontal scale must be a finite positive number")
    if abs(scale - 1.0) < 1e-6:
        return image
    height, width = image.shape[:2]
    target_width = max(1, int(round(width * scale)))
    if interpolation == "LANCZOS4":
        mode = cv2.INTER_LANCZOS4
    elif interpolation == "NEAREST":
        mode = cv2.INTER_NEAREST
    else:
        mode = cv2.INTER_CUBIC if target_width >= width else cv2.INTER_AREA
    return cv2.resize(image, (target_width, height), interpolation=mode)


# deskew 작업을 수행함
def _deskew(gray: np.ndarray, *, max_angle: float) -> tuple[np.ndarray, float, np.ndarray]:
    angle = estimate_skew_angle(gray, max_angle=max_angle)
    if abs(angle) < 0.3:
        return gray, 0.0, np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=float)
    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, angle, matrix


# reduce shadow 작업을 수행함
def _reduce_shadow(gray: np.ndarray) -> np.ndarray:
    source = _as_gray(gray)
    background = cv2.medianBlur(source, 31)
    diff = 255 - cv2.absdiff(source, background)
    return cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)


# apply morphology 작업을 수행함
def _apply_morphology(image: np.ndarray, mode: str) -> np.ndarray:
    if mode == "minimal":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    if mode == "open":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    if mode == "close":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
    raise ValueError(f"Unsupported morphology mode: {mode}")


# 테두리 요소를 제거함
def _remove_border(image: np.ndarray) -> np.ndarray:
    cleaned = image.copy()
    contours, _ = cv2.findContours(255 - cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = cleaned.shape[:2]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        near_edge = x < 5 or y < 5 or x + w > width - 5 or y + h > height - 5
        if near_edge and w * h > width * height * 0.2:
            cv2.drawContours(cleaned, [contour], -1, 255, thickness=3)
    return cleaned
