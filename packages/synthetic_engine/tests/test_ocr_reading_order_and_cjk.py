# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_reading_order_and_cjk.py
# 경로: packages/synthetic_engine/tests/test_ocr_reading_order_and_cjk.py
# 목적: CJK 다국어 텍스트 및 다단 읽기 순서 정렬을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from synthetic_engine.exporters import ocr_table_reconstructor as reconstructor
from synthetic_engine.exporters.ocr_table_reconstructor import (
    OCRWord,
    _cluster_words_into_lines,
    _line_text,
    preprocess_ocr_image,
    process_scanned_page,
)


# decoy 이미지 작업을 수행함
def _decoy_image() -> np.ndarray:
    """Create an AhnLab-decoy-like page with CJK paragraphs and a watermark."""
    image = Image.new("RGB", (960, 420), "white")
    draw = ImageDraw.Draw(image)
    font_candidates = (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    )
    font_path = next((path for path in font_candidates if Path(path).is_file()), None)
    font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default()
    draw.text((32, 34), "안내문 첫 번째 행", fill=(0, 0, 0), font=font)
    draw.text((32, 82), "안내문 두 번째 행", fill=(0, 0, 0), font=font)
    draw.text((32, 150), "This Note is a decoy that hides the file name", fill=(0, 0, 0), font=font)
    draw.text((32, 220), "ランサムウェアに関する注意", fill=(0, 0, 0), font=font)
    draw.text((32, 290), "这是一个用于测试的诱饵说明", fill=(0, 0, 0), font=font)
    output = np.asarray(image.convert("RGB"))[:, :, ::-1].copy()
    cv2.circle(output, (820, 220), 72, (220, 220, 220), 14)
    cv2.rectangle(output, (785, 180), (855, 260), (225, 225, 225), 10)
    return output


# korean lines are not zipped and english fragments are joined 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_lines_are_not_zipped_and_english_fragments_are_joined() -> None:
    image = _decoy_image()
    assert image.shape == (420, 960, 3)
    words = [
        OCRWord("2행", (190, 84, 235, 108), 0.98),
        OCRWord("한국어", (32, 84, 145, 108), 0.98),
        OCRWord("1행", (190, 36, 235, 60), 0.98),
        OCRWord("한국어", (32, 36, 145, 60), 0.98),
        OCRWord("mly", (534, 154, 570, 178), 0.95),
        OCRWord("rando", (480, 154, 530, 178), 0.95),
        OCRWord("omware", (624, 154, 682, 178), 0.95),
        OCRWord("rans", (580, 154, 620, 178), 0.95),
    ]
    lines = _cluster_words_into_lines(words)
    assert [_line_text(line) for line in lines[:2]] == ["한국어 1행", "한국어 2행"]
    assert _line_text(lines[2]) == "randomly ransomware"


# normalization does not guess words or change characters 기능의 정상 동작 및 제약조건을 테스트함
def test_normalization_does_not_guess_words_or_change_characters() -> None:
    line = [
        OCRWord("createdby", (10, 10, 120, 30), 0.95),
        OCRWord("subjectto", (140, 10, 250, 30), 0.95),
        OCRWord("filenameis", (270, 10, 390, 30), 0.95),
    ]
    assert _line_text(line) == "createdby subjectto filenameis"
    for raw in ("랜성웨어", "이파일은", "만든디코이", "금액 1,000원"):
        normalized = reconstructor._restore_korean_spacing(raw)
        assert "".join(normalized.split()) == "".join(raw.split())


# 한중일 다국어 텍스트 has no garbage and watermark is suppressed 기능의 정상 동작 및 제약조건을 테스트함
def test_cjk_text_has_no_garbage_and_watermark_is_suppressed(monkeypatch) -> None:
    image = _decoy_image()
    monkeypatch.setattr(
        reconstructor,
        "_run_ocr_on_image",
        lambda _: [
            OCRWord("안내문 첫 번째 행", (32, 34, 250, 60), 0.98),
            OCRWord("안내문 두 번째 행", (32, 82, 250, 108), 0.98),
            OCRWord("ランサムウェアに関する注意", (32, 220, 360, 246), 0.98),
            OCRWord("这是一个用于测试的诱饵说明", (32, 290, 380, 316), 0.98),
        ],
    )
    monkeypatch.setattr(reconstructor, "detect_table_grid_cells", lambda _: [])
    monkeypatch.setattr(reconstructor, "detect_borderless_table_cells", lambda *_: [])
    monkeypatch.setattr(reconstructor, "detect_image_figures", lambda *_: [])

    result = process_scanned_page(image, 1)
    text = result.full_text
    assert "안내문 첫 번째 행\n안내문 두 번째 행" in text
    assert "ランサムウェア" in text
    assert "这是一个用于测试的诱饵说明" in text
    assert not any(character in text for character in "{∠∗")

    binary = preprocess_ocr_image(image, return_binary=True)
    scale_x = binary.shape[1] / image.shape[1]
    scale_y = binary.shape[0] / image.shape[0]
    assert binary[round(148 * scale_y), round(820 * scale_x)] == 0


# low 품질 word is preserved for review 기능의 정상 동작 및 제약조건을 테스트함
def test_low_quality_word_is_preserved_for_review(monkeypatch) -> None:
    image = _decoy_image()
    repaired = reconstructor._repair_low_quality_words(
        image, [OCRWord("Z0{5∠0{", (32, 220, 220, 248), 0.41)]
    )
    assert [word.text for word in repaired] == ["Z0{5∠0{"]
    assert repaired[0].confidence == 0.41


# legacy bridge preserves common backend 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_legacy_bridge_preserves_common_backend_confidence(monkeypatch) -> None:
    from ocr.pipeline.models import (
        BoundingBox,
        OCRPageResult as CommonPageResult,
        OCRWord as CommonWord,
    )

    class LocalBackend:
        name = "test_local"

        # recognize 페이지 작업을 수행함
        def recognize_page(self, image, *, page_no=1):
            return CommonPageResult(
                page_no=page_no,
                raw_text="한국어",
                normalized_text="한국어",
                words=(CommonWord("한국어", 0.42, BoundingBox(3, 4, 20, 8)),),
                mean_confidence=0.42,
                median_confidence=0.42,
            )

    monkeypatch.setattr(reconstructor, "get_ocr_backend", lambda: LocalBackend())
    words = reconstructor._run_ocr_on_image(np.full((40, 80, 3), 255, np.uint8))

    assert words == [OCRWord("한국어", (3, 4, 23, 12), 0.42)]
