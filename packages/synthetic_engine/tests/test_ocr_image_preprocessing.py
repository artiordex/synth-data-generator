# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_image_preprocessing.py
# 경로: packages/synthetic_engine/tests/test_ocr_image_preprocessing.py
# 목적: OCR 전처리 이미지 필터링 및 변환 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

import cv2
import numpy as np
import pytest

from synthetic_engine.exporters.ocr_image_preprocessing import (
    _estimate_text_line_height,
    _ocr_upscale_factor,
    deskew_image,
    preprocess_ocr_image,
    remove_table_lines_for_handwriting,
)
from synthetic_engine.exporters.ocr_table_reconstructor import (
    preprocess_ocr_image as legacy_preprocess_ocr_image,
)


# preprocess OCR 인식 이미지 suppresses pale watermark and keeps 어두운 배경 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_preprocess_ocr_image_suppresses_pale_watermark_and_keeps_dark_text() -> None:
    image = np.full((160, 240, 3), 255, dtype=np.uint8)
    cv2.circle(image, (185, 78), 42, (224, 224, 224), 8)
    cv2.putText(image, "OCR", (24, 92), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    binary = preprocess_ocr_image(image, return_binary=True)

    assert binary.shape[0] >= image.shape[0]
    assert binary[round(78 * binary.shape[0] / image.shape[0]), round(185 * binary.shape[1] / image.shape[1])] == 0
    assert np.count_nonzero(binary > 0) > 20


# legacy reconstructor reexports preprocess function 기능의 정상 동작 및 제약조건을 테스트함
def test_legacy_reconstructor_reexports_preprocess_function() -> None:
    assert legacy_preprocess_ocr_image is preprocess_ocr_image


# 텍스트 높이 and upscale factor use connected components 기능의 정상 동작 및 제약조건을 테스트함
def test_text_height_and_upscale_factor_use_connected_components() -> None:
    image = np.full((80, 160), 255, dtype=np.uint8)
    cv2.putText(image, "Hi", (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 1)

    assert _estimate_text_line_height(image) > 0
    assert _ocr_upscale_factor(image) == 3.0


# deskew 이미지 returns original when angle is out of range 기능의 정상 동작 및 제약조건을 테스트함
def test_deskew_image_returns_original_when_angle_is_out_of_range() -> None:
    image = np.full((120, 220, 3), 255, dtype=np.uint8)
    cv2.line(image, (25, 95), (195, 25), (0, 0, 0), 3)

    result, angle = deskew_image(image, max_angle=1.0)

    assert angle == 0.0
    assert result is image


# remove 표(테이블) lines preserves non 변환 규칙 strokes 기능의 정상 동작 및 제약조건을 테스트함
def test_remove_table_lines_preserves_non_rule_strokes() -> None:
    image = np.full((150, 220), 255, dtype=np.uint8)
    cv2.line(image, (15, 55), (205, 55), 0, 2)
    cv2.line(image, (80, 18), (80, 132), 0, 2)
    cv2.putText(image, "7", (105, 98), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.4, 0, 2)

    cleaned = remove_table_lines_for_handwriting(image, (10, 10, 210, 140), dpi=300)

    assert np.mean(cleaned[55, 18:75] < 128) <= 0.05
    assert np.count_nonzero(cleaned[70:112, 100:145] < 128) > 10


# remove 표(테이블) lines rejects invalid 바운딩 박스 기능의 정상 동작 및 제약조건을 테스트함
def test_remove_table_lines_rejects_invalid_bbox() -> None:
    with pytest.raises(ValueError, match="does not intersect"):
        remove_table_lines_for_handwriting(np.full((20, 20), 255, dtype=np.uint8), (30, 30, 40, 40))
