# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ir.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_ir.py
# 목적: IR 노드 계층 트리 조작 및 유효성 검증을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""IR invariants for exact text, nested objects and shared resources."""
from dataclasses import asdict
from uuid import UUID

import pytest

from synthetic_engine.document_conversion.core.enums import (
    BorderStyle, ImagePlacement, ParagraphAlign, StrikeStyle, SupportStatus,
    UnderlineStyle,
)
from synthetic_engine.document_conversion.core.ir import (
    BorderIR, BoundingBoxIR, DocumentIR, DrawingIR, FieldIR, HeaderFooterIR,
    HyperlinkIR, ImageIR, LineBreakIR, ParagraphIR, SectionIR, TableCellIR,
    TableIR, TextRunIR, UnsupportedRecordIR, TabIR,
)
from synthetic_engine.document_conversion.core.source_ref import SourceRef


# unicode whitespace and inline controls remain distinct 기능의 정상 동작 및 제약조건을 테스트함
def test_unicode_whitespace_and_inline_controls_remain_distinct() -> None:
    text = "  \u00a0\u3000\t\u2460\u2461\u2462\u2469\u321c\u3260\u24d0\u2474\u25aa\u25b6\u203b\u00b1\u2264\u2265\u98df\u85e5\u8655 H\u2082O m\u00b2 \ucc38\uace0\u00b9)\n  "
    run = TextRunIR(text, bold=True, italic=True, underline=UnderlineStyle.DOUBLE,
                    strike=StrikeStyle.DOUBLE, color_hex="123456", bg_color_hex="FFFF00",
                    letter_spacing_pt=-0.2, scale_percent=85, superscript=True)
    paragraph = ParagraphIR(inlines=[run, TabIR(24), LineBreakIR("soft"),
                                    TextRunIR("2", subscript=True), LineBreakIR("hard")],
                            align=ParagraphAlign.DISTRIBUTE)
    next_paragraph = ParagraphIR([TextRunIR("")])
    doc = DocumentIR(sections=[SectionIR(elements=[paragraph, next_paragraph])])
    assert run.text.encode("utf-8") == text.encode("utf-8")
    assert asdict(run)["text"] == text
    assert run.underline is UnderlineStyle.DOUBLE
    assert run.strike is StrikeStyle.DOUBLE
    assert run.superscript and paragraph.inlines[3].subscript
    assert [type(item) for item in paragraph.inlines] == [TextRunIR, TabIR, LineBreakIR, TextRunIR, LineBreakIR]
    assert paragraph.inlines[2].kind == "soft"
    assert paragraph.inlines[4].kind == "hard"
    assert list(doc.iter_blocks()) == [paragraph, next_paragraph]


# deep nesting retains provenance and unknown records 기능의 정상 동작 및 제약조건을 테스트함
def test_deep_nesting_retains_provenance_and_unknown_records() -> None:
    ref = SourceRef("hwp", section_no=2, page_no=4, record_offset=256,
                    table_id="source-table-7", row_index=3, col_index=2)
    unknown = UnsupportedRecordIR(777, 9, b"\x00\xff\x01", source_ref=ref)
    innermost = TableIR(rows=[[TableCellIR(0, 0, content=[unknown])]])
    root = innermost
    for depth in range(1100):
        root = TableIR(depth=depth, rows=[[TableCellIR(0, 0, content=[root])]])
    doc = DocumentIR(sections=[SectionIR(elements=[root])])
    blocks = list(doc.iter_blocks())
    assert sum(isinstance(block, TableIR) for block in blocks) == 1101
    assert blocks[-1] is unknown
    assert unknown.raw_bytes == b"\x00\xff\x01"
    assert unknown.support_status is SupportStatus.UNSUPPORTED
    assert unknown.source_ref.record_offset == 256
    assert unknown.source_ref.col_index == 2


# 이미지 목록 share bytes without losing placements 기능의 정상 동작 및 제약조건을 테스트함
def test_images_share_bytes_without_losing_placements() -> None:
    payload = bytes(bytearray(b"original-image-payload"))
    repeated = bytes(bytearray(payload))
    assert payload is not repeated
    first = ImageIR(payload, "image/png", "PNG", 100, 50, aspect_ratio=2)
    second = ImageIR(repeated, "image/png", "PNG", 40, 20, aspect_ratio=2,
                     placement=ImagePlacement.BEHIND)
    third = ImageIR(bytes(bytearray(payload)), "image/png", "PNG", 10, 5,
                    aspect_ratio=2, placement=ImagePlacement.IN_FRONT)
    doc = DocumentIR(sections=[SectionIR(
        elements=[TableIR(rows=[[TableCellIR(0, 0, content=[first])]])],
        header=HeaderFooterIR([second]), footer=HeaderFooterIR([third]),
    )])
    assert first.image_bytes is second.image_bytes is third.image_bytes
    assert first.resource_id == second.resource_id == third.resource_id
    assert doc.resources.get(first.resource_id) == payload
    assert sum(isinstance(block, ImageIR) for block in doc.iter_blocks()) == 3
    assert [first.width_pt, second.width_pt, third.width_pt] == [100, 40, 10]


# independent defaults and unique 표(테이블) ids 기능의 정상 동작 및 제약조건을 테스트함
def test_independent_defaults_and_unique_table_ids() -> None:
    first, second = TableIR(), TableIR()
    assert UUID(first.table_id).version == 4
    assert first.table_id != second.table_id
    first.rows.append([TableCellIR(0, 0)])
    assert second.rows == []
    first.rows[0][0].borders["slash"] = BorderIR(BorderStyle.SOLID, 0.5, "000000")
    assert TableCellIR(0, 0).borders == {}


