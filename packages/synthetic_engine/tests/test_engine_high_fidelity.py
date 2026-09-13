# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_engine_high_fidelity.py
# 경로: packages/synthetic_engine/tests/test_engine_high_fidelity.py
# 목적: 고충실도 합성 데이터 생성 및 상관관계 보존을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import math

import pandas as pd
import pytest

from synthetic_engine import (
    ColumnPlan,
    categorical_tvd,
    compute_composite_quality_score,
    evaluate,
    wasserstein_distance,
    wasserstein_similarity,
)


# wasserstein distance calculation 기능의 정상 동작 및 제약조건을 테스트함
def test_wasserstein_distance_calculation():
    original = pd.Series([0.0, 1.0, 2.0])
    synthetic = pd.Series([1.0, 2.0, 3.0])

    distance = wasserstein_distance(original, synthetic)
    similarity = wasserstein_similarity(original, synthetic)

    assert distance == pytest.approx(1.0)
    assert similarity == pytest.approx(0.5)


# categorical tvd calculation 기능의 정상 동작 및 제약조건을 테스트함
def test_categorical_tvd_calculation():
    original = pd.Series(["A", "A", "B", "C"])
    synthetic = pd.Series(["A", "B", "B", "B"])

    assert categorical_tvd(original, synthetic) == pytest.approx(0.5)


# composite 품질 score 기능의 정상 동작 및 제약조건을 테스트함
def test_composite_quality_score():
    score = compute_composite_quality_score(
        jsd_mean=0.2,
        wasserstein_similarity_mean=0.5,
        correlation_score=0.9,
    )

    assert score == pytest.approx((0.8 * 0.4) + (0.5 * 0.3) + (0.9 * 0.3))


# evaluate reports wasserstein tvd and composite 품질 기능의 정상 동작 및 제약조건을 테스트함
def test_evaluate_reports_wasserstein_tvd_and_composite_quality():
    original = pd.DataFrame({
        "age": [20, 30, 40, 50],
        "cost": [10.0, 20.0, 30.0, 40.0],
        "group": ["A", "A", "B", "C"],
    })
    synthetic = pd.DataFrame({
        "age": [21, 31, 41, 51],
        "cost": [10.0, 22.0, 28.0, 40.0],
        "group": ["A", "B", "B", "B"],
    })
    plan = ColumnPlan(categorical=["group"], numerical=["age", "cost"], ignored=[], pii={}, rules={})

    result = evaluate(original, synthetic, plan, qbins=4, run_anonymeter_eval=False)
    utility = result["utility"]

    assert set(utility["wasserstein_by_column"]) == {"age", "cost"}
    assert set(utility["wasserstein_similarity_by_column"]) == {"age", "cost"}
    assert utility["tvd_by_column"] == {"group": pytest.approx(0.5)}
    assert utility["composite_quality_score"] is not None
    assert math.isfinite(utility["composite_quality_score"])
    assert result["assessment"]["summary"]["composite_quality_score"] == utility["composite_quality_score"]
    assert result["column_distributions"][0]["wasserstein_similarity"] is not None
    assert result["column_distributions"][-1]["tvd"] == pytest.approx(0.5)
