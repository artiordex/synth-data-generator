# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pdf_high_fidelity_converter.py
# 경로: packages/synthetic_engine/tests/test_pdf_high_fidelity_converter.py
# 목적: PDF 문서 고충실도 변환 파이프라인을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import zipfile
from bs4 import BeautifulSoup

import pymupdf as fitz

from synthetic_engine.exporters.pdf_high_fidelity_converter import (
    HighFidelityPdfDoc,
    convert_pdf_to_high_fidelity_html,
    convert_pdf_to_high_fidelity_hwpx,
    convert_pdf_to_high_fidelity_markdown,
)


# 텍스트 격자 구조 PDF 문서 데이터를 파일에 기록함
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


# lined 표(테이블) PDF 문서 데이터를 파일에 기록함
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


# pymupdf 텍스트 격자 구조 행 목록 preserve 페이지 order 기능의 정상 동작 및 제약조건을 테스트함
def test_pymupdf_text_grid_rows_preserve_page_order(tmp_path):
    source = tmp_path / "text-grid.pdf"
    _write_text_grid_pdf(source)

    doc = HighFidelityPdfDoc(source)
    try:
        assert len(doc.pages) == 2
        first_elements = doc.pages[0]["elements"]
        table = next(e for e in first_elements if e["type"] == "table")
        assert table["source"] == "pymupdf_text_grid"
        assert [c['text'] for c in table['rows'][0]['cells']] == ['Name', 'Amount']
        assert [c['text'] for c in table['rows'][1]['cells']] == ['Alpha 1', '100']

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
    assert "| Alpha 2 | 200 |" in markdown


# pdfplumber 표(테이블) feeds HTML 웹 문서 마크다운 and 한글 표준(HWPX) 기능의 정상 동작 및 제약조건을 테스트함
def test_pdfplumber_table_feeds_html_markdown_and_hwpx(tmp_path):
    source = tmp_path / "lined-table.pdf"
    _write_lined_table_pdf(source)

    doc = HighFidelityPdfDoc(source)
    try:
        table = next(e for e in doc.pages[0]["elements"] if e["type"] == "table")
        assert table["source"] == "pdfplumber"
        assert [c['text'] for c in table['rows'][1]['cells']] == ['Name', 'Alpha', 'A1', '100']
        assert table['rows'][1]['cells'][0]['font'] == 'Helvetica'
    finally:
        doc.close()

    html = convert_pdf_to_high_fidelity_html(source, title="layout")
    markdown = convert_pdf_to_high_fidelity_markdown(source)
    assert 'id="page-1"' in html
    assert any([c.get_text() for c in row.find_all(['th', 'td'])] == ['Name', 'Alpha', 'A1', '100'] for row in BeautifulSoup(html, 'html.parser').find_all('tr'))
    assert "| Name | Alpha | A1 | 100 |" in markdown

    target = tmp_path / "lined-table.hwpx"
    convert_pdf_to_high_fidelity_hwpx(source, target)
    assert zipfile.is_zipfile(target)


# 셀 inline 이미지 all outputs and exact 한글 표준(HWPX) 너비 기능의 정상 동작 및 제약조건을 테스트함
def test_cell_inline_image_all_outputs_and_exact_hwpx_width(tmp_path):
    import xml.etree.ElementTree as ET
    import docx
    import openpyxl
    source = tmp_path / 'stamp.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page(width=400, height=300)
        for x in (40, 140, 240, 340):
            page.draw_line((x, 80), (x, 180))
        for y in (80, 130, 180):
            page.draw_line((40, y), (340, y))
        for row in range(2):
            for col in range(3):
                page.insert_text((45 + col * 100, 100 + row * 50), f'R{row}C{col}')
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 12), False)
        pix.clear_with(70)
        page.insert_image(fitz.Rect(290, 150, 315, 175), stream=pix.tobytes('png'))
        pdf.save(source)
    model = HighFidelityPdfDoc(source)
    try:
        assert not any(e['type'] == 'image' for e in model.pages[0]['elements'])
        table = next(e for e in model.pages[0]['elements'] if e['type'] == 'table')
        assert len(table['rows'][1]['cells'][2]['inline_images']) == 1
        soup = BeautifulSoup(model.to_html(), 'html.parser')
        assert len(soup.select('td img, th img')) == 1
        assert '<img ' in model.to_markdown()
        model.to_docx(tmp_path / 'stamp.docx')
        word = docx.Document(tmp_path / 'stamp.docx')
        assert len(word.tables[0].cell(1, 2)._tc.xpath('.//w:drawing')) == 1
        model.to_excel(tmp_path / 'stamp.xlsx')
        workbook = openpyxl.load_workbook(tmp_path / 'stamp.xlsx')
        assert any(ws._images for ws in workbook)
        model.to_hwpx(tmp_path / 'stamp.hwpx')
        with zipfile.ZipFile(tmp_path / 'stamp.hwpx') as archive:
            root = ET.fromstring(archive.read('Contents/section0.xml'))
            ns = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
            row = root.find('.//hp:tbl/hp:tr', ns)
            assert sum(int(size.attrib['width']) for size in row.findall('./hp:tc/hp:cellSz', ns)) == 42520
            assert len(root.findall('.//hp:tc//hp:pic', ns)) == 1
    finally:
        model.close()


