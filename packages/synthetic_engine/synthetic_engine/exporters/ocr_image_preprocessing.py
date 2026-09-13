# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_image_preprocessing.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_image_preprocessing.py
# 목적: OCR 인식률 향상을 위한 이미지 기하 보정 및 필터링을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Image preprocessing helpers for OCR reconstruction."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


# deskew 이미지 작업을 수행함
def deskew_image(img_bgr: np.ndarray, max_angle: float = 15.0) -> Tuple[np.ndarray, float]:
    """Detect and correct a small scan skew angle."""

    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return img_bgr, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > max_angle or abs(angle) < 0.3:
            return img_bgr, 0.0

        h, w = img_bgr.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img_bgr,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, angle
    except Exception:
        return img_bgr, 0.0


# 텍스트 line 높이 수치를 추정하여 반환함
def _estimate_text_line_height(gray: np.ndarray) -> float:
    """Estimate glyph/line height from dark connected components."""

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


# OCR 인식 upscale factor 작업을 수행함
def _ocr_upscale_factor(image: np.ndarray) -> float:
    if image.ndim == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    short_side = min(gray.shape[:2])
    line_height = _estimate_text_line_height(gray)
    return 3.0 if short_side < 600 or (line_height and line_height < 25) else 1.0


# preprocess OCR 인식 이미지 작업을 수행함
def preprocess_ocr_image(image: np.ndarray, *, return_binary: bool = False) -> np.ndarray:
    """Suppress pale watermark graphics and build an adaptive OCR image."""

    if (
        not isinstance(image, np.ndarray)
        or image.size == 0
        or image.dtype != np.uint8
        or image.ndim not in (2, 3)
        or (image.ndim == 3 and image.shape[2] not in (3, 4))
    ):
        raise ValueError("image must be a non-empty uint8 numpy array")

    scale = _ocr_upscale_factor(image)
    if scale > 1.0:
        resized = cv2.resize(
            image,
            dsize=None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LANCZOS4,
        )
    else:
        resized = image

    if resized.ndim == 2:
        gray = resized
        hsv = None
    elif resized.ndim == 3 and resized.shape[2] in (3, 4):
        gray = cv2.cvtColor(
            resized,
            cv2.COLOR_BGRA2GRAY if resized.shape[2] == 4 else cv2.COLOR_BGR2GRAY,
        )
        hsv = cv2.cvtColor(resized[:, :, :3], cv2.COLOR_BGR2HSV)
    else:
        raise ValueError("image must be grayscale, BGR, or BGRA")

    cleaned = cv2.bilateralFilter(gray, d=5, sigmaColor=30, sigmaSpace=30)
    if hsv is None:
        low_saturation = np.ones_like(gray, dtype=bool)
    else:
        low_saturation = hsv[:, :, 1] <= 45
    pale_graphic = low_saturation & (gray >= 200) & (gray < 248)
    cleaned[pale_graphic] = 255

    # Recover small strokes without amplifying scanner noise too aggressively.
    blurred = cv2.GaussianBlur(cleaned, (0, 0), 1.0)
    cleaned = cv2.addWeighted(cleaned, 1.35, blurred, -0.35, 0)
    normalized = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4)).apply(cleaned)
    otsu = cv2.threshold(
        cleaned,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]

    window = max(15, min(51, (min(cleaned.shape[:2]) // 18) | 1))
    mean = cv2.boxFilter(cleaned.astype(np.float32), -1, (window, window), normalize=True)
    squared_mean = cv2.boxFilter(
        np.square(cleaned.astype(np.float32)),
        -1,
        (window, window),
        normalize=True,
    )
    stddev = np.sqrt(np.maximum(0.0, squared_mean - np.square(mean)))
    sauvola_threshold = mean * (1.0 + 0.20 * (stddev / 128.0 - 1.0))
    sauvola = (cleaned.astype(np.float32) < sauvola_threshold).astype(np.uint8) * 255
    binary = cv2.bitwise_or(otsu, sauvola)
    binary[pale_graphic] = 0
    return binary if return_binary else normalized


# 표(테이블) lines for handwriting 요소를 제거함
def remove_table_lines_for_handwriting(
    image: np.ndarray,
    table_bbox: tuple[int, int, int, int],
    *,
    dpi: int = 300,
) -> np.ndarray:
    """Remove ruled-table strokes before handwriting OCR without resizing."""

    if image is None or image.ndim not in (2, 3):
        raise ValueError("image must be a grayscale or BGR numpy array")
    height, width = image.shape[:2]
    x0, y0, x1, y1 = (int(value) for value in table_bbox)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(width, x1), min(height, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("table_bbox does not intersect the image")

    output = image.copy()
    roi = image[y0:y1, x0:x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
    foreground = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]
    scale = max(12, int(round(dpi * 0.08)))
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (scale, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, scale))
    horizontal = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, vertical_kernel)
    line_mask = cv2.bitwise_or(horizontal, vertical)

    target = output[y0:y1, x0:x1]
    if target.ndim == 2:
        background = int(np.percentile(gray, 90))
        target[line_mask > 0] = background
    else:
        for channel in range(target.shape[2]):
            channel_bg = int(np.percentile(target[:, :, channel], 90))
            target[:, :, channel][line_mask > 0] = channel_bg

    residual = cv2.bitwise_and(foreground, cv2.bitwise_not(line_mask))
    bridge_length = max(3, min(9, int(round(dpi / 75))))
    horizontal_bridge = cv2.morphologyEx(
        residual,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (bridge_length, 1)),
    )
    vertical_bridge = cv2.morphologyEx(
        residual,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, bridge_length)),
    )
    restore_mask = cv2.bitwise_and(
        cv2.bitwise_or(horizontal_bridge, vertical_bridge),
        line_mask,
    )
    target[restore_mask > 0] = roi[restore_mask > 0]
    return output
