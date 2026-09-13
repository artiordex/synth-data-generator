# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_capabilities.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_capabilities.py
# 목적: 포맷별 변환 기능 지원 여부 매트릭스를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Capability declarations must not invent implementation support."""

import pytest

from synthetic_engine.document_conversion.core.capabilities import TargetCapabilities


# default capabilities do not claim renderer support 기능의 정상 동작 및 제약조건을 테스트함
def test_default_capabilities_do_not_claim_renderer_support():
    capabilities = TargetCapabilities()
    assert capabilities.unsupported_features(
        ["supports_pages", "supports_rowspan", "supports_pages"]
    ) == ("supports_pages", "supports_rowspan")


# only declared native features are supported 기능의 정상 동작 및 제약조건을 테스트함
def test_only_declared_native_features_are_supported():
    capabilities = TargetCapabilities(supports_nested_tables=True, supports_colspan=True)
    assert capabilities.unsupported_features(
        ["supports_colspan", "supports_rowspan", "supports_nested_tables"]
    ) == ("supports_rowspan",)


# unknown feature is an error not silent success 기능의 정상 동작 및 제약조건을 테스트함
def test_unknown_feature_is_an_error_not_silent_success():
    with pytest.raises(ValueError, match="Unknown target capability"):
        TargetCapabilities().unsupported_features(["supports_row_span"])


# string false does not enable a capability 기능의 정상 동작 및 제약조건을 테스트함
def test_string_false_does_not_enable_a_capability():
    with pytest.raises(TypeError, match="boolean"):
        TargetCapabilities(supports_pages="false")
