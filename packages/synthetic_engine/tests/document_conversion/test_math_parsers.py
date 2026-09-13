# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_math_parsers.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_math_parsers.py
# 목적: 수식 IR 계약과 포맷별 원본 보존 파서 동작을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Math parsing contracts and format-specific preservation regressions."""
from io import BytesIO
import struct
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from PIL import Image

from synthetic_engine.document_conversion.core.ir import (
    DocumentIR,
    MathIR,
    ParagraphIR,
    SectionIR,
    TableIR,
    TextRunIR,
    UnsupportedRecordIR,
)
from synthetic_engine.document_conversion.core.resources import ResourceStore
from synthetic_engine.document_conversion.core.serialization import document_to_dict
from synthetic_engine.document_conversion.core.source_ref import SourceRef
from synthetic_engine.document_conversion.parsers.docx_parser import DocxParser, M, R, W
from synthetic_engine.document_conversion.parsers.hwp5_parser import _parse_eqedit_math
from synthetic_engine.document_conversion.parsers.hwpx_parser import HH, HP, HS, HwpxParser
from synthetic_engine.document_conversion.parsers.image_parser import ImageParser


def _archive(entries: dict[str, str | bytes]) -> BytesIO:
    stream = BytesIO()
    with ZipFile(stream, "w") as package:
        for name, data in entries.items():
            package.writestr(name, data)
    stream.seek(0)
    return stream


def _docx(body: str) -> BytesIO:
    return _archive({
        "word/document.xml": (
            f'<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:m="{M}">'
            f"<w:body>{body}</w:body></w:document>"
        )
    })


def _hwpx(body: str) -> BytesIO:
    return _archive({
        "Contents/header.xml": f'<h:head xmlns:h="{HH}"/>',
        "Contents/section0.xml": (
            f'<s:sec xmlns:s="{HS}" xmlns:p="{HP}">{body}</s:sec>'
        ),
    })


def _linear_omml(text: str = "x+1=2") -> str:
    return f"<m:oMath><m:r><m:t>{text}</m:t></m:r></m:oMath>"


def test_math_ir_rejects_invalid_confidence_and_empty_fallback():
    with pytest.raises(ValueError, match="Confidence"):
        MathIR(latex="x", confidence=1.1)
    with pytest.raises(ValueError, match="evidence"):
        MathIR(needs_review=True, failure_reason="recognition failed")
    with pytest.raises(ValueError, match="failure reason"):
        MathIR(source_expression="?", needs_review=True)


def test_math_ir_serialization_keeps_contract_and_resource_manifest():
    resources = ResourceStore()
    resource_id = resources.add(b"<m:oMath/>", "application/xml")
    math = MathIR(
        source_ref=SourceRef("docx", xml_path="word/document.xml:/w:p/m:oMath"),
        latex="x",
        source_syntax="omml",
        source_resource_id=resource_id,
    )
    document = DocumentIR(
        source_format="docx",
        sections=[SectionIR(elements=[ParagraphIR([math])])],
        resources=resources,
    )

    snapshot = document_to_dict(document)
    serialized = snapshot["document"]["sections"][0]["elements"][0]["inlines"][0]

    assert serialized["$type"] == "MathIR"
    assert serialized["display_mode"] == "inline"
    assert serialized["source_resource_id"] == resource_id
    assert resource_id in snapshot["resources"]


def test_docx_inline_math_preserves_mixed_content_and_source_xml():
    body = (
        "<w:p><w:r><w:t xml:space=\"preserve\">before </w:t></w:r>"
        + _linear_omml()
        + "<w:r><w:t xml:space=\"preserve\"> after</w:t></w:r></w:p>"
    )
    document = DocxParser().parse(_docx(body))
    paragraph = document.sections[0].elements[0]

    assert isinstance(paragraph, ParagraphIR)
    assert [type(item) for item in paragraph.inlines] == [TextRunIR, MathIR, TextRunIR]
    math = paragraph.inlines[1]
    assert math.display_mode == "inline"
    assert math.latex == "x+1=2"
    assert math.mathml is None
    assert math.source_syntax == "omml"
    assert math.confidence is None
    assert math.needs_review is False
    assert b"oMath" in document.resources.get(math.source_resource_id)
    assert math.source_ref.xml_path.endswith("/m:oMath")


