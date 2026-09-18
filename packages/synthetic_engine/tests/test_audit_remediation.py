# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_audit_remediation.py
# 경로: packages/synthetic_engine/tests/test_audit_remediation.py
# 목적: 심의 검토 결과 반영(12개 데이터셋 규칙, 원본 유일 레코드 복제 차단, DCR/NNDR/CAP, pMSE, 자동 탐색) 단위 테스트
# =============================================================================
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.rules.base import RuleType, ActionType
from synthetic_engine.rules.catalog import (
    resolve_column_name,
    match_dataset_schema,
    get_dataset_catalog,
)
from synthetic_engine.rules.engine import DatasetRuleEngine
from synthetic_engine.rules.discovery import (
    discover_temporal_orders,
    discover_conditional_nulls,
    discover_zero_implications,
    discover_numerical_inequalities,
)
from synthetic_engine.privacy.guardrails import PrivacyGuardrails
from synthetic_engine.quality.utility import (
    compute_pmse,
    evaluate_spearman_correlations,
    evaluate_categorical_associations_with_significance,
    evaluate_comprehensive_utility,
)


# -----------------------------------------------------------------------------
# 1. 시맨틱 컬럼 매퍼 및 카탈로그 테스트
# -----------------------------------------------------------------------------
def test_semantic_column_resolution():
    """다양한 한글·영문 컬럼명 패턴이 표준 컬럼으로 안전하게 매핑되는지 검증"""
    cols = ["신청_일자", "지원_시작_일자", "총_자산_금액", "부동산_가액", "임대_보증금"]
    assert resolve_column_name("신청일자", cols) == "신청_일자"
    assert resolve_column_name("지원시작일자", cols) == "지원_시작_일자"
    assert resolve_column_name("총자산", cols) == "총_자산_금액"
    assert resolve_column_name("부동산자산", cols) == "부동산_가액"
    assert resolve_column_name("보증금", cols) == "임대_보증금"
    assert resolve_column_name("존재하지않는컬럼", cols) is None


def test_schema_matching_by_columns():
    """컬럼 구성을 기반으로 12개 데이터셋 스키마를 올바르게 식별하는지 검증"""
    cols = ["신청일자", "지원시작일자", "총자산", "금융자산", "부동산자산"]
    matched = match_dataset_schema(cols=cols)
    assert matched is not None
    assert matched.dataset_id == "vulnerable_support"


# -----------------------------------------------------------------------------
# 2. 12개 데이터셋 주요 지적사항 업무규칙 보정 테스트
# -----------------------------------------------------------------------------
def test_vulnerable_support_rules():
    """취약계층지원: 총자산 >= 0, 부동산 <= 총자산, 신청일 <= 지원시작일 보정 검증"""
    df = pd.DataFrame({
        "신청일자": ["2024-03-01", "2024-05-10"],
        "지원시작일자": ["2024-02-01", "2024-05-20"],  # 첫 번째 행 모순
        "총자산": [-500, 1000],  # 첫 번째 행 음수 모순
        "부동산자산": [200, 1500],  # 두 행 모두 모순 (부동산 > 총자산)
        "금융자산": [100, 500],
    })

    processed = DatasetRuleEngine.postprocess(df, dataset_name="취약계층지원")

    # 총자산 음수 클리핑 확인
    assert (processed["총자산"] >= 0).all()
    # 부동산자산 <= 총자산 확인
    assert (processed["부동산자산"] <= processed["총자산"]).all()
    # 신청일자 <= 지원시작일자 확인
    dt_app = pd.to_datetime(processed["신청일자"])
    dt_start = pd.to_datetime(processed["지원시작일자"])
    assert (dt_app <= dt_start).all()


def test_youth_rent_rules():
    """청년월세: 입주일자 <= 퇴거일자, 퇴거일자 결측 논리 검증"""
    df = pd.DataFrame({
        "입주일자": ["2023-01-01", "2023-06-01", "2023-09-01"],
        "퇴거일자": ["2022-12-01", "2023-12-01", None],  # 첫 번째 행 모순
        "월세금액": [500000, 600000, 450000],
    })

    processed = DatasetRuleEngine.postprocess(df, dataset_name="청년월세")
    # 입주일자 <= 퇴거일자 (결측 제외)
    valid_mask = processed["입주일자"].notna() & processed["퇴거일자"].notna()
    dt_in = pd.to_datetime(processed.loc[valid_mask, "입주일자"])
    dt_out = pd.to_datetime(processed.loc[valid_mask, "퇴거일자"])
    assert (dt_in <= dt_out).all()


