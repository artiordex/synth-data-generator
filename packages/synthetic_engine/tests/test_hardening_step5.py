# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from synthetic_engine.privacy.guardrails import evaluate_subspace_dcr


def test_subspace_dcr_numeric_qi():
    raw = pd.DataFrame({"age": np.arange(20), "income": np.arange(20) * 10})
    synthetic = pd.DataFrame({"age": np.arange(20) + 100, "income": np.arange(20) * 10 + 1000})

    result = evaluate_subspace_dcr(raw, synthetic, ["age"], random_state=42)
    assert result["status"] in {"PASS", "REVIEW", "FAIL"}
    assert result["sample_size_raw"] == 20
    assert result["dcr_median"] is not None


def test_subspace_dcr_categorical_qi():
    raw = pd.DataFrame({"region": ["A", "B", "C"] * 10})
    synthetic = pd.DataFrame({"region": ["A", "B", "C"] * 10})

    result = evaluate_subspace_dcr(raw, synthetic, ["region"])
    assert result["exact_qi_match_rate"] == 1.0
    assert result["status"] == "FAIL"


def test_subspace_dcr_mixed_qi():
    raw = pd.DataFrame({"age": np.arange(30), "region": ["A", "B", "C"] * 10})
    synthetic = pd.DataFrame({"age": np.arange(30) + .5, "region": ["A", "B", "C"] * 10})

    result = evaluate_subspace_dcr(raw, synthetic, ["age", "region"])
    assert result["qi_columns"] == ["age", "region"]
    assert result["dcr_p05"] is not None


def test_subspace_dcr_detects_near_clone_risk():
    raw = pd.DataFrame({"age": np.arange(50, dtype=float), "region": ["A", "B"] * 25})
    synthetic = raw.iloc[:10].copy()

    result = evaluate_subspace_dcr(raw, synthetic, ["age", "region"])
    assert result["exact_qi_match_rate"] == 1.0
    assert result["status"] == "FAIL"


def test_subspace_dcr_holdout_baseline():
    train = pd.DataFrame({"age": np.arange(30, dtype=float)})
    holdout = pd.DataFrame({"age": np.arange(30, 60, dtype=float)})
    synthetic = pd.DataFrame({"age": np.arange(0, 10, dtype=float)})

    result = evaluate_subspace_dcr(train, synthetic, ["age"], raw_holdout=holdout)
    assert result["relative_privacy_risk"] is not None
    assert result["holdout_dcr_median"] is not None


def test_subspace_dcr_failure_is_not_safe():
    result = evaluate_subspace_dcr(
        pd.DataFrame({"age": [1]}),
        pd.DataFrame({"age": [1]}),
        ["missing"],
    )
    assert result["status"] == "NOT_EVALUATED"
    assert result.get("safe") is not True


def test_subspace_dcr_is_reproducible():
    raw = pd.DataFrame({"age": np.arange(100, dtype=float)})
    synthetic = pd.DataFrame({"age": np.arange(100, dtype=float) + .25})

    first = evaluate_subspace_dcr(raw, synthetic, ["age"], sample_size=20, random_state=9)
    second = evaluate_subspace_dcr(raw, synthetic, ["age"], sample_size=20, random_state=9)
    assert first == second
