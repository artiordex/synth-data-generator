# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_jobs_quality.py
# 경로: apps/api/tests/test_jobs_quality.py
# 목적: 작업 보고서 품질 점수의 측정값 처리를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-29
# 수정일: 2026-09-29
# =============================================================================
from synthetic_api.routes.v1.jobs import _report_quality_score


# 측정된 0점과 이전 형식 대체값을 구분하는지 검증함
def test_report_quality_score_preserves_measured_zero_and_uses_legacy_fallback():
    assert _report_quality_score({'quality_score': 0.0, 'overall_quality': 0.72}) == 0.0
    assert _report_quality_score({'quality_score': None, 'overall_quality': 0.72}) == 0.72
    assert _report_quality_score({}) is None
