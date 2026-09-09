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
    from synthetic_engine import get_synthesizer
    plan = build_column_plan({}, sample_df)
    sampler = get_synthesizer("statistical")
    sampler.fit(sample_df, plan)
    synthetic_df = sampler.sample(50)

    eval_res = evaluate(sample_df, synthetic_df, plan, qbins=10, run_anonymeter_eval=False)
    assert "safety" in eval_res
    assert "utility" in eval_res
    assert "assessment" in eval_res
    assert "correlation" in eval_res["utility"]
    assert "dcr" in eval_res["safety"]
    assert eval_res['assessment']['score'] is None
    assert eval_res['assessment']['overall_status'] == 'REVIEW'

def test_synthesizer_registry_and_persistence(tmp_path, sample_df):
    from synthetic_engine import get_synthesizer, list_synthesizers, BaseSynthesizer
    available = list_synthesizers()
    assert "statistical" in available
    assert "gaussian_copula" in available

    plan = build_column_plan({}, sample_df)
    sampler = get_synthesizer("statistical")
    sampler.fit(sample_df, plan)
    sampled = sampler.sample(20)
    assert len(sampled) == 20

    # Test save and load
    save_path = tmp_path / "model.pkl"
    sampler.save(save_path)
    assert save_path.exists()

    loaded = BaseSynthesizer.load(save_path)
    re_sampled = loaded.sample(10)
    assert len(re_sampled) == 10

def test_privacy_guardrails_deduplication(sample_df):
    from synthetic_engine import PrivacyGuardrails
    # create synthetic with duplicate
    synthetic = sample_df.head(10).copy()
    filtered, report = PrivacyGuardrails.filter_exact_duplicates(sample_df, synthetic)
    assert report["exact_duplicates_found"] == 10
    assert report["status"] in ["PASS", "REVIEW", "FAIL"]

def test_correlation_evaluator(sample_df):
    from synthetic_engine import CorrelationEvaluator
    plan = build_column_plan({}, sample_df)
    res = CorrelationEvaluator.evaluate_correlations(sample_df, sample_df, plan)
    assert res["overall_correlation_score"] >= 0.99
    assert res["status"] == "PASS"

def test_cramers_v_all_pairs():
    from synthetic_engine import CorrelationEvaluator, ColumnPlan
    # 6 categorical columns -> 6 * 5 / 2 = 15 pairs
    df = pd.DataFrame({
        "cat1": ["A", "B", "C", "D"] * 10,
        "cat2": ["X", "Y", "Z", "W"] * 10,
        "cat3": ["1", "2", "1", "2"] * 10,
        "cat4": ["P", "Q", "R", "S"] * 10,
        "cat5": ["M", "N", "O", "P"] * 10,
        "cat6": ["Alpha", "Beta", "Gamma", "Delta"] * 10,
    })
    plan = ColumnPlan(
        categorical=list(df.columns),
        numerical=[],
        ignored=[],
        pii={},
        rules={}
    )
    res = CorrelationEvaluator.evaluate_correlations(df, df, plan)
    assert res["categorical_pairs_evaluated"] == 15
    assert res["categorical_association_score"] >= 0.99

def test_extended_pii_detection_and_faker():
    from synthetic_engine import scan_pii_columns, build_column_plan, build_pii_output
    df = pd.DataFrame({
        "여권번호": ["M12345678"] * 20,
        "사업자등록번호": ["123-45-67890"] * 20,
        "자동차등록번호": ["12가 3456"] * 20,
        "접속IP": ["192.168.0.1"] * 20,
        "신용카드번호": ["1234-5678-9012-3456"] * 20,
        "운전면허번호": ["11-12-345678-90"] * 20,
        "외국인등록번호": ["950101-5123456"] * 20,
        "일반컬럼": ["데이터"] * 20,
    })
    detected = scan_pii_columns(df)
    assert "여권번호" in detected and detected["여권번호"]["faker"] == "passport"
    assert "사업자등록번호" in detected and detected["사업자등록번호"]["faker"] == "business_number"
    assert "자동차등록번호" in detected and detected["자동차등록번호"]["faker"] == "car_plate"
    assert "접속IP" in detected and detected["접속IP"]["faker"] == "ip_address"
    assert "신용카드번호" in detected and detected["신용카드번호"]["faker"] == "credit_card"
    assert "운전면허번호" in detected and detected["운전면허번호"]["faker"] == "driver_license"
    assert "외국인등록번호" in detected and detected["외국인등록번호"]["faker"] == "foreigner_id"
    assert "일반컬럼" not in detected

    plan = build_column_plan({}, df)
    synth_df, report = build_pii_output(df, df.copy(), plan, seed=42)
    # Check that synthetic values are generated and anonymized
    assert synth_df["여권번호"].iloc[0] != "M12345678" or synth_df["여권번호"].nunique() > 1
    assert synth_df["사업자등록번호"].iloc[0] != "123-45-67890" or synth_df["사업자등록번호"].nunique() > 1
    assert synth_df["접속IP"].iloc[0] != "192.168.0.1" or synth_df["접속IP"].nunique() > 1


def test_smart_mask_pii_output_preserves_original_column_order():
    from synthetic_engine import build_pii_output

    raw = pd.DataFrame({
        "지역": ["세종", "충남", "전남광주"],
        "학교 소재지": ["세종특별자치시", "충청남도", "광주광역시"],
        "만족도": [5, 4, 3],
    })
    synthetic = pd.DataFrame({
        "지역": ["세종", "충남"],
        "만족도": [4, 5],
    })
    plan = ColumnPlan(
        categorical=["지역"],
        numerical=["만족도"],
        ignored=["학교 소재지"],
        pii={"학교 소재지": {"action": "smart_mask", "faker": "address"}},
        rules={},
    )

    output, report = build_pii_output(raw, synthetic, plan, seed=42)

    assert list(output.columns) == list(raw.columns)
    assert len(output) == len(synthetic)
    assert output["학교 소재지"].notna().all()
    assert report["summary"]["학교 소재지"]["action"] == "mask"


