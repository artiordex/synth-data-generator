# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_phase2_improvements.py
# 경로: tests/ocr/test_phase2_improvements.py
# 목적: OCR 고도화 2단계 개선 항목 및 정밀 인식 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ocr.dataset.comparison import build_phase2_comparison, render_phase2_comparison_markdown
from ocr.engine.rapidocr_korean import RapidOCRKoreanBackend
from ocr.pipeline.models import BoundingBox, OCRWord
from ocr.text.layout import cluster_words_into_lines, merge_touching_fragments, render_lines
from ocr.text.normalization import normalize_ocr_text, normalize_structured_token


# word 작업을 수행함
def _word(text: str, x: int, y: int = 10, width: int = 10, height: int = 10) -> OCRWord:
    return OCRWord(text, 0.95, BoundingBox(x, y, width, height))


# gap based layout preserves real spaces and joins fragments 기능의 정상 동작 및 제약조건을 테스트함
def test_gap_based_layout_preserves_real_spaces_and_joins_fragments():
    words = [_word("가", 10), _word("나", 22), _word("다", 60)]
    lines = cluster_words_into_lines(words)
    merged = merge_touching_fragments(lines)
    assert render_lines(merged) == "가나 다"


# layout tolerates y axis jitter 기능의 정상 동작 및 제약조건을 테스트함
def test_layout_tolerates_y_axis_jitter():
    lines = cluster_words_into_lines([_word("가", 10, 10), _word("나", 25, 13), _word("다", 10, 40)])
    assert len(lines) == 2
    assert [word.text for word in lines[0]] == ["가", "나"]


# structured normalization is conservative 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_normalization_is_conservative():
    assert normalize_structured_token("2026. O9. 0I") == "2026.09.01"
    assert normalize_structured_token("1, 00O원") == "1,000원"
    assert normalize_structured_token("홍길동(O담당)") == "홍길동(O담당)"
    assert normalize_ocr_text("가  나\n\n다") == "가  나\n\n다"


# phase2 comparison reports target and error deltas 기능의 정상 동작 및 제약조건을 테스트함
def test_phase2_comparison_reports_target_and_error_deltas():
    before = {
        "metrics": {"bbox_iou": 0.70, "detection_match_rate": 0.84, "exact_text_match_rate": 0.4},
        "numeric_date_amount_accuracy": {"date": {"accuracy": 0.43}},
        "whitespace_preservation_accuracy": {"accuracy": 0.14},
        "error_distribution": {"counts": {"character_deletion": 100, "missing_text": 80}},
    }
    after = {
        "metrics": {"bbox_iou": 0.86, "detection_match_rate": 0.96, "exact_text_match_rate": 0.5},
        "numeric_date_amount_accuracy": {"date": {"accuracy": 0.86}},
        "whitespace_preservation_accuracy": {"accuracy": 0.81},
        "error_distribution": {"counts": {"character_deletion": 40, "missing_text": 20}},
    }
    report = build_phase2_comparison(before, after)
    assert report["targets"]["bbox_iou"]["status"] is True
    assert report["targets"]["character_deletion_reduction"]["status"] is True
    assert "## Target Status" in render_phase2_comparison_markdown(report)


# rapidocr detection tuning is configurable 기능의 정상 동작 및 제약조건을 테스트함
def test_rapidocr_detection_tuning_is_configurable(monkeypatch):
    monkeypatch.setenv("OCR_DET_BOX_THRESH", "0.31")
    monkeypatch.setenv("OCR_DET_TEXT_THRESH", "0.18")
    monkeypatch.setenv("OCR_DET_UNCLIP_RATIO", "1.9")
    monkeypatch.setenv("OCR_DET_LIMIT_SIDE_LEN", "1024")
    backend = RapidOCRKoreanBackend(reader=SimpleNamespace())
    assert backend.det_box_thresh == 0.31
    assert backend.det_text_thresh == 0.18
    assert backend.det_unclip_ratio == 1.9
    assert backend.det_limit_side_len == 1024
    assert backend.input_padding == 0