def test_docx_display_fraction_is_structured_latex():
    fraction = (
        "<m:oMathPara><m:oMath><m:f>"
        "<m:num><m:r><m:t>1</m:t></m:r></m:num>"
        "<m:den><m:r><m:t>n</m:t></m:r></m:den>"
        "</m:f></m:oMath></m:oMathPara>"
    )
    document = DocxParser().parse(_docx(fraction))
    math = document.sections[0].elements[0]

    assert isinstance(math, MathIR)
    assert math.display_mode == "display"
    assert math.latex == r"\frac{1}{n}"
    assert math.needs_review is False


def test_docx_table_cell_math_remains_inline_content():
    body = (
        "<w:tbl><w:tr><w:tc><w:tcPr/>"
        "<w:p><w:r><w:t>A=</w:t></w:r>"
        "<m:oMath><m:sSup><m:e><m:r><m:t>πr</m:t></m:r></m:e>"
        "<m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:oMath>"
        + "</w:p></w:tc></w:tr></w:tbl>"
    )
    document = DocxParser().parse(_docx(body))
    table = document.sections[0].elements[0]

    assert isinstance(table, TableIR)
    paragraph = table.rows[0][0].content[0]
    assert [type(item) for item in paragraph.inlines] == [TextRunIR, MathIR]
    assert paragraph.inlines[1].latex == "πr^{2}"


def test_docx_unsupported_math_is_reviewable_and_not_empty():
    body = (
        "<w:p><m:oMath><m:phant><m:e><m:r><m:t>x</m:t></m:r>"
        "</m:e></m:phant></m:oMath></w:p>"
    )
    document = DocxParser().parse(_docx(body))
    math = document.sections[0].elements[0].inlines[0]

    assert isinstance(math, MathIR)
    assert math.latex is None
    assert math.source_expression == "x"
    assert math.needs_review is True
    assert "unsupported OMML element" in math.failure_reason
    assert document.resources.get(math.source_resource_id)
    assert any(warning.code == "DOCX_MATH_REVIEW" for warning in document.warnings)


def test_docx_multiple_math_objects_have_distinct_source_references():
    body = "<w:p>" + _linear_omml("a") + _linear_omml("b") + "</w:p>"
    document = DocxParser().parse(_docx(body))
    maths = [item for item in document.sections[0].elements[0].inlines if isinstance(item, MathIR)]

    assert [item.latex for item in maths] == ["a", "b"]
    assert maths[0].source_ref.xml_path != maths[1].source_ref.xml_path


def test_hwpx_equation_preserves_native_script_and_xml_fallback():
    script = "{1} over {n _{j}}\r\n"
    body = (
        '<p:p><p:run><p:equation id="eq-1" lineMode="CHAR">'
        '<p:pos treatAsChar="1"/><p:script xml:space="preserve">'
        + script
        + "</p:script></p:equation></p:run></p:p>"
    )
    document = HwpxParser().parse(_hwpx(body))
    math = document.sections[0].elements[0].inlines[0]

    assert isinstance(math, MathIR)
    assert math.display_mode == "inline"
    assert math.latex is None
    # XML 1.0 normalizes CRLF while the exact package part remains available.
    assert math.source_expression == script.replace("\r\n", "\n")
    assert math.source_syntax == "hancom-equation-script"
    assert math.needs_review is True
    assert math.source_ref.object_id == "eq-1"
    source_xml = document.resources.get(math.source_resource_id)
    assert b"equation" in source_xml
    assert script.encode() in source_xml


