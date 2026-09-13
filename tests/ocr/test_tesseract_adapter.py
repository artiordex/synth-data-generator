# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_tesseract_adapter.py
# 경로: tests/ocr/test_tesseract_adapter.py
# 목적: Tesseract OCR 엔진 연동 어댑터를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Adapter regression tests without a native executable."""

from types import SimpleNamespace

import numpy as np
import pytest

from ocr.engine.base import crop_region
from ocr.engine.tesseract import TesseractBackend
from ocr.pipeline.models import PreprocessedImage, PreprocessingConfig, PreprocessingProfile


# line boundaries and region 기하 좌표 기능의 정상 동작 및 제약조건을 테스트함
def test_line_boundaries_and_region_coordinates():
    """TSV line ids and cropped-word offsets survive adapter mapping."""
    data = {
        "text": ["one", "two", "three"], "conf": [90, 85, 50],
        "left": [1, 20, 1], "top": [2, 2, 30],
        "width": [10, 10, 10], "height": [8, 8, 8],
        "block_num": [1, 1, 1], "par_num": [1, 1, 1], "line_num": [1, 1, 2],
    }
    backend = object.__new__(TesseractBackend)
    backend.language = "eng"
    backend.timeout_seconds = 60.0
    backend._pytesseract = SimpleNamespace(
        Output=SimpleNamespace(DICT="dict"), image_to_data=lambda *args, **kwargs: data,
    )
    image = PreprocessedImage(
        image=np.full((200, 200), 255, dtype=np.uint8),
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=200, height_px=200, applied_steps=(),
    )
    result = backend.recognize_region(image, (50, 60, 100, 100), page_no=7)
    assert result.raw_text == "one two\nthree"
    assert result.words[0].bbox.x == 51
    assert result.words[0].bbox.y == 62
    assert result.low_confidence_regions[0].page_no == 7
    assert result.low_confidence_regions[0].bbox.y == 90


# region clipping does not expand requested area 기능의 정상 동작 및 제약조건을 테스트함
def test_region_clipping_does_not_expand_requested_area():
    """Negative origins clip at the image boundary without shifting the end."""
    image = PreprocessedImage(
        image=np.zeros((20, 20), dtype=np.uint8),
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=20, height_px=20, applied_steps=(),
    )
    assert crop_region(image, (-5, -4, 10, 10)).shape == (6, 5)
    with pytest.raises(ValueError, match="intersect"):
        crop_region(image, (30, 30, 10, 10))