def test_childcare_support_zero_children():
    """보육료지원: 자녀수 0이면 출산경험/출산자녀수 무조건 0 강제 보정 검증"""
    df = pd.DataFrame({
        "자녀수": [0, 0, 2, 0],
        "출산경험여부": ["Y", "1", "Y", "N"],  # 행 0, 1 모순
        "출산자녀수": [1, 2, 2, 0],  # 행 0, 1 모순
    })

    processed = DatasetRuleEngine.postprocess(df, dataset_name="보육료지원")
    zero_mask = processed["자녀수"] == 0
    assert (processed.loc[zero_mask, "출산자녀수"] == 0).all()
    assert (processed.loc[zero_mask, "출산경험여부"].isin(["N", "0", 0])).all()


def test_childcare_helper_age_binning():
    """아이돌봄: 희망돌보미 나이 5세 단위 구간화(익명화/특이값 차단) 검증"""
    df = pd.DataFrame({
        "신청일자": ["2024-01-01", "2024-02-01"],
        "희망돌보미나이": [43, 57],
        "돌봄아동출생년도": [2020, 2022],
    })

    processed = DatasetRuleEngine.postprocess(df, dataset_name="아이돌봄")
    # 43 -> 40, 57 -> 55 (5의 배수 구간화)
    assert processed["희망돌보미나이"].iloc[0] == 40
    assert processed["희망돌보미나이"].iloc[1] == 55


def test_public_rental_arrears_calculation():
    """공공임대: 체납개월수 0이면 체납금액 0, 연체료합계 산식 재계산 검증"""
    df = pd.DataFrame({
        "체납개월수": [0, 3, 0],
        "체납금액": [50000, 300000, 20000],  # 행 0, 2 모순
        "부과금액": [100000, 200000, 150000],
        "연체요율": [0.05, 0.05, 0.05],
        "연체료합계": [0, 0, 0],
    })

    processed = DatasetRuleEngine.postprocess(df, dataset_name="공공임대")
    zero_mask = processed["체납개월수"] == 0
    assert (processed.loc[zero_mask, "체납금액"] == 0).all()
    # 연체료합계 = 부과금액 * 연체요율 재계산 확인
    expected_fee = processed["부과금액"] * processed["연체요율"]
    np.testing.assert_allclose(processed["연체료합계"], expected_fee, rtol=1e-5)


# -----------------------------------------------------------------------------
# 3. 개인정보 안전성 가드레일 (DCR, NNDR, CAP, 원본 유일 레코드 차단)
# -----------------------------------------------------------------------------
def test_raw_unique_exact_clones_blocking():
    """원본 빈도=1인 유일 레코드가 합성 데이터에 생성된 경우 100% 차단되는지 검증"""
    raw_df = pd.DataFrame({
        "나이": [25, 30, 30, 45],  # 25, 45는 유일 레코드 (빈도=1), 30은 빈번 레코드 (빈도=2)
        "소득": [200, 300, 300, 500],
        "지역": ["서울", "경기", "경기", "부산"],
    })

    # 합성 데이터가 원본 유일 레코드(25, 200, 서울)와 빈번 레코드(30, 300, 경기)를 포함
    syn_df = pd.DataFrame({
        "나이": [25, 30, 28, 40],
        "소득": [200, 300, 290, 410],
        "지역": ["서울", "경기", "인천", "대구"],
    })

    filtered, report = PrivacyGuardrails.filter_exact_duplicates(
        raw_df, syn_df, filter_raw_unique_only=True
    )

    # 원본 유일 레코드인 (25, 200, 서울)은 반드시 제거되어야 함
    assert len(filtered) == 3
    assert report["raw_unique_duplicates_found"] == 1
    assert not ((filtered["나이"] == 25) & (filtered["소득"] == 200)).any()


def test_dcr_and_nndr_evaluation():
    """DCR(합성 vs 원본, 원본 내부 baseline) 및 NNDR 지표 산출 검증"""
    np.random.seed(42)
    raw_df = pd.DataFrame({
        "A": np.random.normal(10, 2, 50),
        "B": np.random.normal(50, 10, 50),
    })
    syn_df = pd.DataFrame({
        "A": np.random.normal(10, 2, 50),
        "B": np.random.normal(50, 10, 50),
    })
    plan = ColumnPlan(categorical=[], numerical=["A", "B"], ignored=[], pii=[], rules=[])

    dcr_report = PrivacyGuardrails.evaluate_dcr(raw_df, syn_df, plan)
    assert dcr_report["evaluated"] is True
    assert dcr_report["median_dcr"] is not None
    assert dcr_report["raw_internal_dcr_median"] is not None
    assert dcr_report["nndr_median"] is not None
    assert 0.0 <= dcr_report["nndr_median"] <= 2.0


