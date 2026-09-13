# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_word_document_conversion.py
# 경로: packages/synthetic_engine/tests/test_word_document_conversion.py
# 목적: 워드(DOCX) 문서 변환 충실도 및 정합성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

import zipfile

import pandas as pd

from synthetic_engine.exporters.document_exporter import (
    convert_word_to_html,
    convert_word_to_hwpx,
    convert_word_to_markdown,
    export_pseudonymized_document,
)


# hyperlink 항목을 목록에 추가함
def _add_hyperlink(paragraph, label: str, url: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    rel_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = label
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


# structured 워드(DOCX) 객체 또는 요소를 생성함
def _make_structured_docx(path):
    import docx

    doc = docx.Document()
    doc.add_heading("Document Title", level=1)
    doc.add_paragraph("Before table paragraph.")

    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Name"
    table.rows[0].cells[1].text = "URL"
    table.rows[1].cells[0].text = "Alpha"
    table.rows[1].cells[1].text = "Value | with pipe"

    doc.add_paragraph("After table paragraph.")
    doc.add_paragraph("Top bullet", style="List Bullet")
    doc.add_paragraph("Nested bullet", style="List Bullet 2")

    linked = doc.add_paragraph("Visit ")
    _add_hyperlink(linked, "OpenAI", "https://openai.com/docs")
    linked.add_run(" for details.")
    doc.save(path)


# word to 마크다운 preserves structure and links 기능의 정상 동작 및 제약조건을 테스트함
def test_word_to_markdown_preserves_structure_and_links(tmp_path):
    source = tmp_path / "structured.docx"
    _make_structured_docx(source)

    md = convert_word_to_markdown(source)

    assert "# Document Title" in md
    assert "Before table paragraph." in md
    assert "| Name | URL |" in md
    assert "Value \\| with pipe" in md
    assert md.index("Before table paragraph.") < md.index("| Name | URL |") < md.index("After table paragraph.")
    assert "- Top bullet" in md
    assert "  - Nested bullet" in md
    assert "[OpenAI](https://openai.com/docs)" in md


# word to HTML 웹 문서 preserves semantic 블록 목록 and links 기능의 정상 동작 및 제약조건을 테스트함
def test_word_to_html_preserves_semantic_blocks_and_links(tmp_path):
    source = tmp_path / "structured.docx"
    _make_structured_docx(source)

    html = convert_word_to_html(source)

    assert "<h1>Document Title</h1>" in html
    assert "<table>" in html
    assert "<th>Name</th>" in html
    assert "<p>After table paragraph.</p>" in html
    assert html.index("<p>Before table paragraph.</p>") < html.index("<table>") < html.index("<p>After table paragraph.</p>")
    assert '<a href="https://openai.com/docs">OpenAI</a>' in html
    assert "<ul>" in html
    assert "<li>Nested bullet</li>" in html


# export word original to 마크다운 HTML 웹 문서 and 한글 표준(HWPX) 기능의 정상 동작 및 제약조건을 테스트함
def test_export_word_original_to_markdown_html_and_hwpx(tmp_path):
    source = tmp_path / "structured.docx"
    _make_structured_docx(source)
    df = pd.DataFrame({"문서_내용": ["fallback text"]})

    md_path = export_pseudonymized_document(df, "md", tmp_path / "out.md", original_filepath=source)
    html_path = export_pseudonymized_document(df, "html", tmp_path / "out.html", original_filepath=source)
    hwpx_path = export_pseudonymized_document(df, "hwpx", tmp_path / "out.hwpx", original_filepath=source)

    assert "fallback text" not in md_path.read_text(encoding="utf-8")
    assert "| Name | URL |" in md_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_path.read_text(encoding="utf-8")
    assert '<a href="https://openai.com/docs">OpenAI</a>' in html_path.read_text(encoding="utf-8")
    assert zipfile.is_zipfile(hwpx_path)

    from hwpx.document import HwpxDocument

    hwpx_text = HwpxDocument.open(hwpx_path).text.plain()
    assert "Document Title" in hwpx_text
    assert "Top bullet" in hwpx_text
    assert "Alpha" in hwpx_text
