# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_korean_quality.py
# 경로: tests/ocr/test_korean_quality.py
# 목적: 한국어 OCR 텍스트 정규화 및 품질 검증 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from dataclasses import dataclass

import pytest

from ocr.text.korean_quality import (
    is_ocr_noise_text,
    korean_quality_score,
    needs_secondary_check,
    ocr_candidate_score,
    ocr_result_quality,
    special_character_ratio,
)


@dataclass(frozen=True)
class Candidate:
    text: str
    confidence: float


# korean 품질 prefers meaningful document 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_quality_prefers_meaningful_document_text() -> None:
    broken = "곡 극이료 수서위요 더무가지 동격이이금는"
    meaningful = "데이터 발굴의 배경과 필요성 등이 적절한가"

    assert korean_quality_score(meaningful) > korean_quality_score(broken)
    assert ocr_candidate_score(meaningful, 0.62) > ocr_candidate_score(broken, 0.86)


# high 인식 신뢰도 implausible hangul requires secondary check 기능의 정상 동작 및 제약조건을 테스트함
def test_high_confidence_implausible_hangul_requires_secondary_check() -> None:
    assert needs_secondary_check("이궁뚝용융여무", 0.93)
    assert not needs_secondary_check("구분", 0.93)


# 노이즈 and supported symbols are stable 기능의 정상 동작 및 제약조건을 테스트함
def test_noise_and_supported_symbols_are_stable() -> None:
    assert is_ocr_noise_text("................................")
    assert not is_ocr_noise_text("공유 데이터")
    assert special_character_ratio("용량 5㎎/㎖, 면적 12㎡, 온도 25℃ ※ 확인") == pytest.approx(0.0)


# 결과 품질 combines 인식 신뢰도 품질 and coverage 기능의 정상 동작 및 제약조건을 테스트함
def test_result_quality_combines_confidence_quality_and_coverage() -> None:
    weak = [
        Candidate("이궁뚝용융여무", 0.95),
        Candidate("곡 극이료 수서위요", 0.90),
    ]
    improved = [
        Candidate("평가 착안사항", 0.78),
        Candidate("데이터 발굴의 배경과 필요성", 0.65),
        Candidate("공유 데이터 제공 노력", 0.72),
    ]

    assert ocr_result_quality(improved) > ocr_result_quality(weak)