def test_cap_attribute_inference():
    """CAP (속성 추론 위험도) 산출 및 baseline 대비 advantage 검증"""
    raw_df = pd.DataFrame({
        "성별": ["남", "여", "남", "여", "남"] * 10,
        "연령대": ["20대", "30대", "20대", "30대", "40대"] * 10,
        "소득구간": ["저소득", "고소득", "중소득", "고소득", "중소득"] * 10,
    })
    syn_df = raw_df.copy()
    plan = ColumnPlan(categorical=["성별", "연령대", "소득구간"], numerical=[], ignored=[], pii=[], rules=[])

    cap_report = PrivacyGuardrails.evaluate_cap(raw_df, syn_df, plan, qi_columns=["성별", "연령대"], sensitive_columns=["소득구간"])
    assert cap_report["evaluated"] is True
    assert "cap" in cap_report
    assert "inference_advantage" in cap_report


# -----------------------------------------------------------------------------
# 4. 종합 유용성 평가 (pMSE, Spearman, Cramér's V 유의쌍 보존율)
# -----------------------------------------------------------------------------
def test_pmse_computation():
    """pMSE 및 pMSE Ratio 계산 검증"""
    np.random.seed(42)
    raw_df = pd.DataFrame({
        "x1": np.random.randn(100),
        "x2": np.random.randn(100),
        "cat1": np.random.choice(["A", "B", "C"], 100),
    })
    # 동일한 분포에서 샘플링한 합성 데이터
    syn_df = pd.DataFrame({
        "x1": np.random.randn(100),
        "x2": np.random.randn(100),
        "cat1": np.random.choice(["A", "B", "C"], 100),
    })
    plan = ColumnPlan(categorical=["cat1"], numerical=["x1", "x2"], ignored=[], pii=[], rules=[])

    pmse_report = compute_pmse(raw_df, syn_df, plan)
    assert pmse_report["pmse"] is not None
    assert pmse_report["pmse_ratio"] is not None
    # 동일 분포 샘플이므로 ratio가 폭증하지 않고 정상 범위
    assert pmse_report["status"] in ["PASS", "EXCELLENT", "GOOD", "ACCEPTABLE"]


def test_spearman_correlation_evaluation():
    """Spearman 순위 상관계수 보존율 평가 검증"""
    x = np.linspace(0, 10, 50)
    raw_df = pd.DataFrame({"X": x, "Y": x**2})
    syn_df = pd.DataFrame({"X": x + np.random.normal(0, 0.1, 50), "Y": x**2 + np.random.normal(0, 0.1, 50)})

    res = evaluate_spearman_correlations(raw_df, syn_df, ["X", "Y"])
    assert res["spearman_score"] >= 0.8
    assert res["spearman_mae"] < 0.2


def test_cramers_v_significant_pairs_preservation():
    """Cramér's V 유의 연관쌍 보존율 평가 검증"""
    cat_a = ["A", "B", "A", "B"] * 25
    cat_b = ["1", "2", "1", "2"] * 25  # 강한 연관성
    cat_c = np.random.choice(["X", "Y"], 100)

    raw_df = pd.DataFrame({"A": cat_a, "B": cat_b, "C": cat_c})
    syn_df = pd.DataFrame({"A": cat_a, "B": cat_b, "C": cat_c})

    res = evaluate_categorical_associations_with_significance(raw_df, syn_df, ["A", "B", "C"])
    assert res["significant_pairs_original"] >= 1
    assert res["significant_preservation_rate"] == 1.0


# -----------------------------------------------------------------------------
# 5. 비즈니스 규칙 자동 탐색 엔진 (discovery.py)
# -----------------------------------------------------------------------------
def test_automated_rule_discovery():
    """선후관계, 0값 모순, 조건부 결측 자동 탐색 검증"""
    df = pd.DataFrame({
        "시작일자": ["2023-01-01", "2023-02-01", "2023-03-01"] * 10,
        "종료일자": ["2023-01-15", "2023-02-15", "2023-03-15"] * 10,
        "자녀수": [0, 0, 1, 2, 0] * 6,
        "출산자녀수": [0, 0, 1, 2, 0] * 6,
        "퇴거여부": ["N", "N", "Y", "N", "Y"] * 6,
        "퇴거일자": [None, None, "2023-05-01", None, "2023-06-01"] * 6,
    })

    # 선후관계 탐색 (시작일자 <= 종료일자)
    orders = discover_temporal_orders(df)
    assert any(o.preceding_column == "시작일자" and o.succeeding_column == "종료일자" for o in orders)

    # 0값 함의 탐색 (자녀수=0 -> 출산자녀수=0)
    zero_rules = discover_zero_implications(df)
    assert any(z.primary_column == "자녀수" and z.implied_zero_column == "출산자녀수" for z in zero_rules)

    # 조건부 결측 탐색 (퇴거여부='N' -> 퇴거일자=null)
    null_rules = discover_conditional_nulls(df)
    assert any(n.condition_column == "퇴거여부" and n.target_null_column == "퇴거일자" for n in null_rules)
