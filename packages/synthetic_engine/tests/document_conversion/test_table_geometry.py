# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_table_geometry.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_table_geometry.py
# 목적: 테이블 그리드 분할 및 병합 셀 좌표 계산을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Behavior checks for merged occupancy and non-destructive table layout."""

import math

import pytest

from synthetic_engine.document_conversion.core.ir import ParagraphIR, TableCellIR, TableIR, TextRunIR
from synthetic_engine.document_conversion.exceptions import GeometryError
from synthetic_engine.document_conversion.geometry.table_geometry import (
    build_virtual_grid,
    normalize_column_widths,
    repair_table_geometry,
    validate_spans,
)


# merged 표(테이블) 작업을 수행함
def merged_table() -> TableIR:
    """Return the simultaneous 3-row by 2-column merge from the contract."""
    return TableIR(
        rows=[
            [TableCellIR(0, 0, row_span=3, col_span=2), TableCellIR(0, 2)],
            [TableCellIR(1, 2)],
            [TableCellIR(2, 2)],
        ],
        column_widths_pt=[100.0, 200.0, 300.0],
        total_width_pt=600.0,
    )


# combined 스팬 목록 repeat anchor identity without inventing 셀 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_combined_spans_repeat_anchor_identity_without_inventing_cells():
    table = merged_table()
    grid = build_virtual_grid(table)
    assert len(grid) == 3
    assert all(len(row) == 3 for row in grid)
    assert all(grid[row][column] is table.rows[0][0] for row in range(3) for column in range(2))
    assert len({id(cell) for row in grid for cell in row}) == 4
    assert sum(len(row) for row in table.rows) == 4


# holes remain explicit and empty 표 목록 are valid 기능의 정상 동작 및 제약조건을 테스트함
def test_holes_remain_explicit_and_empty_tables_are_valid():
    cell = TableCellIR(0, 1)
    table = TableIR(rows=[[cell]], column_widths_pt=[20.0, 20.0, 20.0])
    assert build_virtual_grid(table) == [[None, cell, None]]
    assert build_virtual_grid(TableIR()) == []


# invalid 기하 좌표 and sizes are rejected 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("field,value", [
    ("row_span", 0), ("col_span", -1), ("row_index", -1),
    ("col_index", 0.5), ("row_span", True), ("width_pt", math.inf),
])
def test_invalid_coordinates_and_sizes_are_rejected(field, value):
    cell = TableCellIR(0, 0)
    setattr(cell, field, value)
    with pytest.raises(GeometryError):
        validate_spans(TableIR(rows=[[cell]]))


# collisions and bounds are rejected with 기하 좌표 기능의 정상 동작 및 제약조건을 테스트함
def test_collisions_and_bounds_are_rejected_with_coordinates():
    table = merged_table()
    table.rows[1].append(TableCellIR(1, 1))
    with pytest.raises(GeometryError, match="Overlapping cell at row=1 col=1"):
        validate_spans(table)
    with pytest.raises(GeometryError, match="Row span exceeds"):
        validate_spans(TableIR(rows=[[TableCellIR(0, 0, row_span=2)]]))
    with pytest.raises(GeometryError, match="Column span exceeds"):
        validate_spans(TableIR(rows=[[TableCellIR(0, 0, col_span=2)]], column_widths_pt=[10.0]))


# wide 표(테이블) shrinks proportionally and updates merged 너비 기능의 정상 동작 및 제약조건을 테스트함
def test_wide_table_shrinks_proportionally_and_updates_merged_width():
    table = merged_table()
    normalize_column_widths(table, 300)
    assert table.column_widths_pt == pytest.approx([50, 100, 150])
    assert table.rows[0][0].width_pt == pytest.approx(150)
    assert table.total_width_pt == pytest.approx(300)
    normalize_column_widths(table, 900)
    assert table.total_width_pt == pytest.approx(300)
    assert build_virtual_grid(table)[2][1] is table.rows[0][0]


# invalid container 너비 is rejected 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("available", [0, -1, math.inf, math.nan, True])
def test_invalid_container_width_is_rejected(available):
    with pytest.raises(GeometryError):
        normalize_column_widths(merged_table(), available)


# infeasible minimum keeps entire input unchanged 기능의 정상 동작 및 제약조건을 테스트함
def test_infeasible_minimum_keeps_entire_input_unchanged():
    table = merged_table()
    with pytest.raises(GeometryError, match="Minimum column width"):
        normalize_column_widths(table, 3, minimum_cell_width_pt=1)
    assert table.column_widths_pt == [100, 200, 300]
    assert table.rows[0][0].width_pt is None


# 보정 reorders anchors and retains missing 행 slots 기능의 정상 동작 및 제약조건을 테스트함
def test_repair_reorders_anchors_and_retains_missing_row_slots():
    first = TableCellIR(0, 0, row_span=3, col_span=2, width_pt=120)
    last = TableCellIR(2, 2, width_pt=30)
    table = TableIR(rows=[[last, first]])
    repair_table_geometry(table)
    assert table.rows == [[first], [], [last]]
    assert table.column_widths_pt == pytest.approx([60, 60, 30])
    assert table.total_width_pt == pytest.approx(150)
    assert build_virtual_grid(table)[1][0] is first