# 테스트용 한글 폰트 로드 도우미 함수임
def _setup_test_korean_font(page):
    import os
    for p in ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]:
        if os.path.exists(p):
            page.insert_font(fontname="korean", fontfile=p)
            return "korean"
    return None


# 비표 문단(제목, 본문 줄글, 번호 매기기 목록 등)이 표로 잘못 분할되지 않음을 검증함
def test_non_table_prose_and_numbered_lists_not_split_into_tables(tmp_path):
    source = tmp_path / "prose_sample.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=420, height=400)
        fn = _setup_test_korean_font(page)

        if fn:
            title_text = "3. 공공데이터 포털 활용하기-1"
            line1_text = "공공데이터 포털은 행정안전부에서 운영하는 범정부 데이터 플랫폼입니다."
            line2_text = "누구나 필요한 국가 공공데이터를 자유롭게 검색하고 내려받을 수 있습니다."
            item1_text = "1) 범정부 공공데이터 포털 회원가입 및 로그인"
            item2_text = "2) 데이터 목록 검색 및 오픈API 사용 신청"
            item3_text = "3) 인증키(인증 토큰) 발급 후 데이터 연계 테스트 수행"
        else:
            title_text = "3. Public Data Portal Guide-1"
            line1_text = "The public data portal provides access to all government datasets."
            line2_text = "Users can freely search, download, and utilize API data services."
            item1_text = "1) Register and log in to the portal account"
            item2_text = "2) Search data catalogs and request API permission"
            item3_text = "3) Test API endpoints using issued authentication key"

        # 상단 소제목 및 장식용 밑줄선 삽입함
        page.insert_text((40, 50), title_text, fontname=fn, fontsize=14)
        page.draw_line((40, 65), (380, 65), color=(0.7, 0.7, 0.7))

        # 줄글 본문 문단 삽입함
        page.insert_text((40, 95), line1_text, fontname=fn, fontsize=10)
        page.insert_text((40, 115), line2_text, fontname=fn, fontsize=10)

        # 번호 매기기 목록 삽입함
        page.insert_text((40, 150), item1_text, fontname=fn, fontsize=10)
        page.insert_text((40, 175), item2_text, fontname=fn, fontsize=10)
        page.insert_text((40, 200), item3_text, fontname=fn, fontsize=10)

        # 하단 장식용 구분선 삽입함
        page.draw_line((40, 240), (380, 240), color=(0.7, 0.7, 0.7))
        pdf.save(source)

    model = HighFidelityPdfDoc(source)
    try:
        tables = [e for e in model.pages[0]["elements"] if e["type"] == "table"]
        # 비표 페이지이므로 표가 0개로 정상 판정되어야 함
        assert len(tables) == 0

        # Markdown 변환 결과에서도 인위적 표 분할 마크다운(| 열 1 | 등)이 없어야 함
        md = model.to_markdown()
        assert "| 열 1 |" not in md
        assert ("공공데이터" in md if fn else "Public Data" in md)
        assert ("1) 범정부" in md if fn else "1) Register" in md)
    finally:
        model.close()


