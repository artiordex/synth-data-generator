# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_image_conversion.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_image_conversion.py
# 목적: 이미지 기반 문서 변환 파이프라인을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from types import SimpleNamespace

from PIL import Image

from synthetic_engine.document_conversion.pipeline import convert_document
from synthetic_engine.document_conversion.parsers.image_parser import ImageParser
from synthetic_engine.document_conversion.registry import PARSER_REGISTRY, detect_format


# 감지 format 이미지 magic bytes 기능의 정상 동작 및 제약조건을 테스트함
def test_detect_format_image_magic_bytes(tmp_path):
    samples = {
        "png_as_txt.txt": b"\x89PNG\r\n\x1a\n\x00\x00fixture",
        "jpg_as_bin.bin": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00fixture",
        "jpeg_as_dat.dat": b"\xff\xd8\xff\xe1\x00\x18Exif\x00\x00fixture",
        "tiff_little.csv": b"II*\x00\x08\x00\x00\x00fixture",
        "tiff_big.md": b"MM\x00*\x00\x00\x00\x08fixture",
        "bmp.hwpx": b"BM\x36\x00\x00\x00\x00\x00\x00\x00fixture",
        "webp.pdf": b"RIFF\x1a\x00\x00\x00WEBPVP8 fixture",
        "heic.docx": b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00fixture",
        "mif1.xlsx": b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00fixture",
    }

    for name, payload in samples.items():
        path = tmp_path / name
        path.write_bytes(payload)
        assert detect_format(path) == "image"


# 이미지 parser is registered 기능의 정상 동작 및 제약조건을 테스트함
def test_image_parser_is_registered():
    assert PARSER_REGISTRY["image"] == ("image_parser", "ImageParser")


# convert 이미지 to 마크다운 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_convert_image_to_markdown_text(monkeypatch, tmp_path):
    source = tmp_path / "scan.png"
    Image.new("RGB", (240, 120), "white").save(source)

    # fake process 작업을 수행함
    def fake_process(_image, page_num):
        return SimpleNamespace(
            text_blocks=[
                SimpleNamespace(text="식약처 이미지 텍스트", is_heading=True),
                SimpleNamespace(text="OCR 본문 변환", is_heading=False),
            ],
            tables=[],
            figures=[],
            warnings=[],
        )

    import synthetic_engine.exporters.ocr_table_reconstructor as reconstructor

    monkeypatch.setattr(reconstructor, "process_scanned_page", fake_process)
    output = convert_document(source, "md", output_dir=tmp_path)

    text = output.read_text(encoding="utf-8")
    assert "식약처 이미지 텍스트" in text
    assert "OCR 본문 변환" in text


# 이미지 parser records OCR 인식 failure for 품질 gate 기능의 정상 동작 및 제약조건을 테스트함
def test_image_parser_records_ocr_failure_for_quality_gate(monkeypatch, tmp_path):
    source = tmp_path / "failed-scan.png"
    Image.new("RGB", (120, 60), "white").save(source)

    import synthetic_engine.exporters.ocr_table_reconstructor as reconstructor

    monkeypatch.setattr(
        reconstructor,
        "process_scanned_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("local model unavailable")),
    )
    document = ImageParser().parse(source)

    assert document.metadata.custom["ocr_status_p1"] == "failed"
    assert "local model unavailable" in document.metadata.custom["ocr_error_p1"]
    assert any(warning.code == "IMAGE_OCR_FAILED" for warning in document.warnings)
    assert document.sections[0].elements
