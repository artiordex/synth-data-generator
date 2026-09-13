# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_quality_preservation.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_ocr_quality_preservation.py
# 목적: OCR 품질 지표 보존 및 오류 제어를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.ocr_quality_report import PageQualityFixture, build_page_quality_record
from synthetic_engine.document_conversion.core.enums import ImagePlacement
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR,
    ImageIR,
    ParagraphIR,
    SectionIR,
    TableCellIR,
    TableIR,
    TextRunIR,
)
from synthetic_engine.document_conversion.geometry.table_geometry import build_virtual_grid


# fixture document preserves 이미지 relationships merges and 너비 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_fixture_document_preserves_image_relationships_merges_and_widths() -> None:
    logo = ImageIR(
        image_bytes=b"fixture-logo",
        mime_type="image/png",
        format="PNG",
        width_pt=36,
        height_pt=18,
        original_width_px=200,
        original_height_px=100,
        placement=ImagePlacement.INLINE,
    )
    seal = ImageIR(
        image_bytes=b"fixture-seal",
        mime_type="image/png",
        format="PNG",
        width_pt=30,
        height_pt=30,
        original_width_px=120,
        original_height_px=120,
        placement=ImagePlacement.IN_FRONT,
    )
    header = TableCellIR(
        0,
        0,
        col_span=3,
        width_pt=288,
        content=[ParagraphIR([TextRunIR("합성 OCR 품질 측정표")]), logo],
    )
    value = TableCellIR(1, 0, row_span=2, width_pt=72, content=[ParagraphIR([TextRunIR("2026-09-11")])])
    amount = TableCellIR(1, 1, width_pt=120, content=[ParagraphIR([TextRunIR("10,000원")])])
    stamp = TableCellIR(1, 2, width_pt=96, content=[seal])
    note = TableCellIR(2, 1, col_span=2, width_pt=216, content=[ParagraphIR([TextRunIR("□ 미선택 / ■ 선택")])])
    table = TableIR(
        rows=[[header], [value, amount, stamp], [note]],
        column_widths_pt=[72, 120, 96],
        total_width_pt=288,
    )

    document = DocumentIR(sections=[SectionIR(elements=[table])])
    grid = build_virtual_grid(table)

    assert logo.resource_id is not None
    assert seal.resource_id is not None
    assert logo.resource_id != seal.resource_id
    assert document.resources.get(logo.resource_id) == b"fixture-logo"
    assert document.resources.get(seal.resource_id) == b"fixture-seal"
    assert grid[0][0] is grid[0][1] is grid[0][2] is header
    assert grid[1][0] is grid[2][0] is value
    assert grid[2][1] is grid[2][2] is note
    assert table.column_widths_pt == [72, 120, 96]
    assert [logo.width_pt, logo.height_pt, seal.width_pt, seal.height_pt] == [36, 18, 30, 30]
    assert logo.aspect_ratio == 2
    assert seal.aspect_ratio == 1


# 품질 분석 리포트 detects relationship 병합 and 너비 손실 기능의 정상 동작 및 제약조건을 테스트함
def test_quality_report_detects_relationship_merge_and_width_loss() -> None:
    record = build_page_quality_record(
        PageQualityFixture(
            page_no=5,
            reference_text="이미지와 병합 셀 보존",
            recognized_text="이미지와 병합 셀 보존",
            confidence=0.93,
            processing_time_ms=95.0,
            expected_cell_count=6,
            recognized_cell_count=6,
            expected_image_count=2,
            recognized_image_count=1,
            expected_merged_ranges=("A1:C1", "A2:A3", "B3:C3"),
            recognized_merged_ranges=("A1:C1", "B3:C3"),
            expected_column_widths_pt=(72.0, 120.0, 96.0),
            recognized_column_widths_pt=(72.0, 96.0, 96.0),
            expected_relationship_ids=("rIdLogo", "rIdSeal"),
            recognized_relationship_ids=("rIdLogo",),
        )
    )

    assert record["text_fidelity"] == 1.0
    assert record["cell_count_fidelity"] == 1.0
    assert record["image_count_fidelity"] == 0.5
    assert record["merge_fidelity"] == 2 / 3
    assert record["width_fidelity"] < 0.95
    assert record["relationship_fidelity"] == 0.5
    assert record["meets_visual_target_95"] is False
    assert "visual_fidelity_below_95" in record["review_reasons"]
