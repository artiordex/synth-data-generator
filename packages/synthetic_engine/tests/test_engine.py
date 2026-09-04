# -*- coding: utf-8 -*-
import pytest
import numpy as np
import pandas as pd
from synthetic_engine import (
    ColumnPlan,
    SynthesisConfig,
    SyntheticPipeline,
    calculate_sha256,
    detect_system_device,
    infer_columns,
    scan_pii_columns,
    build_column_plan,
    apply_differential_privacy_noise,
    evaluate
)

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "고객ID": [f"U_{i}" for i in range(50)],
        "성명": ["홍길동", "김영희", "이철수", "박지민", "최유진"] * 10,
        "연령": np.random.randint(20, 60, size=50),
        "성별": ["남", "여"] * 25,
        "구매금액": np.random.uniform(10, 200, size=50).round(1),
    })

def test_provenance(sample_df):
    hash_val = calculate_sha256(sample_df)
    assert len(hash_val) == 64
    device = detect_system_device()
    assert "gpu_available" in device

def test_profiling_and_plan(sample_df):
    pii = scan_pii_columns(sample_df)
    assert "성명" in pii
    plan = build_column_plan({}, sample_df)
    assert "연령" in plan.numerical
    assert "성별" in plan.categorical

def test_dp_noise(sample_df):
    perturbed, report = apply_differential_privacy_noise(sample_df, ["구매금액"], epsilon=1.0)
    assert report["enabled"] is True
    assert "구매금액" in report["columns_perturbed"]
    assert len(perturbed) == len(sample_df)

def test_evaluation(sample_df):
    plan = build_column_plan({}, sample_df)
    eval_res = evaluate(sample_df, sample_df, plan, qbins=10, run_anonymeter_eval=False)
    assert "safety" in eval_res
    assert "utility" in eval_res
    assert "assessment" in eval_res
    assert eval_res["assessment"]["score"] >= 80
