# -*- coding: utf-8 -*-
import pytest
import numpy as np
import pandas as pd
from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.quality.assessment import compute_column_distributions, evaluate

def test_compute_column_distributions():
    np.random.seed(42)
    n = 200
    
    orig = pd.DataFrame({
        "age": np.random.randint(20, 70, size=n),
        "amount": np.random.normal(50000, 15000, size=n).round(-2),
        "gender": np.random.choice(["남", "여"], size=n, p=[0.45, 0.55]),
        "tier": np.random.choice(["BRONZE", "SILVER", "GOLD"], size=n, p=[0.6, 0.3, 0.1]),
    })

    # Slight variation for synthetic
    synth = pd.DataFrame({
        "age": np.random.randint(21, 69, size=n),
        "amount": np.random.normal(50500, 14800, size=n).round(-2),
        "gender": np.random.choice(["남", "여"], size=n, p=[0.46, 0.54]),
        "tier": np.random.choice(["BRONZE", "SILVER", "GOLD"], size=n, p=[0.58, 0.31, 0.11]),
    })

    plan = ColumnPlan(
        categorical=["gender", "tier"],
        numerical=["age", "amount"],
        ignored=[],
        pii={},
        rules={}
    )

    dists = compute_column_distributions(orig, synth, plan, n_bins=10)
    assert len(dists) == 4

    # Test numerical column
    age_dist = next(d for d in dists if d["name"] == "age")
    assert age_dist["type"] == "numerical"
    assert "jsd" in age_dist
    assert age_dist["similarity_pct"] > 80.0
    assert len(age_dist["bins"]) == 10
    assert "mean" in age_dist["stats"]["original"]
    assert "mean" in age_dist["stats"]["synthetic"]

    # Test sum of percentages
    orig_sum = sum(b["original_pct"] for b in age_dist["bins"])
    synth_sum = sum(b["synthetic_pct"] for b in age_dist["bins"])
    assert 98.0 <= orig_sum <= 102.0
    assert 98.0 <= synth_sum <= 102.0

    # Test categorical column
    tier_dist = next(d for d in dists if d["name"] == "tier")
    assert tier_dist["type"] == "categorical"
    assert len(tier_dist["bins"]) == 3
    assert tier_dist["stats"]["original"]["unique"] == 3
    assert tier_dist["stats"]["synthetic"]["unique"] == 3

def test_evaluate_includes_distributions():
    np.random.seed(42)
    n = 50
    orig = pd.DataFrame({
        "x": np.random.uniform(0, 10, size=n),
        "cat": np.random.choice(["A", "B"], size=n)
    })
    synth = pd.DataFrame({
        "x": np.random.uniform(0, 10, size=n),
        "cat": np.random.choice(["A", "B"], size=n)
    })
    plan = ColumnPlan(categorical=["cat"], numerical=["x"], ignored=[], pii={}, rules={})

    res = evaluate(orig, synth, plan, run_anonymeter_eval=False)
    assert "column_distributions" in res
    assert len(res["column_distributions"]) == 2
    assert "column_distributions" in res["utility"]
