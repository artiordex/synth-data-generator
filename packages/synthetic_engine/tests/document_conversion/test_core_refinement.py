# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_core_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_core_refinement.py
# 목적: IR 코어 모듈 리팩토링 정합성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Core validation and detached audit snapshot regressions."""
import base64
import json

import pytest

from synthetic_engine.document_conversion.core.enums import SupportStatus
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR, DrawingIR, HeaderFooterIR, HyperlinkIR, ImageIR, ParagraphIR,
    SectionIR, TableCellIR, TableIR,
    TextRunIR, UnsupportedRecordIR,
)
from synthetic_engine.document_conversion.core.resources import ResourceStore
from synthetic_engine.document_conversion.core.serialization import document_to_dict, document_to_json
from synthetic_engine.document_conversion.core.source_ref import BoundingBoxIR, SourceRef


# malformed mime does not add resource 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("mime", ["/", "image/", "/png", "image/png/extra", "image/(png)", "image/png\n"])
def test_malformed_mime_does_not_add_resource(mime):
    store = ResourceStore()
    with pytest.raises(ValueError, match="MIME"):
        store.add(b"payload", mime)
    assert len(store) == 0


# ir numeric validation rejects non numbers and overflow 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("value", [True, "1", 10**1000, float("nan")])
def test_ir_numeric_validation_rejects_non_numbers_and_overflow(value):
    with pytest.raises(ValueError, match="finite"):
        BoundingBoxIR(value, 0, 1, 1, 1)
    with pytest.raises(ValueError, match="Confidence"):
        TableIR(table_confidence=value)
    with pytest.raises(ValueError, match="dimensions"):
        ImageIR(b"x", "image/png", "PNG", value, 1)


# bounding box rejects overflowing extent 기능의 정상 동작 및 제약조건을 테스트함
def test_bounding_box_rejects_overflowing_extent():
    with pytest.raises(ValueError, match="extents"):
        BoundingBoxIR(-1e308, 0, 1e308, 1, 1)


# snapshot retains 텍스트 provenance unknown bytes and 진행 상태 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_retains_text_provenance_unknown_bytes_and_status():
    text = " \u00a0\u3000\uc2dd\uc57d\ucc98\t\n "
    ref = SourceRef("hwp", page_no=1, record_offset=0)
    record = UnsupportedRecordIR(77, 2, b"\x00\xff", source_ref=ref)
    doc = DocumentIR(document_id="stable", sections=[SectionIR(elements=[
        ParagraphIR([TextRunIR(text)]), record,
    ])])
    snapshot = json.loads(document_to_json(doc))
    blocks = snapshot["document"]["sections"][0]["elements"]
    assert snapshot["schema_version"] == 1
    assert blocks[0]["inlines"][0]["text"] == text
    assert blocks[1]["$type"] == "UnsupportedRecordIR"
    assert blocks[1]["support_status"] == SupportStatus.UNSUPPORTED.value
    assert blocks[1]["source_ref"]["record_offset"] == 0
    digest = blocks[1]["raw_bytes"]["$resource"]
    assert base64.b64decode(snapshot["resources"][digest]["data"]) == b"\x00\xff"
    assert document_to_json(doc) == document_to_json(doc)
    blocks[0]["inlines"][0]["text"] = "changed"
    assert doc.sections[0].elements[0].inlines[0].text == text


# snapshot interns late 이미지 목록 without mutating document 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_interns_late_images_without_mutating_document():
    doc = DocumentIR(sections=[SectionIR()])
    attachment = doc.resources.add(b"attachment", "application/pdf")
    first = ImageIR(b"same", "image/png", "PNG", 2, 1)
    second = ImageIR(b"same", "image/jpeg", "JPEG", 4, 2)
    doc.sections[0].elements.extend([first, second])
    snapshot = document_to_dict(doc)
    blocks = snapshot["document"]["sections"][0]["elements"]
    digest = blocks[0]["resource_id"]
    assert digest == blocks[1]["resource_id"]
    assert snapshot["resources"][digest]["mime_types"] == ["image/jpeg", "image/png"]
    assert len(snapshot["resources"]) == 2
    assert attachment in snapshot["resources"]
    assert first.resource_id is second.resource_id is None
    assert len(doc.resources) == 1


# snapshot allows repeated objects but rejects inline cycles 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_allows_repeated_objects_but_rejects_inline_cycles():
    link = HyperlinkIR("https://example.invalid", [TextRunIR("link")])
    paragraph = ParagraphIR([link])
    doc = DocumentIR(sections=[SectionIR(elements=[paragraph, paragraph])])
    snapshot = document_to_dict(doc)
    blocks = snapshot["document"]["sections"][0]["elements"]
    assert blocks[0] == blocks[1]
    link.inlines.append(link)
    with pytest.raises(ValueError, match="cycle"):
        document_to_json(doc)


