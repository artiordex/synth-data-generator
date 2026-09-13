# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_xlsx_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_xlsx_refinement.py
# 목적: 엑셀(XLSX) 파서 및 렌더러 정합성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Spreadsheet rendering retains native cell styles and merge anchors."""
from openpyxl import load_workbook
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR, SectionIR, TableIR, TableCellIR, ParagraphIR, TextRunIR,
)
from synthetic_engine.document_conversion.renderers.xlsx_renderer import XlsxRenderer


# 엑셀(XLSX) native 스타일 목록 and literal formula like 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_xlsx_native_styles_and_literal_formula_like_text(tmp_path):
    source = DocumentIR(sections=[SectionIR(elements=[TableIR(rows=[[
        TableCellIR(0, 0, col_span=2, bg_color_hex='FFCC00', height_pt=24,
                    content=[ParagraphIR(inlines=[TextRunIR('=not a formula', bold=True, size_pt=14)])])
    ]], column_widths_pt=[72, 72], total_width_pt=144)])])
    path = tmp_path / 'styled.xlsx'
    XlsxRenderer().render(source, path)
    workbook = load_workbook(path)
    try:
        sheet = workbook['Table 1']
        assert sheet['A1'].value == '=not a formula'
        assert sheet['A1'].data_type == 's'
        assert sheet['A1'].font.bold and sheet['A1'].font.sz == 14
        assert sheet['A1'].fill.fgColor.rgb.endswith('FFCC00')
        assert str(next(iter(sheet.merged_cells.ranges))) == 'A1:B1'
        assert sheet.row_dimensions[1].height == 24
        assert source.warnings[-1].code == 'XLSX_GRID_DEGRADATION'
    finally:
        workbook.close()
