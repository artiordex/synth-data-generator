# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pdf_parser.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_pdf_parser.py
# 목적: PDF 파서의 텍스트 및 그래픽 추출 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pytest

fitz = pytest.importorskip('pymupdf')
from synthetic_engine.document_conversion.parsers.pdf import parse_pdf, page_texts
from synthetic_engine.document_conversion.core.ir import ImageIR, TextRunIR


# PDF 문서 텍스트 스타일 서식 provenance and source resource 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_text_style_provenance_and_source_resource(tmp_path):
    path = tmp_path / 'source.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page(width=400, height=300)
        page.insert_text((30, 40), 'Phone:  010-1234-5678', fontname='hebo', fontsize=12)
        page.insert_text((30, 70), 'second line')
        pdf.save(path)
        expected = [page.get_text()]
    document = parse_pdf(path)
    assert page_texts(document) == expected
    section = document.sections[0]
    assert section.page_width_pt == 400
    run = section.elements[0].inlines[0]
    assert isinstance(run, TextRunIR) and run.bold and run.size_pt == 12
    assert run.source_ref.page_no == 1
    assert run.bbox.x0 == 30
    assert path.read_bytes() in [document.resources.get(key) for key in document.resources.digests()]
    assert any(w.code == 'PDF_POSITIONED_CONTENT' for w in document.warnings)


# PDF 문서 이미지 occurrences share bytes 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_image_occurrences_share_bytes(tmp_path):
    path = tmp_path / 'images.pdf'
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 4, 4), False)
    pixmap.clear_with(255)
    with fitz.open() as pdf:
        page = pdf.new_page()
        for x in (10, 50):
            page.insert_image(fitz.Rect(x, 10, x + 20, 30), stream=pixmap.tobytes('png'))
        pdf.save(path)
    document = parse_pdf(path)
    images = [block for block in document.iter_blocks() if isinstance(block, ImageIR)]
    assert len(images) == 2
    assert images[0].image_bytes is images[1].image_bytes
    assert images[0].bbox != images[1].bbox


# PDF 문서 페이지 limit 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_page_limit(tmp_path):
    path = tmp_path / 'pages.pdf'
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.new_page()
        pdf.save(path)
    with pytest.raises(ValueError, match='exceeds'):
        parse_pdf(path, max_pages=1)
