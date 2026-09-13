# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_table_geometry.py
# 경로: packages/synthetic_engine/tests/test_ocr_table_geometry.py
# 목적: 표 좌표 감지 및 셀 기하 구조 복원을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from synthetic_engine.exporters.ocr_table_geometry import (
    GridCell,
    bbox_center,
    detect_borderless_table_cells,
    detect_ruled_table_grids,
    detect_ruled_table_grids_v2,
    intersection_area,
    point_in_bbox,
    resolve_span_conflicts,
    snap_grid_boundaries,
    word_inside_any_table,
)


@dataclass
class DummyWord:
    text: str
    bbox: tuple[int, int, int, int]

    # center 작업을 수행함
    @property
    def center(self) -> tuple[float, float]:
        return bbox_center(self.bbox)


@dataclass
class DummyTable:
    bbox: tuple[int, int, int, int]


# ruled 표(테이블) 격자 구조 detection returns 기하 구조 셀 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_ruled_table_grid_detection_returns_geometry_cells() -> None:
    image = np.full((180, 260), 255, dtype=np.uint8)
    for x in (30, 110, 190):
        cv2.line(image, (x, 25), (x, 145), 0, 2)
    for y in (25, 85, 145):
        cv2.line(image, (30, y), (190, y), 0, 2)

    grids = detect_ruled_table_grids(image, min_table_area=2_000)

    assert len(grids) == 1
    assert grids[0].rows_count >= 2
    assert grids[0].cols_count >= 2
    assert len(grids[0].cells) >= 4
    assert all(cell.is_border_detected for cell in grids[0].cells)


# borderless projection and 스팬 helpers are pure 기하 구조 기능의 정상 동작 및 제약조건을 테스트함
def test_borderless_projection_and_span_helpers_are_pure_geometry() -> None:
    image = np.full((220, 320), 255, dtype=np.uint8)
    words = [
        DummyWord("r0c0", (28, 20, 70, 40)),
        DummyWord("r0c1", (145, 20, 190, 40)),
        DummyWord("r1c0", (28, 95, 70, 115)),
        DummyWord("r1c1", (145, 95, 190, 115)),
    ]

    cells = detect_borderless_table_cells(image, words)

    assert len(cells) == 4
    assert {(cell.row_start, cell.col_start) for cell in cells} == {
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    }
    assert all(not cell.is_border_detected for cell in cells)
    assert snap_grid_boundaries([10, 12], [14, 50], tolerance=4) == [12, 50]


# 기하 구조 overlap and membership helpers 기능의 정상 동작 및 제약조건을 테스트함
def test_geometry_overlap_and_membership_helpers() -> None:
    assert intersection_area((0, 0, 20, 20), (10, 5, 30, 25)) == 150
    assert bbox_center((0, 10, 20, 30)) == (10.0, 20.0)
    assert point_in_bbox((10, 20), (0, 10, 20, 30))
    assert word_inside_any_table(
        DummyWord("inside", (4, 4, 8, 8)),
        [DummyTable((0, 0, 10, 10))],
    )


# 스팬 conflict resolution merges rectangular touched 셀 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_span_conflict_resolution_merges_rectangular_touched_cells() -> None:
    cells = [
        GridCell(
            row,
            row + 1,
            col,
            col + 1,
            (col * 50, row * 30, col * 50 + 50, row * 30 + 30),
        )
        for row in range(2)
        for col in range(2)
    ]
    words = [DummyWord("wide", (5, 4, 95, 26))]

    resolved = resolve_span_conflicts(cells, words)

    merged = next(cell for cell in resolved if cell.row_start == 0 and cell.col_start == 0)
    assert (merged.rowspan, merged.colspan) == (1, 2)
    assert len(resolved) == 3


# v2 recovers colspan from missing 테두리 not 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_v2_recovers_colspan_from_missing_border_not_text() -> None:
    image = np.full((190, 300), 255, dtype=np.uint8)
    for y in (20, 80, 150):
        cv2.line(image, (25, y), (275, y), 0, 1)
    for x in (25, 275):
        cv2.line(image, (x, 20), (x, 150), 0, 1)
    for x in (105, 195):
        cv2.line(image, (x, 80), (x, 150), 0, 1)

    grids = detect_ruled_table_grids_v2(image, min_table_area=2_000)

    assert len(grids) == 1
    assert grids[0].source == "ruled_v2"
    header = next(cell for cell in grids[0].cells if cell.row_start == 0)
    assert (header.rowspan, header.colspan) == (1, 3)
    assert len(grids[0].cells) == 4


# v2 recovers rowspan from missing horizontal 테두리 기능의 정상 동작 및 제약조건을 테스트함
def test_v2_recovers_rowspan_from_missing_horizontal_border() -> None:
    image = np.full((210, 300), 255, dtype=np.uint8)
    for x in (25, 110, 275):
        cv2.line(image, (x, 20), (x, 180), 0, 1)
    for y in (20, 180):
        cv2.line(image, (25, y), (275, y), 0, 1)
    cv2.line(image, (110, 95), (275, 95), 0, 1)

    grid = detect_ruled_table_grids_v2(image, min_table_area=2_000)[0]

    category = next(cell for cell in grid.cells if cell.row_start == 0 and cell.col_start == 0)
    assert (category.rowspan, category.colspan) == (2, 1)
    assert len(grid.cells) == 3


# v2 repairs small line gaps and detects thin coloured 격자 구조 기능의 정상 동작 및 제약조건을 테스트함
def test_v2_repairs_small_line_gaps_and_detects_thin_coloured_grid() -> None:
    image = np.full((190, 310, 3), (236, 220, 190), dtype=np.uint8)
    for x in (30, 150, 280):
        cv2.line(image, (x, 25), (x, 160), (55, 55, 55), 1)
    for y in (25, 90, 160):
        cv2.line(image, (30, y), (145, y), (55, 55, 55), 1)
        cv2.line(image, (154, y), (280, y), (55, 55, 55), 1)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    grid = detect_ruled_table_grids_v2(
        gray, min_table_area=2_000, line_merge_tolerance=4
    )[0]

    assert (grid.rows_count, grid.cols_count) == (2, 2)
    assert len(grid.cells) == 4
    assert grid.confidence >= 0.5


# word crossing 셀 목록 cannot override a visible shared 테두리 기능의 정상 동작 및 제약조건을 테스트함
def test_word_crossing_cells_cannot_override_a_visible_shared_border() -> None:
    visible = [
        GridCell(0, 0 + 1, 0, 1, (0, 0, 100, 50), borders={"right": True}),
        GridCell(0, 0 + 1, 1, 2, (100, 0, 200, 50), borders={"left": True}),
    ]
    absent = [
        GridCell(0, 1, 0, 1, (0, 0, 100, 50), borders={"right": False}),
        GridCell(0, 1, 1, 2, (100, 0, 200, 50), borders={"left": False}),
    ]
    crossing_word = [DummyWord("crossing", (20, 8, 180, 42))]

    assert len(resolve_span_conflicts(visible, crossing_word)) == 2
    merged = resolve_span_conflicts(absent, crossing_word)
    assert len(merged) == 1
    assert merged[0].colspan == 2
