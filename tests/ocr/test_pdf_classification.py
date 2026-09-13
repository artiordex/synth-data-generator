# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pdf_classification.py
# 경로: tests/ocr/test_pdf_classification.py
# 목적: PDF 문서 유형(디지털/스캔) 자동 분류 알고리즘을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pytest

fitz = pytest.importorskip("pymupdf")
from PIL import Image

from ocr.pdf.classification import classify_pdf
from ocr.pdf.inspection import inspect_pdf_pages
from ocr.pdf.pipeline import plan_pdf_ocr, run_pdf_ocr
from ocr.pipeline.models import OCRStatus, PdfType


# 텍스트 PDF 문서 is classified without OCR 인식 기능의 정상 동작 및 제약조건을 테스트함
def test_text_pdf_is_classified_without_ocr(tmp_path):
    source = tmp_path / "text.pdf"
    with fitz.open() as document:
        page = document.new_page(width=300, height=200)
        page.insert_text((30, 50), "MFDS PDF Text Layer 123")
        document.save(source)

    assert classify_pdf(source) == PdfType.TEXT_PDF
    plan = plan_pdf_ocr(source)
    assert plan.native_text_pages == (1,)
    assert plan.ocr_pages == ()


# 이미지 only PDF 문서 is classified for OCR 인식 기능의 정상 동작 및 제약조건을 테스트함
def test_image_only_pdf_is_classified_for_ocr(tmp_path):
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (200, 120), "white").save(image_path)
    source = tmp_path / "scan.pdf"
    with fitz.open() as document:
        page = document.new_page(width=300, height=200)
        page.insert_image(fitz.Rect(30, 30, 230, 150), filename=image_path)
        document.save(source)

    assert classify_pdf(source) == PdfType.IMAGE_ONLY_PDF
    inspection = inspect_pdf_pages(source)
    assert inspection.pages[0].ocr_required is True
    assert inspection.pages[0].image_count == 1
    assert plan_pdf_ocr(source).ocr_pages == (1,)


# mixed PDF 문서 is classified 페이지 by 페이지 기능의 정상 동작 및 제약조건을 테스트함
def test_mixed_pdf_is_classified_page_by_page(tmp_path):
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (200, 120), "white").save(image_path)
    source = tmp_path / "mixed.pdf"
    with fitz.open() as document:
        text_page = document.new_page(width=300, height=200)
        text_page.insert_text((30, 50), "MFDS PDF Text Layer 123")
        image_page = document.new_page(width=300, height=200)
        image_page.insert_image(fitz.Rect(30, 30, 230, 150), filename=image_path)
        document.save(source)

    assert classify_pdf(source) == PdfType.MIXED_PDF
    plan = plan_pdf_ocr(source)
    assert plan.native_text_pages == (1,)
    assert plan.ocr_pages == (2,)


# mixed PDF 문서 OCR 인식 only renders required 페이지 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_mixed_pdf_ocr_only_renders_required_pages(tmp_path):
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (200, 120), "white").save(image_path)
    source = tmp_path / "mixed.pdf"
    with fitz.open() as document:
        text_page = document.new_page(width=300, height=200)
        text_page.insert_text((30, 50), "MFDS PDF Text Layer 123")
        image_page = document.new_page(width=300, height=200)
        image_page.insert_image(fitz.Rect(30, 30, 230, 150), filename=image_path)
        document.save(source)

    class CountingBackend:
        name = "counting"

        # CountingBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(self):
            self.calls = []

        # recognize 페이지 작업을 수행함
        def recognize_page(self, image, *, page_no=1):
            from ocr.pipeline.models import BoundingBox, OCRPageResult, OCRWord, confidence_stats
            from ocr.text.normalization import normalize_ocr_text

            self.calls.append((page_no, image.config.target_dpi, image.width_px, image.height_px))
            words = (OCRWord("식약처", 0.91, BoundingBox(0, 0, 30, 12)),)
            mean, med = confidence_stats(words)
            return OCRPageResult(
                page_no=page_no,
                raw_text="식약처",
                normalized_text=normalize_ocr_text("식약처"),
                words=words,
                mean_confidence=mean,
                median_confidence=med,
                engine=self.name,
                status=OCRStatus.SUCCESS,
            )

        # recognize region 작업을 수행함
        def recognize_region(self, image, bbox, *, page_no=1):
            return self.recognize_page(image, page_no=page_no)

    backend = CountingBackend()
    result = run_pdf_ocr(source, backend=backend, dpi=300)

    assert result.status == OCRStatus.SUCCESS
    assert backend.calls == [(2, 300, 1250, 834)]
    assert [page.status for page in result.pages] == [OCRStatus.NOT_REQUIRED, OCRStatus.SUCCESS]
