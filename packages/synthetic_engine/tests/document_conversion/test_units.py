# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_units.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_units.py
# 목적: 문서 물리 단위(pt, px, mm, emu) 상호 변환을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Point conversion invariants and malformed numeric inputs."""

import pytest

from synthetic_engine.document_conversion.core import units


# exact unit definitions and fractional roundtrip 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize(
    ("to_pt", "from_pt", "one_inch"),
    [
        (units.inch_to_pt, units.pt_to_inch, 1),
        (units.hwpunit_to_pt, units.pt_to_hwpunit, 7200),
        (units.emu_to_pt, units.pt_to_emu, 914400),
        (units.twip_to_pt, units.pt_to_twip, 1440),
    ],
)
def test_exact_unit_definitions_and_fractional_roundtrip(to_pt, from_pt, one_inch):
    assert to_pt(one_inch) == 72
    for value in (0, 0.12345, -4.5, 100000.125):
        assert to_pt(from_pt(value)) == pytest.approx(value)


# nonfinite units fail 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000])
def test_nonfinite_units_fail(value):
    with pytest.raises(ValueError, match="finite"):
        units.hwpunit_to_pt(value)


# non numeric units fail 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("value", [True, "72", None])
def test_non_numeric_units_fail(value):
    with pytest.raises(TypeError):
        units.pt_to_emu(value)


# unit multiplication cannot overflow silently 기능의 정상 동작 및 제약조건을 테스트함
def test_unit_multiplication_cannot_overflow_silently():
    with pytest.raises(ValueError, match="finite"):
        units.pt_to_emu(1e308)
