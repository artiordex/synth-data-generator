# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_temporal_constraints.py
# 경로: packages/synthetic_engine/tests/test_temporal_constraints.py
# 목적: 시계열 시간 순서 및 논리 제약조건 보존을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pandas as pd

from synthetic_engine import DummyDataGenerator
from synthetic_engine.preprocessing.transformer import (
    apply_constraints_after_generation,
    infer_temporal_constraints,
)


# date order repairs reversed lifecycle dates 기능의 정상 동작 및 제약조건을 테스트함
def test_date_order_repairs_reversed_lifecycle_dates():
    frame = pd.DataFrame({
        "입사일": ["2024-05-01", "20240501"],
        "퇴사일": ["2024-04-01", "20240401"],
    })

    repaired = apply_constraints_after_generation(frame, [{
        "type": "date_order",
        "before_column": "입사일",
        "after_column": "퇴사일",
        "min_days": 1,
    }])

    assert repaired["퇴사일"].tolist() == ["2024-05-02", "20240502"]


# age 변환 규칙 repairs birth date against reference date 기능의 정상 동작 및 제약조건을 테스트함
def test_age_rule_repairs_birth_date_against_reference_date():
    frame = pd.DataFrame({
        "생년월일": ["2010-01-01", "1890-01-01"],
        "입사일": ["2024-01-01", "2024-01-01"],
    })

    repaired = apply_constraints_after_generation(frame, [{
        "type": "age_at_least",
        "birth_column": "생년월일",
        "reference_column": "입사일",
        "min_years": 15,
        "max_years": 120,
    }])

    assert repaired["생년월일"].tolist() == ["2009-01-01", "1904-01-01"]


# age 변환 규칙 ignores 행 목록 with missing reference date 기능의 정상 동작 및 제약조건을 테스트함
def test_age_rule_ignores_rows_with_missing_reference_date():
    frame = pd.DataFrame({"생년월일": ["2010-01-01"], "입사일": [None]})

    repaired = apply_constraints_after_generation(frame, [{
        "type": "age_at_least",
        "birth_column": "생년월일",
        "reference_column": "입사일",
        "min_years": 15,
    }])

    assert repaired.loc[0, "생년월일"] == "2010-01-01"


# existing inequality constraint handles date strings 기능의 정상 동작 및 제약조건을 테스트함
def test_existing_inequality_constraint_handles_date_strings():
    frame = pd.DataFrame({"start": ["2024-05-01"], "end": ["2024-04-01"]})

    repaired = apply_constraints_after_generation(frame, [{
        "type": "greater_than",
        "low_column": "start",
        "high_column": "end",
    }])

    assert repaired.loc[0, "end"] == "2024-05-01"


# temporal constraints are inferred for common korean 컬럼 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_temporal_constraints_are_inferred_for_common_korean_columns():
    frame = pd.DataFrame({
        "생년월일": ["2000-01-01"],
        "입사일": ["2024-01-01"],
        "퇴사일": ["2023-01-01"],
        "가입일": ["2024-03-01"],
        "탈퇴일": ["2024-02-01"],
    })

    inferred = infer_temporal_constraints(frame)
    pairs = {
        (rule.get("type"), rule.get("before_column"), rule.get("after_column"))
        for rule in inferred
    }
    age_refs = {
        (rule.get("birth_column"), rule.get("reference_column"), rule.get("min_years"))
        for rule in inferred
        if rule.get("type") == "age_at_least"
    }

    assert ("date_order", "입사일", "퇴사일") in pairs
    assert ("date_order", "가입일", "탈퇴일") in pairs
    assert ("생년월일", "입사일", 15) in age_refs


# 더미 데이터 generator repairs temporal 컬럼 목록 in normal scenario 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_generator_repairs_temporal_columns_in_normal_scenario():
    columns = [
        {"name": "생년월일", "rule": {"type": "date_between", "start": "2010-01-01", "end": "2010-01-01"}},
        {"name": "입사일", "rule": {"type": "date_between", "start": "2024-01-01", "end": "2024-01-01"}},
        {"name": "퇴사일", "rule": {"type": "date_between", "start": "2023-01-01", "end": "2023-01-01"}},
    ]

    generated = DummyDataGenerator(seed=7).generate(columns, 3)

    assert generated["생년월일"].tolist() == ["2009-01-01"] * 3
    assert generated["퇴사일"].tolist() == ["2024-01-01"] * 3
