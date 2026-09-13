# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: table_geometry.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/geometry/table_geometry.py
# 목적: 표 그리드, 셀 병합, 테두리 기하 좌표를 계산함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Non-destructive occupancy validation and point-based table width layout.

Rows contain anchor cells only. A virtual grid repeats each anchor across its
rectangle; uncovered coordinates remain None. Conflicting anchors are errors.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
import logging
import math

from ..core.ir import ImageIR, TableCellIR, TableIR
from ..exceptions import GeometryError

logger = logging.getLogger(__name__)
MAX_GRID_SLOTS = 1_000_000


# 격자 구조 크기 유효성 및 상태를 점검함
def _check_grid_size(rows: int, columns: int) -> None:
    # Count empty rows too: a zero-column grid still allocates one list per row.
    if rows * max(1, columns) > MAX_GRID_SLOTS or columns > MAX_GRID_SLOTS:
        raise GeometryError("Table occupancy exceeds the geometry slot budget")


# positive 작업을 수행함
def _positive(value: float, name: str) -> float:
    """Validate physical dimensions before division or allocation."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GeometryError(f"{name} must be a finite positive number")
    if not math.isfinite(value) or value <= 0:
        raise GeometryError(f"{name} must be a finite positive number")
    return float(value)


# index 작업을 수행함
def _index(value: int, name: str, minimum: int = 0) -> int:
    """Require exact integer coordinates, excluding boolean values."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GeometryError(f"{name} must be an integer >= {minimum}")
    return value


# 셀 목록 작업을 수행함
def _cells(table: TableIR) -> list[TableCellIR]:
    """Collect anchors and validate their coordinate and dimension types."""
    cells = [cell for row in table.rows for cell in row]
    for cell in cells:
        for name in ("row_index", "col_index"):
            _index(getattr(cell, name), name)
        for name in ("row_span", "col_span"):
            _index(getattr(cell, name), name, 1)
        for name in ("width_pt", "height_pt"):
            value = getattr(cell, name)
            if value is not None:
                _positive(value, name)
    return cells


# virtual 격자 구조 구조를 생성 및 조립함
def build_virtual_grid(table: TableIR) -> list[list[TableCellIR | None]]:
    """Expand spans without copying cells; reject collisions and overflow.

    Explicit track widths define the column count, otherwise anchor extents do.
    The outer row list defines the row count, including empty rows under spans.
    Holes are legal and represented by None, never synthesized as logical cells.
    """
    cells = _cells(table)
    columns = len(table.column_widths_pt) or max(
        (cell.col_index + cell.col_span for cell in cells), default=0
    )
    _check_grid_size(len(table.rows), columns)
    grid: list[list[TableCellIR | None]] = [[None] * columns for _ in table.rows]
    for row_index, anchors in enumerate(table.rows):
        for cell in anchors:
            location = f"table={table.table_id} row={cell.row_index} col={cell.col_index}"
            if cell.row_index != row_index:
                raise GeometryError(f"Anchor is in the wrong physical row: {location}")
            if cell.row_index + cell.row_span > len(grid):
                raise GeometryError(f"Row span exceeds table bounds: {location}")
            if cell.col_index + cell.col_span > columns:
                raise GeometryError(f"Column span exceeds table bounds: {location}")
            for row in range(cell.row_index, cell.row_index + cell.row_span):
                for column in range(cell.col_index, cell.col_index + cell.col_span):
                    if grid[row][column] is not None:
                        raise GeometryError(f"Overlapping cell at row={row} col={column}: {location}")
                    grid[row][column] = cell
    return grid


# 표 셀의 row_span 및 col_span 범위를 검증함
def validate_spans(table: TableIR) -> None:
    """Validate occupancy throughout a nested table tree, without mutation."""
    for current in _walk(table):
        build_virtual_grid(current)


# walk 작업을 수행함
def _walk(table: TableIR) -> Iterator[TableIR]:
    """Visit nested tables without imposing a recursion-depth limit."""
    stack = [(table, frozenset())]
    seen: set[int] = set()
    seen_cells: set[int] = set()
    while stack:
        current, ancestors = stack.pop()
        identity = id(current)
        if identity in ancestors:
            raise GeometryError(f"Cyclic nested table: {current.table_id}")
        if identity in seen:
            raise GeometryError(f"A table object has multiple parents: {current.table_id}")
        seen.add(identity)
        yield current
        descendants = ancestors | {identity}
        for row in reversed(current.rows):
            for cell in reversed(row):
                if id(cell) in seen_cells:
                    raise GeometryError("A cell object has multiple anchors or parents")
                seen_cells.add(id(cell))
                for block in reversed(cell.content):
                    if isinstance(block, TableIR):
                        stack.append((block, descendants))


