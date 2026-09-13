# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_free_pipeline.py
# 경로: packages/synthetic_engine/tests/test_ocr_free_pipeline.py
# 목적: 네이티브 텍스트 추출 기반 OCR Free 변환을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

import cv2
import numpy as np
import pymupdf
import pytest

from synthetic_engine.exporters import ocr_table_reconstructor as reconstructor


# full 페이지 scan uses native embedded 이미지 기능의 정상 동작 및 제약조건을 테스트함
def test_full_page_scan_uses_native_embedded_image(tmp_path, monkeypatch) -> None:
    source_image = np.full((900, 600, 3), 255, dtype=np.uint8)
    cv2.putText(source_image, "OCR", (80, 300), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 5)
    ok, encoded = cv2.imencode(".png", source_image)
    assert ok

    pdf_path = tmp_path / "scan.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=450)
    page.insert_image(page.rect, stream=encoded.tobytes())
    document.save(pdf_path)
    document.close()

    captured = []

    # fake process 작업을 수행함
    def fake_process(image, page_num):
        captured.append(image.shape)
        return reconstructor.OCRPageResult(page_num, image.shape[1], image.shape[0])

    monkeypatch.setattr(reconstructor, "process_scanned_page", fake_process)
    pages = reconstructor.extract_scanned_pdf_pages(pdf_path, dpi=72)

    assert len(pages) == 1
    assert captured == [(900, 600, 3)]


# full 페이지 native 이미지 honors PDF 문서 rotation 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize(
    ("rotation", "expected_shape", "expected_marker_yx"),
    [
        (0, (90, 60, 3), (10, 12)),
        (90, (60, 90, 3), (12, 79)),
        (180, (90, 60, 3), (79, 47)),
        (270, (60, 90, 3), (47, 10)),
    ],
)
def test_full_page_native_image_honors_pdf_rotation(
    tmp_path, monkeypatch, rotation, expected_shape, expected_marker_yx
) -> None:
    source_image = np.full((90, 60, 3), 255, dtype=np.uint8)
    source_image[5:16, 7:18] = (0, 0, 255)
    ok, encoded = cv2.imencode(".png", source_image)
    assert ok

    pdf_path = tmp_path / f"scan-rot-{rotation}.pdf"
    document = pymupdf.open()
    page = document.new_page(width=60, height=90)
    page.insert_image(page.rect, stream=encoded.tobytes())
    page.set_rotation(rotation)
    document.save(pdf_path)
    document.close()

    captured = []

    # fake process 작업을 수행함
    def fake_process(image, page_num):
        captured.append(image.copy())
        return reconstructor.OCRPageResult(page_num, image.shape[1], image.shape[0])

    monkeypatch.setattr(reconstructor, "process_scanned_page", fake_process)

    reconstructor.extract_scanned_pdf_pages(pdf_path, dpi=72)

    assert [image.shape for image in captured] == [expected_shape]
    y, x = expected_marker_yx
    assert tuple(int(value) for value in captured[0][y, x]) == (0, 0, 255)


# rendering is used when native 이미지 is disabled 기능의 정상 동작 및 제약조건을 테스트함
def test_rendering_is_used_when_native_image_is_disabled(tmp_path, monkeypatch) -> None:
    source_image = np.full((900, 600, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", source_image)
    assert ok
    pdf_path = tmp_path / "scan.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=450)
    page.insert_image(page.rect, stream=encoded.tobytes())
    document.save(pdf_path)
    document.close()
    monkeypatch.setenv("OCR_USE_NATIVE_PDF_IMAGE", "false")

    captured = []
    monkeypatch.setattr(
        reconstructor,
        "process_scanned_page",
        lambda image, page_num: captured.append(image.shape)
        or reconstructor.OCRPageResult(page_num, image.shape[1], image.shape[0]),
    )
    reconstructor.extract_scanned_pdf_pages(pdf_path, dpi=72)

    assert captured == [(450, 300, 3)]


# korean spacing never changes non space characters 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_spacing_never_changes_non_space_characters(monkeypatch) -> None:
    class Spacer:
        # space 작업을 수행함
        def space(self, text, reset_whitespace=False):
            assert reset_whitespace is False
            return "환경을 제공한다"

    monkeypatch.setattr(reconstructor, "_KOREAN_SPACER", Spacer())
    reconstructor._restore_korean_spacing.cache_clear()
    original = "환경을제공한다"
    spaced = reconstructor._restore_korean_spacing(original)
    assert spaced == "환경을 제공한다"
    assert spaced.replace(" ", "") == original


# korean spacing rejects content mutation 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_spacing_rejects_content_mutation(monkeypatch) -> None:
    class Spacer:
        # space 작업을 수행함
        def space(self, text, reset_whitespace=False):
            return "환경을 변경한다"

    monkeypatch.setattr(reconstructor, "_KOREAN_SPACER", Spacer())
    reconstructor._restore_korean_spacing.cache_clear()
    assert reconstructor._restore_korean_spacing("환경을제공한다") == "환경을제공한다"
