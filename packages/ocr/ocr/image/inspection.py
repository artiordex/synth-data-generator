# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: inspection.py
# 경로: packages/ocr/ocr/image/inspection.py
# 목적: 입력 이미지의 해상도, 기울기, 왜곡 등 품질 결함을 검사함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Image quality inspection for adaptive OCR preprocessing."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from ..pipeline.models import ErrorCode, ImageInspection, ImageIssue


class ImageInspectionError(ValueError):
    """Raised when an image cannot be opened or inspected."""


SUPPORTED_IMAGE_FORMATS = {"PNG", "JPEG", "JPG", "TIFF", "BMP"}


# inspect 이미지 작업을 수행함
def inspect_image(path: str | Path) -> ImageInspection:
    """Inspect an image and classify quality issues without mutating it."""

    source = Path(path)
    try:
        with Image.open(source) as image:
            image_format = (image.format or source.suffix.lstrip(".")).upper()
            width, height = image.size
            dpi_x, dpi_y = _dpi_pair(image.info.get("dpi"))
            data = np.array(image.convert("RGB"))
    except (OSError, UnidentifiedImageError) as exc:
        raise ImageInspectionError(f"{ErrorCode.FILE_OPEN_FAILED.value}: {source}") from exc

    if image_format == "JPG":
        image_format = "JPEG"
    if image_format not in SUPPORTED_IMAGE_FORMATS:
        raise ImageInspectionError(f"Unsupported image format: {image_format}")

    gray = cv2.cvtColor(data, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    noise_score = _estimate_noise(gray)
    contrast_score = float(gray.std())
    skew_angle = estimate_skew_angle(gray)
    issues = _classify_issues(width, height, dpi_x, dpi_y, blur_score, noise_score, contrast_score, skew_angle, gray)

    return ImageInspection(
        path=source,
        format=image_format,
        width_px=width,
        height_px=height,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        blur_score=blur_score,
        noise_score=noise_score,
        contrast_score=contrast_score,
        skew_angle_deg=skew_angle,
        issues=tuple(issues),
    )


# skew angle 수치를 추정하여 반환함
def estimate_skew_angle(gray: np.ndarray, *, max_angle: float = 20.0) -> float:
    """Estimate document skew angle in degrees."""

    if gray.size == 0:
        return 0.0
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(threshold > 0))
    if len(coords) < 100:
        return 0.0
    angle = float(cv2.minAreaRect(coords)[-1])
    if angle < -45.0:
        angle = -(90.0 + angle)
    else:
        angle = -angle
    if abs(angle) > max_angle:
        return 0.0
    return angle


# dpi pair 작업을 수행함
def _dpi_pair(value: object) -> tuple[float | None, float | None]:
    if isinstance(value, tuple) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None, None
    return None, None


# 노이즈 수치를 추정하여 반환함
def _estimate_noise(gray: np.ndarray) -> float:
    denoised = cv2.medianBlur(gray, 3)
    residual = gray.astype(np.float32) - denoised.astype(np.float32)
    return float(np.mean(np.abs(residual)))


# classify issues 작업을 수행함
def _classify_issues(
    width: int,
    height: int,
    dpi_x: float | None,
    dpi_y: float | None,
    blur_score: float,
    noise_score: float,
    contrast_score: float,
    skew_angle: float,
    gray: np.ndarray,
) -> list[ImageIssue]:
    issues: list[ImageIssue] = []
    if width * height < 900_000 or min(width, height) < 900:
        issues.append(ImageIssue.LOW_RESOLUTION)
    if (dpi_x is not None and dpi_x < 250) or (dpi_y is not None and dpi_y < 250):
        issues.append(ImageIssue.LOW_DPI)
    if contrast_score < 38.0:
        issues.append(ImageIssue.LOW_CONTRAST)
    if noise_score > 10.0:
        issues.append(ImageIssue.HIGH_NOISE)
    if blur_score < 70.0:
        issues.append(ImageIssue.BLURRED)
    if abs(skew_angle) >= 1.0:
        issues.append(ImageIssue.SKEWED)
    if _has_table_lines(gray):
        issues.append(ImageIssue.TABLE_HEAVY)
    if len(issues) > 1:
        issues.append(ImageIssue.MIXED_PROBLEM)
    if not issues:
        issues.append(ImageIssue.NORMAL)
    return issues


# 표(테이블) lines 보유 여부를 확인함
def _has_table_lines(gray: np.ndarray) -> bool:
    threshold = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, gray.shape[1] // 35), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, gray.shape[0] // 35)))
    horizontal = cv2.dilate(cv2.erode(threshold, horizontal_kernel), horizontal_kernel)
    vertical = cv2.dilate(cv2.erode(threshold, vertical_kernel), vertical_kernel)
    line_pixels = int(np.count_nonzero(cv2.add(horizontal, vertical)))
    return line_pixels / float(gray.size) > 0.015
