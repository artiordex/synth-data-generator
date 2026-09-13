# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_geometry_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_geometry_refinement.py
# 목적: 기하 좌표 계산 및 공간 변환 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Regression coverage for nested merged-table geometry refinements."""

import pytest

from synthetic_engine.document_conversion.core.ir import ImageIR, TableCellIR, TableIR
from synthetic_engine.document_conversion.exceptions import GeometryError
from synthetic_engine.document_conversion.geometry.table_geometry import (
    MAX_GRID_SLOTS, build_virtual_grid, normalize_column_widths,
    repair_table_geometry,
)


# constrained 표(테이블) 작업을 수행함
def constrained_table():
    return TableIR(rows=[
        [TableCellIR(0, 0, col_span=2, width_pt=100)],
        [TableCellIR(1, 1, col_span=2, width_pt=120)],
        [TableCellIR(2, 0, col_span=3, width_pt=150)],
    ])


# overlapping merged 너비 evidence recovers unique tracks 기능의 정상 동작 및 제약조건을 테스트함
def test_overlapping_merged_width_evidence_recovers_unique_tracks():
    table = constrained_table()
    anchors = [row[0] for row in table.rows]
    repair_table_geometry(table)
    assert table.column_widths_pt == pytest.approx([30, 70, 50])
    assert [cell.width_pt for cell in anchors] == pytest.approx([100, 120, 150])
    assert table.total_width_pt == pytest.approx(150)
    grid = build_virtual_grid(table)
    assert grid[0][2] is None and grid[1][0] is None
    assert grid[2] == [anchors[2]] * 3
    repair_table_geometry(table)
    assert table.column_widths_pt == pytest.approx([30, 70, 50])


# nested merged content 너비 and padding are used 기능의 정상 동작 및 제약조건을 테스트함
def test_nested_merged_content_width_and_padding_are_used():
    child = constrained_table()
    anchor = TableCellIR(0, 0, col_span=2, row_span=2, width_pt=200,
                         padding_pt=(0, 10, 0, 20), content=[child])
    parent = TableIR(rows=[[anchor]])
    repair_table_geometry(parent)
    normalize_column_widths(parent, 100)
    assert parent.rows == [[anchor], []]
    assert anchor.width_pt == pytest.approx(100)
    assert child.total_width_pt == pytest.approx(70)
    assert child.column_widths_pt == pytest.approx([14, 98 / 3, 70 / 3])
    assert build_virtual_grid(parent)[1] == [anchor, anchor]
    assert anchor.content[0] is child


# conflicting nested 너비 evidence is transactional 기능의 정상 동작 및 제약조건을 테스트함
def test_conflicting_nested_width_evidence_is_transactional():
    child = TableIR(rows=[
        [TableCellIR(0, 0, width_pt=30), TableCellIR(0, 1, width_pt=40)],
        [TableCellIR(1, 0, col_span=2, width_pt=100)],
    ])
    anchor = TableCellIR(2, 0, content=[child])
    parent = TableIR(rows=[[anchor]])
    original_rows = parent.rows
    with pytest.raises(GeometryError, match="Conflicting merged"):
        repair_table_geometry(parent)
    assert parent.rows is original_rows
    assert parent.column_widths_pt == [] and anchor.width_pt is None
    assert child.column_widths_pt == []
    assert child.rows[1][0].width_pt == 100


# explicit tracks remain authoritative over 셀 hints 기능의 정상 동작 및 제약조건을 테스트함
def test_explicit_tracks_remain_authoritative_over_cell_hints():
    table = constrained_table()
    table.column_widths_pt = [20, 30, 40]
    repair_table_geometry(table)
    assert table.column_widths_pt == [20, 30, 40]
    assert [row[0].width_pt for row in table.rows] == [50, 70, 90]


# 보정 rejects huge occupancy before expansion 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("field", ["row_index", "col_index", "row_span", "col_span"])
def test_repair_rejects_huge_occupancy_before_expansion(field):
    cell = TableCellIR(0, 0)
    setattr(cell, field, MAX_GRID_SLOTS + 1)
    table = TableIR(rows=[[cell]])
    with pytest.raises(GeometryError, match="slot budget"):
        repair_table_geometry(table)
    assert table.rows == [[cell]] and table.column_widths_pt == []


# 격자 구조 rejects huge 컬럼 extent 기능의 정상 동작 및 제약조건을 테스트함
def test_grid_rejects_huge_column_extent():
    table = TableIR(rows=[[TableCellIR(0, MAX_GRID_SLOTS)]])
    with pytest.raises(GeometryError, match="slot budget"):
        build_virtual_grid(table)


# shared 셀 between nested 표 목록 is rejected before mutation 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("operation", [repair_table_geometry, lambda table: normalize_column_widths(table, 50)])
def test_shared_cell_between_nested_tables_is_rejected_before_mutation(operation):
    shared = TableCellIR(0, 0)
    first = TableIR(rows=[[shared]], column_widths_pt=[100])
    second = TableIR(rows=[[shared]], column_widths_pt=[200])
    parent = TableIR(rows=[[TableCellIR(0, 0, content=[first, second])]], column_widths_pt=[300])
    with pytest.raises(GeometryError, match="cell object has multiple"):
        operation(parent)
    assert parent.column_widths_pt == [300]
    assert first.column_widths_pt == [100] and second.column_widths_pt == [200]
    assert shared.width_pt is None


