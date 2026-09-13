# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_table_geometry.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_table_geometry.py
# 목적: OCR 단어 좌표 기반 격자 표 구조 및 셀 좌표를 복원함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Geometry-only table detection helpers for OCR reconstruction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np


@dataclass
class GridCell:
    """Geometry-first table cell shared by ruled and borderless detectors."""

    row_start: int
    row_end: int
    col_start: int
    col_end: int
    bbox: tuple[int, int, int, int]
    is_border_detected: bool = True
    bg_color_hex: str = "#ffffff"
    border_styles: dict[str, str] = field(default_factory=dict)
    text_align: str = "left"
    borders: dict[str, bool] = field(default_factory=dict)
    border_confidence: dict[str, float] = field(default_factory=dict)
    grid_confidence: float = 1.0
    source: Literal["ruled_v2", "ruled_legacy", "borderless"] = "ruled_legacy"

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        if self.row_start < 0 or self.col_start < 0:
            raise ValueError("cell coordinates must be non-negative")
        if self.row_end <= self.row_start or self.col_end <= self.col_start:
            raise ValueError("cell end coordinates must be exclusive and greater than start")
        x0, y0, x1, y1 = self.bbox
        if x1 <= x0 or y1 <= y0:
            raise ValueError("cell bbox must have positive width and height")

    # rowspan 작업을 수행함
    @property
    def rowspan(self) -> int:
        return self.row_end - self.row_start

    # colspan 작업을 수행함
    @property
    def colspan(self) -> int:
        return self.col_end - self.col_start


@dataclass(frozen=True)
class DetectedTableGrid:
    bbox: tuple[int, int, int, int]
    cells: tuple[GridCell, ...]
    rows_count: int
    cols_count: int
    x_lines: tuple[int, ...] = ()
    y_lines: tuple[int, ...] = ()
    confidence: float = 1.0
    source: Literal["ruled_v2", "ruled_legacy", "borderless"] = "ruled_legacy"


@dataclass(frozen=True)
class LineSegment:
    """A ruled-line observation in deskewed page pixel coordinates."""

    x0: int
    y0: int
    x1: int
    y1: int
    orientation: Literal["horizontal", "vertical"]
    confidence: float