# 복합 격자 표(헤더 및 데이터 셀)는 표 구조가 온전히 보존됨을 검증함
def test_complex_table_with_merged_cells_preserved(tmp_path):
    source = tmp_path / "complex_table.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=420, height=360)
        fn = _setup_test_korean_font(page)

        page_title = "정기 점검 현황표" if fn else "Inspection Report"
        headers = ["구분", "점검일자", "상태", "담당자"] if fn else ["Category", "Date", "Status", "Manager"]
        row1 = ["시스템 A", "2026-09-01", "정상", "홍길동"] if fn else ["System A", "2026-09-01", "OK", "John"]
        row2 = ["시스템 B", "2026-09-02", "점검필요", "이몽룡"] if fn else ["System B", "2026-09-02", "Warn", "Alice"]
        row3 = ["시스템 C", "2026-09-03", "정상", "성춘향"] if fn else ["System C", "2026-09-03", "OK", "Bob"]

        page.insert_text((40, 40), page_title, fontname=fn, fontsize=13)

        # 복합 테두리 선 생성함
        left, top, right, bottom = 40, 60, 380, 180
        # 수평선
        for y in (top, 90, 120, 150, bottom):
            page.draw_line((left, y), (right, y), color=(0, 0, 0))
        # 수직선
        for x in (left, 130, 210, 290, right):
            page.draw_line((x, top), (x, bottom), color=(0, 0, 0))

        # 셀 텍스트
        page.insert_text((50, 80), headers[0], fontname=fn, fontsize=9)
        page.insert_text((140, 80), headers[1], fontname=fn, fontsize=9)
        page.insert_text((220, 80), headers[2], fontname=fn, fontsize=9)
        page.insert_text((300, 80), headers[3], fontname=fn, fontsize=9)

        page.insert_text((50, 110), row1[0], fontname=fn, fontsize=9)
        page.insert_text((140, 110), row1[1], fontname=fn, fontsize=9)
        page.insert_text((220, 110), row1[2], fontname=fn, fontsize=9)
        page.insert_text((300, 110), row1[3], fontname=fn, fontsize=9)

        page.insert_text((50, 140), row2[0], fontname=fn, fontsize=9)
        page.insert_text((140, 140), row2[1], fontname=fn, fontsize=9)
        page.insert_text((220, 140), row2[2], fontname=fn, fontsize=9)
        page.insert_text((300, 140), row2[3], fontname=fn, fontsize=9)

        page.insert_text((50, 170), row3[0], fontname=fn, fontsize=9)
        page.insert_text((140, 170), row3[1], fontname=fn, fontsize=9)
        page.insert_text((220, 170), row3[2], fontname=fn, fontsize=9)
        page.insert_text((300, 170), row3[3], fontname=fn, fontsize=9)

        pdf.save(source)

    model = HighFidelityPdfDoc(source)
    try:
        tables = [e for e in model.pages[0]["elements"] if e["type"] == "table"]
        assert len(tables) == 1
        table = tables[0]
        # 4행 4열 구조가 정확히 보존되어야 함
        assert len(table["rows"]) == 4
        assert [c["text"] for c in table["rows"][0]["cells"]] == headers
        assert [c["text"] for c in table["rows"][1]["cells"]] == row1

        md = model.to_markdown()
        assert f"| {headers[0]} | {headers[1]} | {headers[2]} | {headers[3]} |" in md
        assert f"| {row1[0]} | {row1[1]} | {row1[2]} | {row1[3]} |" in md
    finally:
        model.close()


# 표(테이블) of contents not converted to 표(테이블) 기능의 정상 동작 및 제약조건을 테스트함
def test_table_of_contents_not_converted_to_table(tmp_path):
    """목차(CONTENTS) 및 개요 번호와 페이지 번호 목록이 표로 오인 분할되지 않음을 검증함."""
    source = tmp_path / "toc.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=420, height=500)
        fn = _setup_test_korean_font(page)
        page.insert_text((45, 50), "CONTENTS", fontname=fn, fontsize=16)
        page.insert_text((45, 90), "I. Chapter One Analysis", fontname=fn, fontsize=12)
        page.insert_text((65, 120), "1. Background and Purpose", fontname=fn, fontsize=10)
        page.insert_text((350, 120), "2", fontname=fn, fontsize=10)
        page.insert_text((65, 150), "2. Content and Scope", fontname=fn, fontsize=10)
        page.insert_text((350, 150), "3", fontname=fn, fontsize=10)
        page.insert_text((65, 180), "3. Method", fontname=fn, fontsize=10)
        page.insert_text((350, 180), "5", fontname=fn, fontsize=10)
        page.insert_text((45, 220), "II. Chapter Two Statistics", fontname=fn, fontsize=12)
        page.insert_text((65, 250), "1. Research Status", fontname=fn, fontsize=10)
        page.insert_text((350, 250), "8", fontname=fn, fontsize=10)
        page.insert_text((65, 280), "2. Researcher Distribution", fontname=fn, fontsize=10)
        page.insert_text((350, 280), "11", fontname=fn, fontsize=10)
        pdf.save(source)

    model = HighFidelityPdfDoc(source)
    try:
        tables = [e for e in model.pages[0]["elements"] if e["type"] == "table"]
        # 목차 페이지이므로 표가 0개여야 함
        assert len(tables) == 0
        md = model.to_markdown()
        # 마크다운 렌더링 시 표 구문(| ... |)이 없어야 함
        assert "| 열 1 |" not in md
        assert "CONTENTS" in md
        assert "Chapter One Analysis" in md
        assert "Background and Purpose" in md
    finally:
        model.close()


