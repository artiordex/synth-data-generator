# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_style_extractor.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_style_extractor.py
# 목적: OCR 결과로부터 폰트 크기, 굵기, 색상 등 서식 스타일을 추출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np

BBox = Tuple[int, int, int, int]


# clip 바운딩 박스 작업을 수행함
def _clip_bbox(image: np.ndarray, bbox: BBox) -> BBox:
    if image is None or image.ndim not in (2, 3):
        raise ValueError("image must be a grayscale or BGR numpy array")
    height, width = image.shape[:2]
    x0, y0, x1, y1 = (int(value) for value in bbox)
    x0, x1 = max(0, x0), min(width, x1)
    y0, y1 = max(0, y0), min(height, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("bbox does not intersect the image")
    return x0, y0, x1, y1


# 셀 background 색상 요소를 추출하여 반환함
def extract_cell_background_color(image_bgr: np.ndarray, bbox: BBox) -> str:
    """Return the dominant printable cell fill as a normalized RGB hex color."""
    x0, y0, x1, y1 = _clip_bbox(image_bgr, bbox)
    crop = image_bgr[y0:y1, x0:x1]
    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)

    inset = max(2, min(crop.shape[:2]) // 12)
    interior = crop[inset:-inset, inset:-inset]
    if interior.size == 0:
        interior = crop

    # Dark glyphs and colored pen strokes are not cell background. Quantizing
    # before taking the mode is stable for JPEG/scanner noise around flat fills.
    pixels = interior.reshape(-1, 3)
    luminance = pixels.mean(axis=1)
    candidates = pixels[luminance >= np.percentile(luminance, 35)]
    if len(candidates) == 0:
        candidates = pixels
    quantized = (candidates // 8) * 8
    colors, counts = np.unique(quantized, axis=0, return_counts=True)
    dominant = colors[int(np.argmax(counts))].astype(int) + 4
    dominant = np.clip(dominant, 0, 255)
    dominant[dominant >= 244] = 255
    blue, green, red = (int(value) for value in dominant)
    return f"#{red:02x}{green:02x}{blue:02x}"


# classify edge 작업을 수행함
def _classify_edge(edge_gray: np.ndarray, *, horizontal: bool) -> str:
    dark = edge_gray < 150
    line_strength = dark.mean(axis=1 if horizontal else 0)
    strong = np.flatnonzero(line_strength >= 0.72)
    if strong.size:
        groups = np.split(strong, np.where(np.diff(strong) > 1)[0] + 1)
        if len(groups) >= 2 and groups[-1][0] - groups[0][-1] >= 1:
            return "double"
        return "solid"

    # A dashed rule has multiple dark runs along one candidate scan line but a
    # lower global coverage than a solid rule.
    axis = 1 if horizontal else 0
    best = dark[np.argmax(line_strength), :] if horizontal else dark[:, np.argmax(line_strength)]
    transitions = np.diff(np.pad(best.astype(np.int8), (1, 1)))
    runs = int(np.count_nonzero(transitions == 1))
    coverage = float(best.mean())
    if runs >= 3 and coverage >= 0.18:
        return "dashed"
    return "none"


# 감지 셀 테두리 스타일 목록 작업을 수행함
def detect_cell_border_styles(image: np.ndarray, bbox: BBox) -> Dict[str, str]:
    """Classify top/right/bottom/left borders as none, solid, dashed or double."""
    x0, y0, x1, y1 = _clip_bbox(image, bbox)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    radius = max(3, min(8, min(x1 - x0, y1 - y0) // 5))
    trim = min(4, max(0, (x1 - x0) // 10), max(0, (y1 - y0) // 10))

    horizontal_slice = slice(x0 + trim, max(x0 + trim + 1, x1 - trim))
    vertical_slice = slice(y0 + trim, max(y0 + trim + 1, y1 - trim))
    return {
        "top": _classify_edge(gray[max(0, y0 - radius):min(gray.shape[0], y0 + radius + 1), horizontal_slice], horizontal=True),
        "right": _classify_edge(gray[vertical_slice, max(0, x1 - radius - 1):min(gray.shape[1], x1 + radius)], horizontal=False),
        "bottom": _classify_edge(gray[max(0, y1 - radius - 1):min(gray.shape[0], y1 + radius), horizontal_slice], horizontal=True),
        "left": _classify_edge(gray[vertical_slice, max(0, x0 - radius):min(gray.shape[1], x0 + radius + 1)], horizontal=False),
    }


# 감지 텍스트 정렬 상태 작업을 수행함
def detect_text_alignment(cell_bbox: BBox, text_bbox: BBox) -> str:
    """Infer horizontal alignment from text geometry without changing layout."""
    cx0, _, cx1, _ = cell_bbox
    tx0, _, tx1, _ = text_bbox
    if tx1 <= tx0 or cx1 <= cx0:
        return "left"
    left_gap = max(0, tx0 - cx0)
    right_gap = max(0, cx1 - tx1)
    tolerance = max(3.0, (cx1 - cx0) * 0.08)
    if abs(left_gap - right_gap) <= tolerance:
        return "center"
    return "right" if right_gap < left_gap else "left"

