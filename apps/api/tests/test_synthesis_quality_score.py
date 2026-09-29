# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_synthesis_quality_score.py
# 경로: apps/api/tests/test_synthesis_quality_score.py
# 목적: 합성 품질 점수의 실제 측정 및 정규화를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-29
# 수정일: 2026-09-29
# =============================================================================
import pytest

from synthetic_api.application.services.synthesis_service import _validated_quality_score


# 유효한 측정값과 잘못된 품질 점수를 구분하는지 검증함
@pytest.mark.parametrize(('report', 'expected'), [
    ({'overall_quality': 0.93}, 0.93),
    ({}, None),
    ({'overall_quality': None}, None),
    ({'overall_quality': float('nan')}, None),
    ({'overall_quality': 1.01}, None),
    ({'overall_quality': True}, None),
])
def test_quality_score_is_measured_and_normalized(report, expected):
    assert _validated_quality_score(report) == expected
