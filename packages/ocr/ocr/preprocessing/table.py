# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: table.py
# 경로: packages/ocr/ocr/preprocessing/table.py
# 목적: 이미지 내 표 영역 감지 및 테이블 셀 분할 전처리를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Conservative ruled-table geometry detection, independent of OCR pixels."""

from __future__ import annotations

import cv2
import numpy as np

from ..pipeline.models import BoundingBox
from ..structure.models import OCRCell, OCRTable


# 감지 표(테이블) lines 작업을 수행함
def detect_table_lines(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return separate horizontal/vertical uint8 masks without changing image.

    Input is a nonempty uint8 grayscale or BGR image with dark rules on a
    light background. Masks are detection artifacts, not OCR input images.
    """

    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError("Expected a uint8 grayscale or BGR image")
    if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[2] != 3):
        raise ValueError("Expected a grayscale or three-channel BGR image")
    if not image.size:
        raise ValueError("Image must not be empty")
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # Odd kernels preserve rule coordinates; no closing invents missing edges.
    horizontal_size = max(15, image.shape[1] // 40) | 1
    vertical_size = max(15, image.shape[0] // 40) | 1
    horizontal = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, np.ones((1, horizontal_size), dtype=np.uint8),
        borderType=cv2.BORDER_CONSTANT, borderValue=0,
    )
    vertical = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, np.ones((vertical_size, 1), dtype=np.uint8),
        borderType=cv2.BORDER_CONSTANT, borderValue=0,
    )
    return horizontal, vertical


# 감지 표 목록 작업을 수행함
def detect_tables(image: np.ndarray) -> tuple[OCRTable, ...]:
    """Detect axis-aligned ruled grids in input pixel coordinates.

    Only adjacent grid slots with at least 90% support on every edge are
    emitted. Missing slots remain missing; spans and words retain schema
    defaults. Merged cells, borderless tables and skew/perspective recovery
    are unsupported. Confidence is a [0, 0.95] geometry heuristic, not a
    calibrated probability or OCR confidence. A lone frame is not a table.
    """

    horizontal, vertical = detect_table_lines(image)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        cv2.bitwise_or(horizontal, vertical), connectivity=8,
    )
    tables: list[OCRTable] = []
    for label in range(1, count):
        x, y, width, height, _ = (int(value) for value in stats[label])
        component = labels[y:y + height, x:x + width] == label
        h = (horizontal[y:y + height, x:x + width] > 0) & component
        v = (vertical[y:y + height, x:x + width] > 0) & component
        xs = _rule_centers(v, axis=0)
        ys = _rule_centers(h, axis=1)
        if len(xs) < 2 or len(ys) < 2:
            continue
        slots = (len(xs) - 1) * (len(ys) - 1)
        if slots < 2:
            continue
        cells: list[OCRCell] = []
        support: list[float] = []
        for row, (top, bottom) in enumerate(zip(ys, ys[1:])):
            for column, (left, right) in enumerate(zip(xs, xs[1:])):
                if right - left < 8 or bottom - top < 8:
                    continue
                edges = (
                    _edge_support(h, top, left, right),
                    _edge_support(h, bottom, left, right),
                    _edge_support(v.T, left, top, bottom),
                    _edge_support(v.T, right, top, bottom),
                )
                if min(edges) < 0.9:
                    continue
                cells.append(OCRCell(
                    row=row, column=column,
                    bbox=BoundingBox(x + left, y + top, right - left, bottom - top),
                ))
                support.append(min(edges))
        if len(cells) < 2:
            continue
        tables.append(OCRTable(
            bbox=BoundingBox(x + xs[0], y + ys[0], xs[-1] - xs[0], ys[-1] - ys[0]),
            rows=len(ys) - 1, columns=len(xs) - 1, cells=tuple(cells),
            confidence=0.95 * min(support) * len(cells) / slots,
        ))
    return tuple(sorted(tables, key=lambda table: (table.bbox.y, table.bbox.x)))


# 변환 규칙 centers 작업을 수행함
def _rule_centers(mask: np.ndarray, *, axis: int) -> list[int]:
    positions = np.flatnonzero(np.count_nonzero(mask, axis=axis) >= 15)
    if not positions.size:
        return []
    groups = np.split(positions, np.flatnonzero(np.diff(positions) > 1) + 1)
    return [int((group[0] + group[-1]) // 2) for group in groups]


# edge support 작업을 수행함
def _edge_support(mask: np.ndarray, position: int, start: int, end: int) -> float:
    strip = mask[max(0, position - 1):position + 2, start:end + 1]
    return float(np.mean(np.any(strip, axis=0)))
