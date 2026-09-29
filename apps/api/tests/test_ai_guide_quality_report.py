# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ai_guide_quality_report.py
# 경로: apps/api/tests/test_ai_guide_quality_report.py
# 목적: AI 가이드 품질 점수의 미측정 상태 보존을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-29
# 수정일: 2026-09-29
# =============================================================================
import pytest

from synthetic_api.routes.v1.ai_guide import (
    _format_measured_completeness_score,
    _measured_ai_readiness_score,
)


# 품질 보고서가 실제 측정값만 표시하는지 검증함
@pytest.mark.parametrize(('score', 'expected'), [
    (94.25, '94.2%'),
    (0, '0.0%'),
    (None, '미측정'),
    (float('nan'), '미측정'),
    (101, '미측정'),
    (True, '미측정'),
])
def test_quality_report_does_not_invent_a_completeness_score(score, expected):
    assert _format_measured_completeness_score(score) == expected


# 준비도 점수가 미측정 상태를 보존하는지 검증함
@pytest.mark.parametrize(('metrics', 'expected'), [
    ([{'category': 'COMPLETENESS', 'score': 94.25}], 94.25),
    ([{'category': 'COMPLETENESS', 'score': 0}], 0.0),
    ([{'category': 'COMPLETENESS', 'score': None}], None),
    ([{'category': 'VALIDITY', 'score': 90}], None),
    ([{'category': 'COMPLETENESS', 'score': float('nan')}], None),
])
def test_readiness_score_preserves_unmeasured_state(metrics, expected):
    assert _measured_ai_readiness_score(metrics) == expected
