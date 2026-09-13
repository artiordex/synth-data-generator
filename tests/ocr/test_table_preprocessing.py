# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_table_preprocessing.py
# 경로: tests/ocr/test_table_preprocessing.py
# 목적: 표 영역 감지 및 테이블 셀 전처리 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import cv2
import numpy as np
import pytest

from ocr.pipeline.models import BoundingBox
from ocr.preprocessing.table import detect_table_lines, detect_tables


# 격자 구조 작업을 수행함
def _grid(*, thickness=1):
    image = np.full((180, 220), 255, dtype=np.uint8)
    for x in (20, 80, 140, 200):
        cv2.line(image, (x, 20), (x, 140), 0, thickness)
    for y in (20, 60, 100, 140):
        cv2.line(image, (20, y), (200, y), 0, thickness)
    return image


# detects 격자 구조 기하 구조 in existing 스키마 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("thickness", [1, 3])
def test_detects_grid_geometry_in_existing_schema(thickness):
    tables = detect_tables(_grid(thickness=thickness))

    assert len(tables) == 1
    table = tables[0]
    assert table.bbox == BoundingBox(20, 20, 180, 120)
    assert (table.rows, table.columns) == (3, 3)
    assert len(table.cells) == 9
    assert table.cells[4].bbox == BoundingBox(80, 60, 60, 40)
    assert [(cell.row, cell.column) for cell in table.cells] == [
        (row, column) for row in range(3) for column in range(3)
    ]
    assert all(cell.row_span == cell.col_span == 1 for cell in table.cells)
    assert all(cell.words == () for cell in table.cells)
    assert 0.9 <= table.confidence <= 0.95


# detection preserves OCR 인식 pixels and uses independent masks 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("color", [False, True])
def test_detection_preserves_ocr_pixels_and_uses_independent_masks(color):
    image = _grid()
    cv2.putText(image, "OCR", (27, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)
    if color:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    original = image.copy()
    image.flags.writeable = False

    horizontal, vertical = detect_table_lines(image)
    assert len(detect_tables(image)) == 1
    assert horizontal.shape == vertical.shape == image.shape[:2]
    assert horizontal.dtype == vertical.dtype == np.uint8
    assert horizontal[20, 45] == 255 and vertical[20, 45] == 0
    assert vertical[40, 20] == 255 and horizontal[40, 20] == 0
    assert not np.shares_memory(horizontal, vertical)
    assert not np.shares_memory(horizontal, image)
    assert not np.shares_memory(vertical, image)
    horizontal[:] = 0
    vertical[:] = 0
    np.testing.assert_array_equal(image, original)


# missing divider omits uncertain slots without inventing 스팬 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_divider_omits_uncertain_slots_without_inventing_spans():
    complete = detect_tables(_grid())[0]
    image = _grid()
    image[21:60, 80] = 255

    table = detect_tables(image)[0]

    assert (table.rows, table.columns) == (3, 3)
    assert len(table.cells) == 7
    assert (0, 0) not in {(cell.row, cell.column) for cell in table.cells}
    assert (0, 1) not in {(cell.row, cell.column) for cell in table.cells}
    assert all(cell.row_span == cell.col_span == 1 for cell in table.cells)
    assert 0 < table.confidence < complete.confidence


# separate 표 목록 keep local 행 목록 and 페이지 기하 좌표 기능의 정상 동작 및 제약조건을 테스트함
def test_separate_tables_keep_local_rows_and_page_coordinates():
    image = np.full((400, 500), 255, dtype=np.uint8)
    image[:180, :220] = _grid()
    image[200:380, 250:470] = _grid()

    tables = detect_tables(image)

    assert len(tables) == 2
    assert tables[1].bbox == BoundingBox(270, 220, 180, 120)
    assert tables[1].cells[0].bbox == BoundingBox(270, 220, 60, 40)
    assert tables[1].cells[0].row == tables[1].cells[0].column == 0


# non grids do not produce 표 목록 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("kind", ["blank", "text", "rules", "frame", "tiny"])
def test_non_grids_do_not_produce_tables(kind):
    image = np.full((180, 220), 255, dtype=np.uint8)
    if kind == "text":
        cv2.putText(image, "OCR text", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 1)
    elif kind == "rules":
        for y in (20, 60, 100):
            cv2.line(image, (20, y), (200, y), 0, 1)
    elif kind == "frame":
        cv2.rectangle(image, (20, 20), (200, 140), 0, 1)
    elif kind == "tiny":
        image = np.full((1, 1), 255, dtype=np.uint8)

    assert detect_tables(image) == ()


# rejects unsupported input 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("image", [
    np.empty((0, 10), dtype=np.uint8),
    np.zeros((20, 20), dtype=np.float32),
    np.zeros((20, 20, 4), dtype=np.uint8),
    np.zeros((20,), dtype=np.uint8),
])
def test_rejects_unsupported_input(image):
    with pytest.raises(ValueError):
        detect_tables(image)