class _DisjointSet:
    # _DisjointSet 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.members = [{index} for index in range(size)]

    # find 작업을 수행함
    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    # union if rectangular 작업을 수행함
    def union_if_rectangular(self, left: int, right: int, cols: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return True
        combined = self.members[left_root] | self.members[right_root]
        rows = [item // cols for item in combined]
        columns = [item % cols for item in combined]
        expected_size = (max(rows) - min(rows) + 1) * (max(columns) - min(columns) + 1)
        if len(combined) != expected_size:
            return False
        if len(self.members[left_root]) < len(self.members[right_root]):
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.members[left_root] |= self.members[right_root]
        self.members[right_root] = set()
        return True


# foreground 마스킹 작업을 수행함
def _foreground_mask(gray: np.ndarray) -> np.ndarray:
    block = max(15, min(61, (min(gray.shape[:2]) // 12) | 1))
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 9
    )
    otsu = cv2.threshold(
        cv2.GaussianBlur(gray, (3, 3), 0),
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]
    # Adaptive thresholding is resilient to coloured cells; Otsu only restores
    # dark pixels already close to an adaptive foreground neighbourhood.
    neighbourhood = cv2.dilate(adaptive, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.bitwise_or(adaptive, cv2.bitwise_and(otsu, neighbourhood))


# estimated glyph 높이 작업을 수행함
def _estimated_glyph_height(foreground: np.ndarray) -> float:
    count, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    heights = [
        float(stats[index, cv2.CC_STAT_HEIGHT])
        for index in range(1, count)
        if 3 <= stats[index, cv2.CC_STAT_AREA]
        and 3 <= stats[index, cv2.CC_STAT_HEIGHT] <= max(8, foreground.shape[0] // 12)
        and stats[index, cv2.CC_STAT_WIDTH] <= foreground.shape[1] // 5
    ]
    return float(np.median(heights)) if heights else 12.0


# line segments 요소를 추출하여 반환함
def _extract_line_segments(
    mask: np.ndarray,
    orientation: Literal["horizontal", "vertical"],
    *,
    min_length: int,
    glyph_height: float,
) -> tuple[np.ndarray, list[LineSegment]]:
    kernel_length = max(7, int(round(min_length * 0.65)))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (kernel_length, 1) if orientation == "horizontal" else (1, kernel_length),
    )
    line_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    count, _, stats, _ = cv2.connectedComponentsWithStats(line_mask, 8)
    height, width = mask.shape[:2]
    segments: list[LineSegment] = []
    for index in range(1, count):
        x, y, component_w, component_h, area = (
            int(value) for value in stats[index]
        )
        length = component_w if orientation == "horizontal" else component_h
        thickness = component_h if orientation == "horizontal" else component_w
        page_span = width if orientation == "horizontal" else height
        edge_coordinate = y + component_h / 2 if orientation == "horizontal" else x + component_w / 2
        edge_span = height if orientation == "horizontal" else width
        if length < min_length or thickness > max(7, glyph_height * 0.65):
            continue
        if edge_coordinate <= 2 or edge_coordinate >= edge_span - 3:
            if length >= page_span * 0.85:
                continue
        aspect_score = min(1.0, length / max(1.0, thickness * 12.0))
        length_score = min(1.0, length / max(1.0, min_length * 2.0))
        density_score = min(1.0, area / max(1.0, length * max(1, thickness)))
        confidence = 0.35 * aspect_score + 0.40 * length_score + 0.25 * density_score
        if orientation == "horizontal":
            coordinate = int(round(y + (component_h - 1) / 2))
            segments.append(LineSegment(x, coordinate, x + component_w - 1, coordinate, orientation, confidence))
        else:
            coordinate = int(round(x + (component_w - 1) / 2))
            segments.append(LineSegment(coordinate, y, coordinate, y + component_h - 1, orientation, confidence))
    return line_mask, segments


# gap has strong 텍스트 작업을 수행함
def _gap_has_strong_text(
    foreground: np.ndarray,
    left: LineSegment,
    right: LineSegment,
    glyph_height: float,
) -> bool:
    pad = max(2, int(round(glyph_height * 0.35)))
    if left.orientation == "horizontal":
        x0, x1 = left.x1 + 1, right.x0
        y = int(round((left.y0 + right.y0) / 2))
        roi = foreground[max(0, y - pad):min(foreground.shape[0], y + pad + 1), x0:x1]
    else:
        y0, y1 = left.y1 + 1, right.y0
        x = int(round((left.x0 + right.x0) / 2))
        roi = foreground[y0:y1, max(0, x - pad):min(foreground.shape[1], x + pad + 1)]
    if not roi.size:
        return False
    density = np.count_nonzero(roi) / roi.size
    # A perpendicular rule inside the gap is narrow on the longitudinal axis
    # and must not be mistaken for text. Glyphs occupy most columns (or rows)
    # across a short gap, while a crossing rule occupies only a few.
    longitudinal_occupancy = (
        np.count_nonzero(np.any(roi > 0, axis=0)) / max(1, roi.shape[1])
        if left.orientation == "horizontal"
        else np.count_nonzero(np.any(roi > 0, axis=1)) / max(1, roi.shape[0])
    )
    return bool(density >= 0.18 and longitudinal_occupancy >= 0.55)


# 병합 collinear segments 작업을 수행함
def _merge_collinear_segments(
    segments: list[LineSegment],
    foreground: np.ndarray,
    *,
    tolerance: int,
    glyph_height: float,
) -> list[LineSegment]:
    if not segments:
        return []
    orientation = segments[0].orientation
    coordinate = lambda segment: segment.y0 if orientation == "horizontal" else segment.x0
    ordered = sorted(segments, key=lambda segment: (coordinate(segment), segment.x0, segment.y0))
    clusters: list[list[LineSegment]] = []
    for segment in ordered:
        target = next(
            (cluster for cluster in reversed(clusters)
             if abs(coordinate(segment) - np.median([coordinate(item) for item in cluster])) <= tolerance),
            None,
        )
        if target is None:
            clusters.append([segment])
        else:
            target.append(segment)

    merged: list[LineSegment] = []
    max_gap = max(tolerance * 4, int(round(glyph_height * 1.5)))
    for cluster in clusters:
        axis = int(round(float(np.median([coordinate(item) for item in cluster]))))
        items = sorted(cluster, key=lambda item: item.x0 if orientation == "horizontal" else item.y0)
        current = items[0]
        for following in items[1:]:
            gap = (following.x0 - current.x1 - 1) if orientation == "horizontal" else (following.y0 - current.y1 - 1)
            if gap <= max_gap and (gap <= 0 or not _gap_has_strong_text(foreground, current, following, glyph_height)):
                if orientation == "horizontal":
                    current = LineSegment(
                        min(current.x0, following.x0), axis,
                        max(current.x1, following.x1), axis, orientation,
                        min(1.0, max(current.confidence, following.confidence) + 0.05),
                    )
                else:
                    current = LineSegment(
                        axis, min(current.y0, following.y0), axis,
                        max(current.y1, following.y1), orientation,
                        min(1.0, max(current.confidence, following.confidence) + 0.05),
                    )
            else:
                merged.append(current)
                current = following
        merged.append(current)
    return merged


# segment components 작업을 수행함
def _segment_components(
    horizontal: list[LineSegment], vertical: list[LineSegment], tolerance: int
) -> list[tuple[list[LineSegment], list[LineSegment]]]:
    all_segments = horizontal + vertical
    dsu = _DisjointSet(len(all_segments))
    offset = len(horizontal)
    for h_index, h_segment in enumerate(horizontal):
        for v_index, v_segment in enumerate(vertical):
            if (
                h_segment.x0 - tolerance <= v_segment.x0 <= h_segment.x1 + tolerance
                and v_segment.y0 - tolerance <= h_segment.y0 <= v_segment.y1 + tolerance
            ):
                # This union is for graph connectivity; a cross intersection is
                # always a valid two-node component, so rectangularity is moot.
                left, right = dsu.find(h_index), dsu.find(offset + v_index)
                if left != right:
                    dsu.parent[right] = left
                    dsu.members[left] |= dsu.members[right]
                    dsu.members[right] = set()
    grouped: dict[int, list[int]] = {}
    for index in range(len(all_segments)):
        grouped.setdefault(dsu.find(index), []).append(index)
    result = []
    for indices in grouped.values():
        hs = [all_segments[index] for index in indices if index < offset]
        vs = [all_segments[index] for index in indices if index >= offset]
        if hs and vs:
            result.append((hs, vs))
    return result


# cluster line 기하 좌표 작업을 수행함
def _cluster_line_coordinates(values: list[int], tolerance: int) -> list[int]:
    return snap_grid_boundaries(values, tolerance=tolerance)


# edge support 작업을 수행함
def _edge_support(
    segments: list[LineSegment],
    coordinate: int,
    start: int,
    end: int,
    *,
    tolerance: int,
) -> float:
    intervals: list[tuple[int, int]] = []
    horizontal = bool(segments and segments[0].orientation == "horizontal")
    for segment in segments:
        segment_coordinate = segment.y0 if horizontal else segment.x0
        if abs(segment_coordinate - coordinate) > tolerance:
            continue
        low = max(start, segment.x0 if horizontal else segment.y0)
        high = min(end, segment.x1 if horizontal else segment.y1)
        if high > low:
            intervals.append((low, high))
    if not intervals or end <= start:
        return 0.0
    covered = 0
    current_start, current_end = sorted(intervals)[0]
    for low, high in sorted(intervals)[1:]:
        if low <= current_end + 1:
            current_end = max(current_end, high)
        else:
            covered += current_end - current_start
            current_start, current_end = low, high
    covered += current_end - current_start
    return max(0.0, min(1.0, covered / max(1, end - start)))


# 셀 목록 from 격자 구조 graph 작업을 수행함
def _cells_from_grid_graph(
    x_lines: list[int],
    y_lines: list[int],
    horizontal: list[LineSegment],
    vertical: list[LineSegment],
    tolerance: int,
    intersection_confidence: float,
) -> tuple[list[GridCell], float]:
    rows, cols = len(y_lines) - 1, len(x_lines) - 1
    if rows < 1 or cols < 1:
        return [], 0.0
    primitive_borders: list[dict[str, float]] = []
    for row in range(rows):
        for col in range(cols):
            x0, x1 = x_lines[col], x_lines[col + 1]
            y0, y1 = y_lines[row], y_lines[row + 1]
            primitive_borders.append({
                "top": _edge_support(horizontal, y0, x0, x1, tolerance=tolerance),
                "right": _edge_support(vertical, x1, y0, y1, tolerance=tolerance),
                "bottom": _edge_support(horizontal, y1, x0, x1, tolerance=tolerance),
                "left": _edge_support(vertical, x0, y0, y1, tolerance=tolerance),
            })

    dsu = _DisjointSet(rows * cols)
    absent_edges: list[tuple[float, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            index = row * cols + col
            if col + 1 < cols:
                support = min(primitive_borders[index]["right"], primitive_borders[index + 1]["left"])
                if support < 0.22:
                    absent_edges.append((support, index, index + 1))
            if row + 1 < rows:
                support = min(primitive_borders[index]["bottom"], primitive_borders[index + cols]["top"])
                if support < 0.22:
                    absent_edges.append((support, index, index + cols))
    for _, left, right in sorted(absent_edges):
        dsu.union_if_rectangular(left, right, cols)

    groups: dict[int, set[int]] = {}
    for index in range(rows * cols):
        groups.setdefault(dsu.find(index), set()).add(index)
    cells: list[GridCell] = []
    border_scores: list[float] = []
    for members in groups.values():
        member_rows = [item // cols for item in members]
        member_cols = [item % cols for item in members]
        row_start, row_end = min(member_rows), max(member_rows) + 1
        col_start, col_end = min(member_cols), max(member_cols) + 1
        bbox = (x_lines[col_start], y_lines[row_start], x_lines[col_end], y_lines[row_end])
        confidences = {
            "top": _edge_support(horizontal, y_lines[row_start], bbox[0], bbox[2], tolerance=tolerance),
            "right": _edge_support(vertical, x_lines[col_end], bbox[1], bbox[3], tolerance=tolerance),
            "bottom": _edge_support(horizontal, y_lines[row_end], bbox[0], bbox[2], tolerance=tolerance),
            "left": _edge_support(vertical, x_lines[col_start], bbox[1], bbox[3], tolerance=tolerance),
        }
        borders = {side: score >= 0.45 for side, score in confidences.items()}
        cell_confidence = 0.55 * intersection_confidence + 0.45 * (sum(confidences.values()) / 4.0)
        border_scores.extend(confidences.values())
        cells.append(GridCell(
            row_start=row_start,
            row_end=row_end,
            col_start=col_start,
            col_end=col_end,
            bbox=bbox,
            is_border_detected=any(borders.values()),
            borders=borders,
            border_confidence=confidences,
            grid_confidence=cell_confidence,
            source="ruled_v2",
        ))

    occupied = {
        (row, col)
        for cell in cells
        for row in range(cell.row_start, cell.row_end)
        for col in range(cell.col_start, cell.col_end)
    }
    if occupied != {(row, col) for row in range(rows) for col in range(cols)}:
        return [], 0.0
    confidence = 0.65 * intersection_confidence + 0.35 * (
        sum(border_scores) / max(1, len(border_scores))
    )
    return sorted(cells, key=lambda cell: (cell.row_start, cell.col_start)), confidence


# 감지 ruled 표(테이블) grids v2 작업을 수행함
def detect_ruled_table_grids_v2(
    img_gray: np.ndarray,
    *,
    min_table_area: int = 8000,
    min_line_length_ratio: float = 0.06,
    line_merge_tolerance: int = 5,
) -> list[DetectedTableGrid]:
    """Detect ruled tables as a line-segment/grid graph in deskewed pixels.

    Missing internal edges define merged cells. OCR text is deliberately not an
    input, so a wide word can never erase an observed border or create a span.
    """

    if not isinstance(img_gray, np.ndarray) or img_gray.size == 0:
        return []
    if img_gray.ndim == 3:
        gray = cv2.cvtColor(img_gray[:, :, :3], cv2.COLOR_BGR2GRAY)
    elif img_gray.ndim == 2:
        gray = img_gray
    else:
        return []
    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    height, width = gray.shape[:2]
    foreground = _foreground_mask(gray)
    glyph_height = _estimated_glyph_height(foreground)
    horizontal_min = max(12, int(round(width * min_line_length_ratio)), int(round(glyph_height * 2.2)))
    vertical_min = max(12, int(round(height * min_line_length_ratio)), int(round(glyph_height * 2.2)))
    _, horizontal = _extract_line_segments(
        foreground, "horizontal", min_length=horizontal_min, glyph_height=glyph_height
    )
    _, vertical = _extract_line_segments(
        foreground, "vertical", min_length=vertical_min, glyph_height=glyph_height
    )
    horizontal = _merge_collinear_segments(
        horizontal, foreground, tolerance=line_merge_tolerance, glyph_height=glyph_height
    )
    vertical = _merge_collinear_segments(
        vertical, foreground, tolerance=line_merge_tolerance, glyph_height=glyph_height
    )

    tables: list[DetectedTableGrid] = []
    for h_segments, v_segments in _segment_components(horizontal, vertical, line_merge_tolerance):
        x_lines = _cluster_line_coordinates([segment.x0 for segment in v_segments], line_merge_tolerance)
        y_lines = _cluster_line_coordinates([segment.y0 for segment in h_segments], line_merge_tolerance)
        if len(x_lines) < 2 or len(y_lines) < 2:
            continue
        bbox = (min(x_lines), min(y_lines), max(x_lines), max(y_lines))
        if (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) < min_table_area:
            continue
        if bbox[2] - bbox[0] < width * 0.12:
            continue
        supported_intersections = 0
        for x in x_lines:
            for y in y_lines:
                h_support = any(
                    abs(segment.y0 - y) <= line_merge_tolerance
                    and segment.x0 - line_merge_tolerance <= x <= segment.x1 + line_merge_tolerance
                    for segment in h_segments
                )
                v_support = any(
                    abs(segment.x0 - x) <= line_merge_tolerance
                    and segment.y0 - line_merge_tolerance <= y <= segment.y1 + line_merge_tolerance
                    for segment in v_segments
                )
                supported_intersections += int(h_support and v_support)
        intersection_confidence = supported_intersections / max(1, len(x_lines) * len(y_lines))
        if intersection_confidence < 0.30:
            continue
        cells, confidence = _cells_from_grid_graph(
            x_lines, y_lines, h_segments, v_segments, line_merge_tolerance, intersection_confidence
        )
        if not cells or confidence < 0.32:
            continue
        tables.append(DetectedTableGrid(
            bbox=bbox,
            cells=tuple(cells),
            rows_count=len(y_lines) - 1,
            cols_count=len(x_lines) - 1,
            x_lines=tuple(x_lines),
            y_lines=tuple(y_lines),
            confidence=confidence,
            source="ruled_v2",
        ))
    return sorted(tables, key=lambda table: (table.bbox[1], table.bbox[0]))


# 감지 ruled 표(테이블) grids 작업을 수행함
def detect_ruled_table_grids(
    img_gray: np.ndarray,
    min_cell_w: int = 30,
    min_cell_h: int = 15,
    min_table_area: int = 8000,
) -> list[DetectedTableGrid]:
    """Detect ruled table grids through OpenCV morphology."""

    h, w = img_gray.shape[:2]
    thresh = cv2.adaptiveThreshold(
        ~img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2
    )

    h_scale = max(20, w // 40)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_scale, 1))
    h_lines = cv2.erode(thresh, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_lines, h_kernel, iterations=1)

    v_scale = max(15, h // 40)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_scale))
    v_lines = cv2.erode(thresh, v_kernel, iterations=1)
    v_lines = cv2.dilate(v_lines, v_kernel, iterations=1)

    table_structure = cv2.add(h_lines, v_lines)
    table_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    table_structure_dilated = cv2.dilate(table_structure, table_kernel, iterations=2)
    contours, _ = cv2.findContours(
        table_structure_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    tables: list[DetectedTableGrid] = []
    for cnt in contours:
        tx, ty, tw, th = cv2.boundingRect(cnt)
        if tw * th < min_table_area or tw < w * 0.2:
            continue

        table_roi = table_structure[ty:ty + th, tx:tx + tw]
        cell_contours, _ = cv2.findContours(
            table_roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        detected_cell_boxes: list[tuple[int, int, int, int]] = []
        for c_cnt in cell_contours:
            cx, cy, cw, ch = cv2.boundingRect(c_cnt)
            if (
                cw >= min_cell_w
                and ch >= min_cell_h
                and cw < tw * 0.98
                and ch < th * 0.98
                and (cw * ch) > 400
            ):
                detected_cell_boxes.append((tx + cx, ty + cy, tx + cx + cw, ty + cy + ch))

        if len(detected_cell_boxes) < 4:
            continue

        detected_cell_boxes = sorted(detected_cell_boxes, key=lambda b: (b[1], b[0]))
        y_centers = [(b[1] + b[3]) / 2.0 for b in detected_cell_boxes]
        row_bands: list[float] = []
        for yc in sorted(y_centers):
            if not any(abs(yc - rb) < 15 for rb in row_bands):
                row_bands.append(yc)
        row_bands.sort()

        x_centers = [(b[0] + b[2]) / 2.0 for b in detected_cell_boxes]
        col_bands: list[float] = []
        for xc in sorted(x_centers):
            if not any(abs(xc - cb) < 20 for cb in col_bands):
                col_bands.append(xc)
        col_bands.sort()

        num_rows = max(1, len(row_bands))
        num_cols = max(1, len(col_bands))
        cells: list[GridCell] = []
        for box in detected_cell_boxes:
            bc_x = (box[0] + box[2]) / 2.0
            bc_y = (box[1] + box[3]) / 2.0
            best_r = min(range(num_rows), key=lambda r: abs(bc_y - row_bands[r]))
            best_c = min(range(num_cols), key=lambda c: abs(bc_x - col_bands[c]))
            c_w = box[2] - box[0]
            c_h = box[3] - box[1]
            c_span = max(1, round(c_w / max(30, (tw / num_cols))))
            r_span = max(1, round(c_h / max(20, (th / num_rows))))
            cells.append(GridCell(best_r, best_r + r_span, best_c, best_c + c_span, box))

        vertical_roi = v_lines[ty:ty + th, tx:tx + tw]
        horizontal_roi = h_lines[ty:ty + th, tx:tx + tw]
        _, nonzero_x = np.where(vertical_roi > 0)
        nonzero_y, _ = np.where(horizontal_roi > 0)
        normalized_bbox = (tx, ty, tx + tw, ty + th)
        if nonzero_x.size and nonzero_y.size:
            # edge center 작업을 수행함
            def edge_center(values: np.ndarray, first: bool) -> int:
                unique = np.unique(values)
                groups = np.split(unique, np.where(np.diff(unique) > 1)[0] + 1)
                group = groups[0] if first else groups[-1]
                return int(round(float(np.mean(group))))

            normalized_bbox = (
                tx + edge_center(nonzero_x, True),
                ty + edge_center(nonzero_y, True),
                tx + edge_center(nonzero_x, False) + 1,
                ty + edge_center(nonzero_y, False) + 1,
            )

        tables.append(DetectedTableGrid(normalized_bbox, tuple(cells), num_rows, num_cols))

    return sorted(tables, key=lambda table: table.bbox[1])


# word box 작업을 수행함
def word_box(word: Any) -> tuple[int, int, int, int]:
    box = getattr(word, "bbox", None)
    if box is None and isinstance(word, dict):
        box = word.get("bbox")
    if box is None or len(box) != 4:
        raise ValueError("OCR word must provide a four-coordinate bbox")
    return tuple(int(round(float(value))) for value in box)


# snap 격자 구조 boundaries 작업을 수행함
def snap_grid_boundaries(*coordinate_sets: list[int], tolerance: int = 5) -> list[int]:
    """Cluster independently detected grid coordinates within ``tolerance`` px."""

    coordinates = sorted(int(value) for values in coordinate_sets for value in values)
    if not coordinates:
        return []
    clusters: list[list[int]] = [[coordinates[0]]]
    for coordinate in coordinates[1:]:
        if coordinate - clusters[-1][-1] <= tolerance:
            clusters[-1].append(coordinate)
        else:
            clusters.append([coordinate])
    return [int(round(sum(cluster) / len(cluster))) for cluster in clusters]


# projection boundaries 작업을 수행함
def _projection_boundaries(
    intervals: list[tuple[int, int]], outer_start: int, outer_end: int
) -> list[int]:
    if not intervals:
        return []
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    boundaries = [outer_start]
    for left, right in zip(merged, merged[1:]):
        gap = right[0] - left[1]
        if gap >= 4:
            boundaries.append(int(round((left[1] + right[0]) / 2)))
    boundaries.append(outer_end)
    return snap_grid_boundaries(boundaries, tolerance=5)


# 감지 borderless 표(테이블) 셀 목록 작업을 수행함
def detect_borderless_table_cells(
    img_gray: np.ndarray,
    text_words: list[Any],
    *,
    min_rows: int = 2,
    min_cols: int = 2,
) -> list[GridCell]:
    """Infer a borderless grid from horizontal/vertical whitespace projections."""

    if img_gray is None or img_gray.ndim not in (2, 3) or not text_words:
        return []

    boxes = [word_box(word) for word in text_words]
    x0 = max(0, min(box[0] for box in boxes))
    y0 = max(0, min(box[1] for box in boxes))
    x1 = min(img_gray.shape[1], max(box[2] for box in boxes))
    y1 = min(img_gray.shape[0], max(box[3] for box in boxes))

    median_h = float(np.median([box[3] - box[1] for box in boxes]))
    median_w = float(np.median([box[2] - box[0] for box in boxes]))
    pad_x = max(4, int(round(median_w * 0.15)))
    pad_y = max(3, int(round(median_h * 0.35)))
    x0, x1 = max(0, x0 - pad_x), min(img_gray.shape[1], x1 + pad_x)
    y0, y1 = max(0, y0 - pad_y), min(img_gray.shape[0], y1 + pad_y)

    x_intervals = [(box[0], box[2]) for box in boxes]
    y_intervals = [(box[1], box[3]) for box in boxes]
    x_boundaries = _projection_boundaries(x_intervals, x0, x1)
    y_boundaries = _projection_boundaries(y_intervals, y0, y1)
    if len(x_boundaries) - 1 < min_cols or len(y_boundaries) - 1 < min_rows:
        return []

    rows_count, cols_count = len(y_boundaries) - 1, len(x_boundaries) - 1
    occupancy: set[tuple[int, int]] = set()
    for box in boxes:
        center_x, center_y = bbox_center(box)
        col = next(
            (index for index in range(cols_count)
             if x_boundaries[index] <= center_x <= x_boundaries[index + 1]),
            None,
        )
        row = next(
            (index for index in range(rows_count)
             if y_boundaries[index] <= center_y <= y_boundaries[index + 1]),
            None,
        )
        if row is not None and col is not None:
            occupancy.add((row, col))
    density = len(occupancy) / max(1, rows_count * cols_count)
    if density < 0.55:
        return []
    if any(sum((row, col) in occupancy for col in range(cols_count)) < min_cols
           for row in range(rows_count)):
        return []
    if any(sum((row, col) in occupancy for row in range(rows_count)) < min_rows
           for col in range(cols_count)):
        return []

    return [
        GridCell(
            row_start=row,
            row_end=row + 1,
            col_start=col,
            col_end=col + 1,
            bbox=(
                x_boundaries[col],
                y_boundaries[row],
                x_boundaries[col + 1],
                y_boundaries[row + 1],
            ),
            is_border_detected=False,
            borders={side: False for side in ("top", "right", "bottom", "left")},
            border_confidence={side: 0.0 for side in ("top", "right", "bottom", "left")},
            grid_confidence=0.45,
            source="borderless",
        )
        for row in range(len(y_boundaries) - 1)
        for col in range(len(x_boundaries) - 1)
    ]


# intersection area 작업을 수행함
def intersection_area(
    left: tuple[int, int, int, int], right: tuple[int, int, int, int]
) -> int:
    x0, y0 = max(left[0], right[0]), max(left[1], right[1])
    x1, y1 = min(left[2], right[2]), min(left[3], right[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


# 바운딩 박스 center 작업을 수행함
def bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


# point in 바운딩 박스 작업을 수행함
def point_in_bbox(point: tuple[float, float], bbox: tuple[int, int, int, int]) -> bool:
    x, y = point
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


# word inside any 표(테이블) 작업을 수행함
def word_inside_any_table(word: Any, tables: list[Any]) -> bool:
    box = word_box(word)
    area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
    return any(intersection_area(box, table.bbox) / area >= 0.35 for table in tables)


# resolve 스팬 conflicts 작업을 수행함
def resolve_span_conflicts(
    cells: list[GridCell],
    text_words: list[Any],
    *,
    overlap_threshold: float = 0.18,
) -> list[GridCell]:
    """Merge a rectangular set of cells when one OCR box crosses boundaries."""

    resolved = list(cells)
    for word in sorted(
        text_words,
        key=lambda item: -(
            (word_box(item)[2] - word_box(item)[0])
            * (word_box(item)[3] - word_box(item)[1])
        ),
    ):
        box = word_box(word)
        word_area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
        touched = [
            cell for cell in resolved
            if intersection_area(cell.bbox, box) / word_area >= overlap_threshold
        ]
        if len(touched) < 2:
            continue

        visible_internal_border = False
        for left_index, left_cell in enumerate(touched):
            for right_cell in touched[left_index + 1:]:
                horizontal_neighbours = (
                    left_cell.col_end == right_cell.col_start
                    or right_cell.col_end == left_cell.col_start
                ) and max(left_cell.row_start, right_cell.row_start) < min(
                    left_cell.row_end, right_cell.row_end
                )
                vertical_neighbours = (
                    left_cell.row_end == right_cell.row_start
                    or right_cell.row_end == left_cell.row_start
                ) and max(left_cell.col_start, right_cell.col_start) < min(
                    left_cell.col_end, right_cell.col_end
                )
                if horizontal_neighbours:
                    first, second = (
                        (left_cell, right_cell)
                        if left_cell.col_end == right_cell.col_start
                        else (right_cell, left_cell)
                    )
                    visible_internal_border |= bool(
                        first.borders.get("right") or second.borders.get("left")
                    )
                if vertical_neighbours:
                    first, second = (
                        (left_cell, right_cell)
                        if left_cell.row_end == right_cell.row_start
                        else (right_cell, left_cell)
                    )
                    visible_internal_border |= bool(
                        first.borders.get("bottom") or second.borders.get("top")
                    )
        if visible_internal_border:
            continue

        row_start = min(cell.row_start for cell in touched)
        row_end = max(cell.row_end for cell in touched)
        col_start = min(cell.col_start for cell in touched)
        col_end = max(cell.col_end for cell in touched)
        occupied = {
            (row, col)
            for cell in touched
            for row in range(cell.row_start, cell.row_end)
            for col in range(cell.col_start, cell.col_end)
        }
        expected = {
            (row, col)
            for row in range(row_start, row_end)
            for col in range(col_start, col_end)
        }
        if occupied != expected:
            continue

        touched_ids = {id(cell) for cell in touched}
        merged = GridCell(
            row_start=row_start,
            row_end=row_end,
            col_start=col_start,
            col_end=col_end,
            bbox=(
                min(cell.bbox[0] for cell in touched),
                min(cell.bbox[1] for cell in touched),
                max(cell.bbox[2] for cell in touched),
                max(cell.bbox[3] for cell in touched),
            ),
            is_border_detected=all(cell.is_border_detected for cell in touched),
            borders={
                "top": any(cell.borders.get("top", False) for cell in touched if cell.row_start == row_start),
                "right": any(cell.borders.get("right", False) for cell in touched if cell.col_end == col_end),
                "bottom": any(cell.borders.get("bottom", False) for cell in touched if cell.row_end == row_end),
                "left": any(cell.borders.get("left", False) for cell in touched if cell.col_start == col_start),
            },
            grid_confidence=min(cell.grid_confidence for cell in touched),
            source=touched[0].source,
        )
        resolved = [cell for cell in resolved if id(cell) not in touched_ids]
        resolved.append(merged)

    return sorted(resolved, key=lambda cell: (cell.row_start, cell.col_start))