# snapshot rejects nonfinite mutations 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_rejects_nonfinite_mutations():
    run = TextRunIR("text")
    doc = DocumentIR(sections=[SectionIR(elements=[ParagraphIR([run])])])
    run.size_pt = float("nan")
    with pytest.raises(ValueError, match="finite"):
        document_to_json(doc)


# snapshot handles deep 표 목록 and detects deep cycles 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_handles_deep_tables_and_detects_deep_cycles():
    leaf = ParagraphIR([TextRunIR("deep text")])
    block = leaf
    for _ in range(1500):
        block = TableIR(rows=[[TableCellIR(0, 0, content=[block])]])
    doc = DocumentIR(sections=[SectionIR(elements=[block, block])])
    snapshot = document_to_dict(doc)
    for occurrence in snapshot["document"]["sections"][0]["elements"]:
        for _ in range(1500):
            assert occurrence["$type"] == "TableIR"
            occurrence = occurrence["rows"][0][0]["content"][0]
        assert occurrence["inlines"][0]["text"] == "deep text"
    leaf.inlines.append(HyperlinkIR("cycle", [leaf]))
    with pytest.raises(ValueError, match="cycle"):
        document_to_dict(doc)


# json encoder recursion error is explicit 기능의 정상 동작 및 제약조건을 테스트함
def test_json_encoder_recursion_error_is_explicit(monkeypatch):
    # fail 작업을 수행함
    def fail(*args, **kwargs):
        raise RecursionError("encoder runtime limit")

    monkeypatch.setattr(json, "dumps", fail)
    with pytest.raises(ValueError, match="JSON encoder recursion limit") as error:
        document_to_json(DocumentIR())
    assert isinstance(error.value.__cause__, RecursionError)


# snapshot resource order is independent of insertion order 기능의 정상 동작 및 제약조건을 테스트함
def test_snapshot_resource_order_is_independent_of_insertion_order():
    first, second = DocumentIR(document_id="same"), DocumentIR(document_id="same")
    for payload in (b"a", b"b"):
        first.resources.add(payload)
    for payload in (b"b", b"a"):
        second.resources.add(payload)
    assert document_to_json(first) == document_to_json(second)


# document rejects hyperlink cycles at construction 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("indirect", [False, True])
def test_document_rejects_hyperlink_cycles_at_construction(indirect):
    link = HyperlinkIR("first")
    if indirect:
        link.inlines.append(HyperlinkIR("second", [link]))
    else:
        link.inlines.append(link)
    with pytest.raises(ValueError, match="inline graph contains a cycle"):
        DocumentIR(sections=[SectionIR(elements=[ParagraphIR([link])])])


# document rechecks mutated inline cycles in all 문서 블록 locations 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("location", ["body", "header", "footer", "cell", "table_caption", "image_caption", "drawing"])
def test_document_rechecks_mutated_inline_cycles_in_all_block_locations(location):
    link = HyperlinkIR("target", [TextRunIR("text")])
    paragraph = ParagraphIR([link])
    section = SectionIR()
    if location in ("header", "footer"):
        setattr(section, location, HeaderFooterIR([paragraph]))
    elif location == "cell":
        section.elements = [TableIR(rows=[[TableCellIR(0, 0, content=[paragraph])]])]
    elif location == "table_caption":
        section.elements = [TableIR(caption=paragraph)]
    elif location == "image_caption":
        section.elements = [ImageIR(b"x", "image/png", "PNG", 1, 1, caption=paragraph)]
    elif location == "drawing":
        section.elements = [DrawingIR("text_box", text_content=[paragraph])]
    else:
        section.elements = [paragraph]
    document = DocumentIR(sections=[section])
    link.inlines.append(link)
    with pytest.raises(ValueError, match="inline graph contains a cycle"):
        for block in document.iter_blocks():
            assert block is not paragraph
    with pytest.raises(ValueError, match="inline graph contains a cycle"):
        document.intern_resources()


# document allows deep shared inline graph and detects late cycle 기능의 정상 동작 및 제약조건을 테스트함
def test_document_allows_deep_shared_inline_graph_and_detects_late_cycle():
    leaf = HyperlinkIR("leaf", [TextRunIR("unchanged")])
    root = leaf
    for _ in range(1500):
        root = HyperlinkIR("parent", [root])
    left, right = HyperlinkIR("left", [root]), HyperlinkIR("right", [root])
    paragraph = ParagraphIR([left, right, leaf, leaf])
    document = DocumentIR(sections=[SectionIR(elements=[paragraph, paragraph])])
    assert list(document.iter_blocks()) == [paragraph, paragraph]
    assert paragraph.inlines == [left, right, leaf, leaf]
    leaf.inlines.append(root)
    with pytest.raises(ValueError, match="inline graph contains a cycle"):
        list(document.iter_blocks())