# inferred tracks 작업을 수행함
def _inferred_tracks(cells: list[TableCellIR], columns: int) -> list[float]:
    """Recover track widths from connected prefix-boundary constraints.

    A merged cell fixes the distance between two column boundaries. Connected
    boundaries can determine individual tracks even without single-column cells.
    """
    edges: dict[int, list[tuple[int, float]]] = {}
    for cell in cells:
        if cell.width_pt is None:
            continue
        start, end = cell.col_index, cell.col_index + cell.col_span
        edges.setdefault(start, []).append((end, cell.width_pt))
        edges.setdefault(end, []).append((start, -cell.width_pt))
    offsets: dict[int, float] = {}
    components: dict[int, int] = {}
    for root in edges:
        if root in offsets:
            continue
        offsets[root] = 0.0
        components[root] = root
        pending = [root]
        while pending:
            start = pending.pop()
            for end, distance in edges[start]:
                offset = offsets[start] + distance
                if not math.isfinite(offset):
                    raise GeometryError("Inferred table width is not finite")
                if end in offsets:
                    if not math.isclose(offsets[end], offset, rel_tol=1e-9, abs_tol=1e-7):
                        raise GeometryError("Conflicting merged cell widths")
                    continue
                offsets[end] = offset
                components[end] = root
                pending.append(end)
    widths = [0.0] * columns
    for index in range(columns):
        if index in components and components.get(index + 1) == components[index]:
            widths[index] = _positive(offsets[index + 1] - offsets[index], "inferred column width")
    return widths


# 너비 목록 작업을 수행함
def _widths(table: TableIR, columns: int, default_width_pt: float) -> list[float]:
    """Resolve absent widths; explicit column widths are authoritative."""
    if table.column_widths_pt:
        return [_positive(width, "column width") for width in table.column_widths_pt]
    cells = _cells(table)
    widths = _inferred_tracks(cells, columns)
    for cell in sorted(cells, key=lambda item: item.col_span):
        if cell.width_pt is None:
            continue
        indices = range(cell.col_index, cell.col_index + cell.col_span)
        missing = [index for index in indices if widths[index] == 0]
        remaining = cell.width_pt - sum(widths[index] for index in indices)
        if missing and remaining > 0:
            for index in missing:
                widths[index] = remaining / len(missing)
    missing = [index for index, width in enumerate(widths) if width == 0]
    fallback = default_width_pt
    if missing and table.total_width_pt > sum(widths):
        fallback = (table.total_width_pt - sum(widths)) / len(missing)
    for index in missing:
        widths[index] = fallback
    return widths


# 표 격자 구조 및 셀 경계 좌표를 복원 및 보정함
def repair_table_geometry(table: TableIR, *, default_column_width_pt: float = 36.0) -> TableIR:
    """Repair row placement, absent rows and widths while retaining all cells.

    Coordinates and spans are authoritative. Collisions are errors, not repair
    candidates. Descendants are validated before any change is applied. Content,
    resources, borders, captions and pagination flags are never changed.
    """
    default_width = _positive(default_column_width_pt, "default column width")
    plans: list[tuple[TableIR, list[list[TableCellIR]], list[float]]] = []
    for current in _walk(table):
        cells = _cells(current)
        row_count = max(len(current.rows), max(
            (cell.row_index + cell.row_span for cell in cells), default=0
        ))
        columns = len(current.column_widths_pt) or max(
            (cell.col_index + cell.col_span for cell in cells), default=0
        )
        _check_grid_size(row_count, columns)
        rows: list[list[TableCellIR]] = [[] for _ in range(row_count)]
        for cell in cells:
            rows[cell.row_index].append(cell)
        for row in rows:
            row.sort(key=lambda cell: cell.col_index)
        candidate = replace(current, rows=rows)
        grid = build_virtual_grid(candidate)
        columns = len(grid[0]) if grid else len(current.column_widths_pt)
        if (
            isinstance(current.total_width_pt, bool)
            or not isinstance(current.total_width_pt, (int, float))
            or not math.isfinite(current.total_width_pt)
            or current.total_width_pt < 0
        ):
            raise GeometryError("Total table width must be finite and nonnegative")
        widths = _widths(candidate, columns, default_width)
        if not math.isfinite(sum(widths)):
            raise GeometryError("Total table width is not finite")
        plans.append((current, rows, widths))
    for current, rows, widths in plans:
        current.rows = rows
        current.column_widths_pt = widths
        current.total_width_pt = sum(widths)
        for row in rows:
            for cell in row:
                cell.width_pt = sum(widths[cell.col_index:cell.col_index + cell.col_span])
        logger.debug("Repaired table geometry", extra={"table_id": current.table_id})
    return table


