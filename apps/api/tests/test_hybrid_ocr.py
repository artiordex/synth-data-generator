# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_hybrid_ocr.py
# 경로: apps/api/tests/test_hybrid_ocr.py
# 목적: 로컬 우선 OCR 품질 진단 게이트 및 스마트 AI 에스컬레이션 로직을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-18
# =============================================================================
"""Unit tests for intelligent local-first OCR quality gate and escalation."""
from __future__ import annotations

from unittest.mock import MagicMock

from synthetic_engine.document_conversion.parsers.image_parser import _evaluate_local_ocr_quality


# 로컬 OCR 결과가 None인 경우 엔진 실패로 진단되는지 검증함
def test_evaluate_local_ocr_quality_none() -> None:
    acceptable, reason, conf = _evaluate_local_ocr_quality(None)
    assert acceptable is False
    assert reason == "ocr_engine_failed"
    assert conf == 0.0


# 텍스트 추출량이 부족한 경우 불합격 판정되는지 검증함
def test_evaluate_local_ocr_quality_insufficient_text() -> None:
    mock_ocr = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "가나다"
    mock_block.confidence = 0.95
    mock_ocr.text_blocks = [mock_block]
    mock_ocr.tables = []
    acceptable, reason, _ = _evaluate_local_ocr_quality(mock_ocr)
    assert acceptable is False
    assert reason == "insufficient_text_extracted"


# 평균 신뢰도가 임계값 미만인 경우 저신뢰도로 진단되는지 검증함
def test_evaluate_local_ocr_quality_low_confidence() -> None:
    mock_ocr = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "식품의약품안전처 의약품 안전 관리 지침 공시 전문"
    mock_block.confidence = 0.52
    mock_ocr.text_blocks = [mock_block]
    mock_ocr.tables = []
    acceptable, reason, conf = _evaluate_local_ocr_quality(mock_ocr)
    assert acceptable is False
    assert "low_confidence" in reason
    assert conf < 0.68


# 정상적인 텍스트와 신뢰도를 만족할 때 로컬 합격 판정되는지 검증함
def test_evaluate_local_ocr_quality_success() -> None:
    mock_ocr = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "식품의약품안전처 의약품 안전 관리 지침 공시 전문"
    mock_block.confidence = 0.92
    mock_ocr.text_blocks = [mock_block]
    mock_ocr.tables = []
    mock_ocr.requires_review = False
    acceptable, reason, conf = _evaluate_local_ocr_quality(mock_ocr)
    assert acceptable is True
    assert reason == "acceptable_quality"
    assert conf >= 0.90


# 높은 신뢰도라도 한글 외계어가 다수 감지되는 경우 불합격 판정되는지 검증함
def test_evaluate_local_ocr_quality_korean_gibberish_rejected() -> None:
    mock_ocr = MagicMock()
    # 실제 스캔본 오인식 외계어 샘플 블록 구성함
    gibberish_texts = [
        "융데위 취유해 ㅎ이를 를이드궁콩연루유들스",
        "수이 |이욕 옮콩 궁이야 능마문로 버없비 극영공",
        "몽에이누형위 등누이가를 군들 글이 극을 계속",
        "ㅋ병이제위급이후이위을 ㄷ헌을기",
    ]
    mock_ocr.text_blocks = [MagicMock(text=t, confidence=0.88, bbox=[10, 10, 200, 30]) for t in gibberish_texts]
    mock_ocr.tables = []
    mock_ocr.requires_review = False
    acceptable, reason, _ = _evaluate_local_ocr_quality(mock_ocr)
    assert acceptable is False
    assert "low_korean_quality" in reason


# 손글씨(Handwriting) 영역이 감지되는 경우 자동 에스컬레이션 판정되는지 검증함
def test_evaluate_local_ocr_quality_handwriting_detected(monkeypatch) -> None:
    import numpy as np

    # is_handwritten_region을 True로 모킹하여 손글씨 필기체 감지 상황을 시뮬레이션함
    monkeypatch.setattr(
        "synthetic_engine.exporters.handwriting_vlm.is_handwritten_region",
        lambda crop, conf: True,
    )

    mock_ocr = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "원두 10kg 확인 완료"
    # 0.68 이상 0.70 미만에서 저신뢰도 필기 감지 분기를 검증함
    mock_block.confidence = 0.69
    mock_block.bbox = [10, 10, 80, 50]
    mock_ocr.text_blocks = [mock_block]
    mock_ocr.tables = []
    mock_ocr.requires_review = False

    dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
    acceptable, reason, _ = _evaluate_local_ocr_quality(mock_ocr, image_bgr=dummy_image)
    assert acceptable is False
    assert "handwriting_detected" in reason