# 이미지 ratio uses original 기하 구조 when available 기능의 정상 동작 및 제약조건을 테스트함
def test_image_ratio_uses_original_geometry_when_available() -> None:
    original = ImageIR(b"payload", "image/png", "PNG", 100, 100,
                       original_width_px=400, original_height_px=200)
    display = ImageIR(b"payload", "image/png", "PNG", 60, 20)
    explicit = ImageIR(b"payload", "image/png", "PNG", 100, 100, aspect_ratio=3)
    assert original.aspect_ratio == 2
    assert display.aspect_ratio == 3
    assert explicit.aspect_ratio == 3
    with pytest.raises(ValueError, match="aspect ratio"):
        ImageIR(b"payload", "image/png", "PNG", 0, 0)


# dynamic fields links and drawing 텍스트 are not flattened 기능의 정상 동작 및 제약조건을 테스트함
def test_dynamic_fields_links_and_drawing_text_are_not_flattened() -> None:
    page = FieldIR("PAGE_NUMBER", cached_text="7")
    link = HyperlinkIR("https://example.invalid", [TextRunIR(" link ")])
    footer_paragraph = ParagraphIR([TextRunIR("- "), page, TextRunIR(" -")])
    drawing_paragraph = ParagraphIR([link])
    drawing = DrawingIR("text_box", text_content=[drawing_paragraph])
    doc = DocumentIR(sections=[SectionIR(elements=[drawing], footer=HeaderFooterIR([footer_paragraph]))])
    assert list(doc.iter_blocks()) == [drawing, drawing_paragraph, footer_paragraph]
    assert footer_paragraph.inlines[1] is page
    assert page.field_type == "PAGE_NUMBER"
    assert link.inlines[0].text == " link "


# cycle detection does not reject reused 문서 블록 occurrences 기능의 정상 동작 및 제약조건을 테스트함
def test_cycle_detection_does_not_reject_reused_block_occurrences() -> None:
    paragraph = ParagraphIR([TextRunIR("reused")])
    doc = DocumentIR(sections=[SectionIR(elements=[paragraph, paragraph])])
    assert len(list(doc.iter_blocks())) == 2
    table = TableIR(rows=[[TableCellIR(0, 0)]])
    table.rows[0][0].content.append(table)
    with pytest.raises(ValueError, match="cycle"):
        DocumentIR(sections=[SectionIR(elements=[table])])


# invalid inference scores are rejected 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_inference_scores_are_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="Confidence"):
        TableIR(table_confidence=confidence)
    with pytest.raises(ValueError, match="Confidence"):
        TableCellIR(0, 0, cell_confidence=confidence)


# unknown 인식 신뢰도 differs from inferred 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_unknown_confidence_differs_from_inferred_confidence() -> None:
    assert TableIR().table_confidence is None
    inferred = TableIR(table_confidence=0.71, support_status=SupportStatus.INFERRED)
    assert inferred.support_status is SupportStatus.INFERRED
    assert inferred.table_confidence == 0.71


# bounding box 기하 구조 validation 기능의 정상 동작 및 제약조건을 테스트함
def test_bounding_box_geometry_validation() -> None:
    box = BoundingBoxIR(10, 20, 110, 70, 4)
    assert (box.width_pt, box.height_pt) == (100, 50)
    with pytest.raises(ValueError, match="ordered"):
        BoundingBoxIR(5, 0, 1, 1, 1)
    with pytest.raises(ValueError, match="finite"):
        BoundingBoxIR(0, 0, float("nan"), 1, 1)
    with pytest.raises(ValueError, match="one-based"):
        BoundingBoxIR(0, 0, 1, 1, 0)


# source indices reject invalid values 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("name", ["page_no", "section_no", "record_offset", "row_index", "col_index"])
@pytest.mark.parametrize("value", [True, False, 1.5, -1, "1"])
def test_source_indices_reject_invalid_values(name: str, value: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        SourceRef("pdf", **{name: value})


# source 좌표 bases are preserved 기능의 정상 동작 및 제약조건을 테스트함
def test_source_coordinate_bases_are_preserved() -> None:
    source = SourceRef("hwp", page_no=1, section_no=1, row_index=0, col_index=0, record_offset=0)
    assert source.record_offset == 0
    for name in ("page_no", "section_no"):
        with pytest.raises(ValueError, match="integer"):
            SourceRef("hwp", **{name: 0})


# bounding box 페이지 requires integer 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("page", [True, False, 1.5, "1"])
def test_bounding_box_page_requires_integer(page: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        BoundingBoxIR(0, 0, 1, 1, page)


# 이미지 rotation requires finite value 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("rotation", [float("nan"), float("inf"), -float("inf")])
def test_image_rotation_requires_finite_value(rotation: float) -> None:
    with pytest.raises(ValueError, match="rotation"):
        ImageIR(b"image", "image/png", "PNG", 10, 5, rotation_deg=rotation)


# partial original dimensions do not invent other dimension 기능의 정상 동작 및 제약조건을 테스트함
def test_partial_original_dimensions_do_not_invent_other_dimension() -> None:
    image = ImageIR(b"image", "image/png", "PNG", 10, 5, original_width_px=800)
    assert image.original_height_px is None
    assert image.aspect_ratio == 2