# 표 컬럼 너비를 페이지 가용 폭에 맞게 정규화함
def normalize_column_widths(
    table: TableIR,
    available_width_pt: float,
    *,
    minimum_cell_width_pt: float = 1.0,
) -> TableIR:
    """Shrink tracks proportionally, also honoring nested cell content widths.

    Tables are never enlarged. The minimum applies to virtual column tracks.
    Infeasible widths/padding raise GeometryError. Changes are transactional
    across the tree, including proportional fitting of cell images. Existing
    display proportions are retained; missing dimensions use aspect_ratio.
    Missing track widths must first be resolved with repair. Font measurements
    and image height constraints belong to subsequent layout stages.
    """
    available = _positive(available_width_pt, "available width")
    minimum = _positive(minimum_cell_width_pt, "minimum cell width")
    list(_walk(table))
    stack = [(table, available)]
    plans: list[tuple[TableIR, list[float]]] = []
    image_plans: dict[int, tuple[ImageIR, float, float]] = {}
    while stack:
        current, container = stack.pop()
        grid = build_virtual_grid(current)
        columns = len(grid[0]) if grid else len(current.column_widths_pt)
        if columns and not current.column_widths_pt:
            raise GeometryError("Missing column widths; repair table geometry first")
        widths = [_positive(width, "column width") for width in current.column_widths_pt]
        total = sum(widths)
        if not math.isfinite(total):
            raise GeometryError("Total table width is not finite")
        ratio = min(1.0, container / total) if total else 1.0
        normalized = [width * ratio for width in widths]
        if any(width < minimum - 1e-9 for width in normalized):
            raise GeometryError(f"Minimum column width cannot fit table={current.table_id}")
        plans.append((current, normalized))
        for row in current.rows:
            for cell in row:
                cell_width = sum(normalized[cell.col_index:cell.col_index + cell.col_span])
                if len(cell.padding_pt) != 4 or any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0
                    for value in cell.padding_pt
                ):
                    raise GeometryError("Cell padding must contain four finite nonnegative points")
                inner_width = cell_width - cell.padding_pt[1] - cell.padding_pt[3]
                for block in cell.content:
                    if isinstance(block, TableIR):
                        stack.append((block, _positive(inner_width, "nested table available width")))
                    elif isinstance(block, ImageIR):
                        for dimension in (block.width_pt, block.height_pt):
                            if (isinstance(dimension, bool) or not isinstance(dimension, (int, float))
                                    or not math.isfinite(dimension) or dimension < 0):
                                raise GeometryError("Image dimensions must be finite and nonnegative")
                        if block.width_pt == 0 and block.height_pt == 0:
                            continue
                        content_width = _positive(inner_width, "image available width")
                        width, height = block.width_pt, block.height_pt
                        if width == 0 or height == 0:
                            aspect = _positive(block.aspect_ratio, "image aspect ratio")
                            width = width or height * aspect
                            height = height or width / aspect
                        width = _positive(width, "image width")
                        height = _positive(height, "image height")
                        scale = min(1.0, content_width / width)
                        fitted_width = _positive(width * scale, "fitted image width")
                        fitted_height = _positive(height * scale, "fitted image height")
                        previous = image_plans.get(id(block))
                        # Shared image objects must fit every occurrence in this tree.
                        if previous is None or fitted_width < previous[1]:
                            image_plans[id(block)] = (block, fitted_width, fitted_height)
    for current, widths in plans:
        current.column_widths_pt = widths
        current.total_width_pt = sum(widths)
        for row in current.rows:
            for cell in row:
                cell.width_pt = sum(widths[cell.col_index:cell.col_index + cell.col_span])
        logger.debug("Normalized table widths", extra={"table_id": current.table_id})
    for image, width, height in image_plans.values():
        image.width_pt = width
        image.height_pt = height
    return table