# 보정 rejects collision instead of discarding data 기능의 정상 동작 및 제약조건을 테스트함
def test_repair_rejects_collision_instead_of_discarding_data():
    left, right = TableCellIR(0, 0), TableCellIR(0, 0)
    table = TableIR(rows=[[left, right]])
    with pytest.raises(GeometryError, match="Overlapping"):
        repair_table_geometry(table)
    assert table.rows == [[left, right]]
    assert table.column_widths_pt == []


# nested depth four uses parent content 너비 and keeps content 기능의 정상 동작 및 제약조건을 테스트함
def test_nested_depth_four_uses_parent_content_width_and_keeps_content():
    paragraph = ParagraphIR(inlines=[TextRunIR(text=" NBSP\u00a0\u3000\t ")])
    nested = TableIR(rows=[[TableCellIR(0, 0, content=[paragraph])]], column_widths_pt=[600.0])
    levels = [nested]
    for depth in range(3, -1, -1):
        nested = TableIR(
            depth=depth,
            rows=[[TableCellIR(0, 0, content=[nested], padding_pt=(0, 5, 0, 5))]],
            column_widths_pt=[600.0], repeat_header_rows=1, cant_split=True,
        )
        levels.append(nested)
    normalize_column_widths(nested, 300)
    assert [item.total_width_pt for item in reversed(levels)] == [300, 290, 280, 270, 260]
    assert levels[0].rows[0][0].content[0] is paragraph
    assert nested.repeat_header_rows == 1
    assert nested.cant_split is True


# nested failure does not partially resize parent 기능의 정상 동작 및 제약조건을 테스트함
def test_nested_failure_does_not_partially_resize_parent():
    child = TableIR(rows=[[TableCellIR(0, 0)]], column_widths_pt=[100.0])
    table = TableIR(rows=[[TableCellIR(0, 0, content=[child], padding_pt=(0, 30, 0, 30))]], column_widths_pt=[100.0])
    with pytest.raises(GeometryError, match="nested table available width"):
        normalize_column_widths(table, 50)
    assert table.column_widths_pt == [100]
    assert child.column_widths_pt == [100]


# cycles are explicit errors not recursion failure 기능의 정상 동작 및 제약조건을 테스트함
def test_cycles_are_explicit_errors_not_recursion_failure():
    table = TableIR(rows=[[TableCellIR(0, 0)]], column_widths_pt=[10.0])
    table.rows[0][0].content.append(table)
    with pytest.raises(GeometryError, match="Cyclic"):
        repair_table_geometry(table)


# nested invalid 스팬 is checked by public validator 기능의 정상 동작 및 제약조건을 테스트함
def test_nested_invalid_span_is_checked_by_public_validator():
    child = TableIR(rows=[[TableCellIR(0, 0, row_span=2)]])
    table = TableIR(rows=[[TableCellIR(0, 0, content=[child])]])
    with pytest.raises(GeometryError, match="Row span exceeds"):
        validate_spans(table)


# 보정 overflowing 너비 목록 does not mutate 표(테이블) 기능의 정상 동작 및 제약조건을 테스트함
def test_repair_overflowing_widths_does_not_mutate_table():
    table = TableIR(rows=[[TableCellIR(0, 0), TableCellIR(0, 1)]], column_widths_pt=[1e308, 1e308])
    with pytest.raises(GeometryError, match="not finite"):
        repair_table_geometry(table)
    assert table.total_width_pt == 0
    assert table.rows[0][0].width_pt is None


# 기하 구조 preserves borders fill 이미지 and pagination 기능의 정상 동작 및 제약조건을 테스트함
def test_geometry_preserves_borders_fill_image_and_pagination():
    from synthetic_engine.document_conversion.core.enums import BorderStyle
    from synthetic_engine.document_conversion.core.ir import BorderIR, ImageIR

    image = ImageIR(image_bytes=b"image", mime_type="image/png", format="png", width_pt=20, height_pt=10, aspect_ratio=2)
    borders = {key: BorderIR(style=style, width_pt=1, color_hex="123456") for key, style in (
        ("top", BorderStyle.NONE), ("slash", BorderStyle.SOLID), ("backslash", BorderStyle.DOUBLE),
    )}
    cell = TableCellIR(0, 0, borders=borders, bg_color_hex="AABBCC", content=[image])
    table = TableIR(rows=[[cell]], column_widths_pt=[100], repeat_header_rows=1, cant_split=True)
    repair_table_geometry(table)
    normalize_column_widths(table, 50)
    assert cell.borders is borders
    assert cell.bg_color_hex == "AABBCC"
    assert cell.content[0] is image
    assert image.width_pt == 20 and image.height_pt == 10
    assert table.repeat_header_rows == 1 and table.cant_split