def test_hwpx_ole_is_preserved_without_assuming_it_is_math():
    body = '<p:p><p:run><p:ole id="ole-1"><p:sz width="100" height="100"/></p:ole></p:run></p:p>'
    document = HwpxParser().parse(_hwpx(body))
    record = document.sections[0].elements[0]

    assert isinstance(record, UnsupportedRecordIR)
    assert b"ole" in record.raw_bytes
    assert record.source_ref.object_id == "ole-1"
    assert any(warning.code == "HWPX_OLE_REVIEW" for warning in document.warnings)


def test_hwp5_eqedit_preserves_script_and_raw_record():
    script = "{a} over {b}\r\n"
    encoded = script.encode("utf-16-le")
    payload = struct.pack("<IH", 0, len(script)) + encoded + b"\x00\x01fallback-tail"
    resources = ResourceStore()
    ref = SourceRef("hwp", section_no=1, record_offset=128)

    math = _parse_eqedit_math(payload, ref, resources)

    assert math.display_mode == "inline"
    assert math.source_expression == script
    assert math.source_syntax == "hwp-eqedit-script"
    assert math.needs_review is True
    assert resources.get(math.source_resource_id) == payload


def test_hwp5_invalid_eqedit_keeps_nonempty_fallback():
    payload = b"\x01\x02\x03"
    resources = ResourceStore()
    math = _parse_eqedit_math(payload, SourceRef("hwp", section_no=1), resources)

    assert math.latex is None and math.mathml is None
    assert math.source_expression is None
    assert math.needs_review is True
    assert "record" in math.failure_reason.lower()
    assert resources.get(math.source_resource_id) == payload


def test_image_explicit_math_candidate_keeps_bbox_image_and_review_state(monkeypatch, tmp_path):
    source = tmp_path / "equation.png"
    Image.new("RGB", (200, 100), "white").save(source)

    def fake_process(_image, page_num):
        return SimpleNamespace(
            text_blocks=[SimpleNamespace(
                text="x^2 + y^2 = z^2",
                bbox=(10, 20, 190, 50),
                confidence=0.72,
                is_equation=True,
                is_heading=False,
            )],
            tables=[],
            figures=[],
            warnings=[],
        )

    import synthetic_engine.exporters.ocr_table_reconstructor as reconstructor

    monkeypatch.setattr(reconstructor, "process_scanned_page", fake_process)
    document = ImageParser().parse(source)
    math = document.sections[0].elements[0]

    assert isinstance(math, MathIR)
    assert math.latex is None
    assert math.ocr_candidates == ["x^2 + y^2 = z^2"]
    assert math.confidence == 0.72
    assert math.needs_review is True
    assert (math.bbox.x0, math.bbox.y0, math.bbox.x1, math.bbox.y1) == (7.5, 15.0, 142.5, 37.5)
    assert document.resources.get(math.fallback_image_resource_id) == source.read_bytes()


def test_pdf_math_like_span_is_candidate_not_verified_latex(tmp_path):
    fitz = pytest.importorskip("pymupdf")
    from synthetic_engine.document_conversion.parsers.pdf import page_texts, parse_pdf

    source = tmp_path / "equation.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=300, height=200)
        page.insert_text((30, 50), "x + y = 2", fontsize=12)
        page.insert_text((30, 80), "ordinary sentence", fontsize=12)
        pdf.save(source)

    document = parse_pdf(source)
    first, second = document.sections[0].elements
    math = first.inlines[0]

    assert isinstance(math, MathIR)
    assert math.latex is None
    assert math.source_expression == "x + y = 2"
    assert math.source_syntax == "pdf-positioned-text-candidate"
    assert math.bbox is not None and math.source_ref.page_no == 1
    assert math.needs_review is True
    assert isinstance(second.inlines[0], TextRunIR)
    assert "x + y = 2" in page_texts(document)[0]