# underdetermined single 병합 keeps equal 너비 폴백 기능의 정상 동작 및 제약조건을 테스트함
def test_underdetermined_single_merge_keeps_equal_width_fallback():
    table = TableIR(rows=[[TableCellIR(0, 0, col_span=3, width_pt=120)]])
    repair_table_geometry(table)
    assert table.column_widths_pt == pytest.approx([40, 40, 40])


# nonpositive inferred track rejects without mutation 기능의 정상 동작 및 제약조건을 테스트함
def test_nonpositive_inferred_track_rejects_without_mutation():
    table = TableIR(rows=[
        [TableCellIR(0, 0, width_pt=100)],
        [TableCellIR(1, 0, col_span=2, width_pt=80)],
    ])
    with pytest.raises(GeometryError, match="inferred column width"):
        repair_table_geometry(table)
    assert table.column_widths_pt == []


# 이미지 객체 또는 요소를 생성함
def make_image(width=200, height=100):
    return ImageIR(image_bytes=b"original", mime_type="image/png", format="png",
                   width_pt=width, height_pt=height, aspect_ratio=2)


# default zero 표(테이블) 너비 repairs then normalizes 기능의 정상 동작 및 제약조건을 테스트함
def test_default_zero_table_width_repairs_then_normalizes():
    table = TableIR(rows=[[TableCellIR(0, 0)]])
    assert table.total_width_pt == 0
    repair_table_geometry(table)
    normalize_column_widths(table, 20)
    assert table.column_widths_pt == [20]
    empty = TableIR()
    repair_table_geometry(empty)
    normalize_column_widths(empty, 20)
    assert empty.total_width_pt == 0


# 이미지 fits nested merged 셀 and preserves payload 기능의 정상 동작 및 제약조건을 테스트함
def test_image_fits_nested_merged_cell_and_preserves_payload():
    image = make_image()
    child = TableIR(rows=[[TableCellIR(0, 0, col_span=2, content=[image],
                                     padding_pt=(0, 5, 0, 15))]], column_widths_pt=[100, 100])
    parent = TableIR(rows=[[TableCellIR(0, 0, content=[child],
                                      padding_pt=(0, 10, 0, 10))]], column_widths_pt=[300])
    normalize_column_widths(parent, 120)
    assert (image.width_pt, image.height_pt) == pytest.approx((80, 40))
    assert image.aspect_ratio == 2 and image.image_bytes == b"original"
    normalize_column_widths(parent, 120)
    assert (image.width_pt, image.height_pt) == pytest.approx((80, 40))


# 이미지 that fits is not enlarged or reproportioned 기능의 정상 동작 및 제약조건을 테스트함
def test_image_that_fits_is_not_enlarged_or_reproportioned():
    image = make_image(20, 15)
    table = TableIR(rows=[[TableCellIR(0, 0, content=[image])]], column_widths_pt=[100])
    normalize_column_widths(table, 50)
    assert (image.width_pt, image.height_pt) == (20, 15)
    assert image.aspect_ratio == 2


# missing 이미지 dimension uses stored aspect 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("width,height", [(200, 0), (0, 100)])
def test_missing_image_dimension_uses_stored_aspect(width, height):
    image = make_image(width, height)
    table = TableIR(rows=[[TableCellIR(0, 0, content=[image])]], column_widths_pt=[100])
    normalize_column_widths(table, 80)
    assert (image.width_pt, image.height_pt) == pytest.approx((80, 40))


# 이미지 resize rolls back when nested validation fails 기능의 정상 동작 및 제약조건을 테스트함
def test_image_resize_rolls_back_when_nested_validation_fails():
    image = make_image()
    child = TableIR(rows=[[TableCellIR(0, 0)]])
    table = TableIR(rows=[[TableCellIR(0, 0, content=[image, child])]], column_widths_pt=[200])
    with pytest.raises(GeometryError, match="Missing column widths"):
        normalize_column_widths(table, 50)
    assert table.column_widths_pt == [200]
    assert (image.width_pt, image.height_pt) == (200, 100)


# 이미지 cannot fit when padding consumes 셀 기능의 정상 동작 및 제약조건을 테스트함
def test_image_cannot_fit_when_padding_consumes_cell():
    image = make_image()
    table = TableIR(rows=[[TableCellIR(0, 0, content=[image], padding_pt=(0, 30, 0, 30))]],
                    column_widths_pt=[100])
    with pytest.raises(GeometryError, match="image available width"):
        normalize_column_widths(table, 50)
    assert table.column_widths_pt == [100] and image.width_pt == 200


# shared 이미지 fits smallest 셀 regardless of order 기능의 정상 동작 및 제약조건을 테스트함
def test_shared_image_fits_smallest_cell_regardless_of_order():
    image = make_image()
    table = TableIR(rows=[[TableCellIR(0, 0, content=[image]),
                           TableCellIR(0, 1, content=[image])]], column_widths_pt=[40, 100])
    normalize_column_widths(table, 140)
    assert (image.width_pt, image.height_pt) == pytest.approx((40, 20))
