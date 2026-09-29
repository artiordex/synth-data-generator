# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_survey_request.py
# 경로: apps/api/tests/test_survey_request.py
# 목적: 설문 위험도 보고 옵션의 요청 호환성을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-29
# 수정일: 2026-09-29
# =============================================================================
import pytest

from synthetic_api.routes.v1.survey import SurveyGenerateRequest, _include_k_anonymity_risk_report


# 신규 옵션과 이전 요청 필드가 함께 동작하는지 검증함
@pytest.mark.parametrize(('values', 'expected'), [
    ({}, True),
    ({'include_k_anonymity_risk_report': False}, False),
    ({'include_k_anonymity_risk_report': True}, True),
    ({'protect_k_anonymity': False}, False),
    ({'protect_k_anonymity': True}, True),
    ({'include_k_anonymity_risk_report': False, 'protect_k_anonymity': True}, False),
])
def test_survey_risk_report_option_keeps_legacy_request_compatibility(values, expected):
    request = SurveyGenerateRequest(file_names=['first.csv', 'second.csv'], **values)
    assert _include_k_anonymity_risk_report(request) is expected
