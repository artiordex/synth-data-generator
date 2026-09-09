import zipfile

import pymupdf as fitz

from synthetic_engine.exporters.pdf_high_fidelity_converter import (
    HighFidelityPdfDoc,
    convert_pdf_to_high_fidelity_html,
    convert_pdf_to_high_fidelity_hwpx,
    convert_pdf_to_high_fidelity_markdown,
)


def _write_text_grid_pdf(path):
    with fitz.open() as doc:
        for page_no in range(1, 3):
            page = doc.new_page(width=420, height=360)
            page.insert_text((45, 45), f"Page {page_no} Title", fontsize=15)
            page.insert_text((45, 92), f"Intro paragraph page {page_no}", fontsize=10)
            page.insert_text((55, 145), "Name", fontsize=10)
            page.insert_text((205, 145), "Amount", fontsize=10)
            page.insert_text((55, 172), f"Alpha {page_no}", fontsize=10)
            page.insert_text((205, 172), f"{page_no}00", fontsize=10)
            page.insert_text((45, 230), f"After table page {page_no}", fontsize=10)
            page.insert_text((195, 335), f"- {page_no} -", fontsize=9)
        doc.save(path)


def _write_lined_table_pdf(path):
    with fitz.open() as doc:
        page = doc.new_page(width=420, height=360)
        page.draw_rect(
            fitz.Rect(30, 30, 390, 80),
            color=(0.1, 0.2, 0.4),
            fill=(0.1, 0.2, 0.4),
        )
        page.insert_text((45, 60), "Document Title", fontsize=15, color=(1, 1, 1))
        page.insert_text((45, 112), "Structured paragraph before table", fontsize=10)

        left, top, right, bottom = 45, 150, 375, 232
        for y in (top, 177, 204, bottom):
            page.draw_line((left, y), (right, y), color=(0.25, 0.25, 0.25))
        for x in (left, 128, 246, 302, right):
            page.draw_line((x, top), (x, bottom), color=(0.25, 0.25, 0.25))
        page.insert_text((55, 168), "Field", fontsize=10)
        page.insert_text((138, 168), "Value", fontsize=10)
        page.insert_text((256, 168), "Code", fontsize=10)
        page.insert_text((312, 168), "Count", fontsize=10)
        page.insert_text((55, 195), "Name", fontsize=10)
        page.insert_text((138, 195), "Alpha", fontsize=10)
        page.insert_text((256, 195), "A1", fontsize=10)
        page.insert_text((312, 195), "100", fontsize=10)
        doc.save(path)


def test_pymupdf_text_grid_rows_preserve_page_order(tmp_path):
    source = tmp_path / "text-grid.pdf"
    _write_text_grid_pdf(source)

    doc = HighFidelityPdfDoc(source)
    try:
        assert len(doc.pages) == 2
        first_elements = doc.pages[0]["elements"]
        table = next(e for e in first_elements if e["type"] == "table")
        assert table["source"] == "pymupdf_text_grid"
        assert table["rows"][0] == {"type": "colspan", "c0": "Name", "c1": "Amount"}
        assert table["rows"][1] == {"type": "colspan", "c0": "Alpha 1", "c1": "100"}

        ordered_text = [
            "\n".join(block["text"] for block in elem.get("blocks", []))
            for elem in first_elements
            if elem["type"] in {"paragraph", "table"}
        ]
        assert ordered_text[0] == "Page 1 Title"
        assert ordered_text[1] == "Intro paragraph page 1"
        assert first_elements.index(table) < next(
            idx for idx, elem in enumerate(first_elements)
            if elem["type"] == "paragraph" and "After table" in elem["blocks"][0]["text"]
        )
    finally:
        doc.close()

    markdown = convert_pdf_to_high_fidelity_markdown(source)
    assert "## Page 1" in markdown
    assert "## Page 2" in markdown
    assert "| Alpha 2 | 200 | - | - |" in markdown


def test_pdfplumber_table_feeds_html_markdown_and_hwpx(tmp_path):
    source = tmp_path / "lined-table.pdf"
    _write_lined_table_pdf(source)

    doc = HighFidelityPdfDoc(source)
    try:
        table = next(e for e in doc.pages[0]["elements"] if e["type"] == "table")
        assert table["source"] == "pdfplumber"
        assert table["rows"][1] == {"type": "4col", "c0": "Name", "c1": "Alpha", "c2": "A1", "c3": "100"}
    finally:
        doc.close()

    html = convert_pdf_to_high_fidelity_html(source, title="layout")
    markdown = convert_pdf_to_high_fidelity_markdown(source)
    assert 'id="page-1"' in html
    assert "<th>Name</th><td>Alpha</td>" in html
    assert "| Name | Alpha | A1 | 100 |" in markdown

    target = tmp_path / "lined-table.hwpx"
    convert_pdf_to_high_fidelity_hwpx(source, target)
    assert zipfile.is_zipfile(target)
