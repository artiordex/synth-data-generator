# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: utility.py
# 경로: packages/synthetic_engine/synthetic_engine/quality/utility.py
# 목적: pMSE, Spearman 상관계수, Cramér's V 유의쌍 보존율 등 종합 유용성 지표를 산출함
# =============================================================================
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

from ..common.types import ColumnPlan
from .correlation import fast_cramers_v


def compute_pmse(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan,
    max_samples: int = 2000
) -> dict[str, Any]:
    """
    Propensity Score Mean Squared Error (pMSE) 및 pMSE Ratio를 계산함.
    원본(0)과 합성(1)을 판별하는 로지스틱 회귀 모델의 성향점수 e_i 편차를 측정하여
    두 분포가 얼마나 식별 불가능하게 유사한지 평가함.
    """
    eval_cols = [c for c in plan.categorical + plan.numerical if c in original.columns and c in synthetic.columns]
    if not eval_cols or len(original) == 0 or len(synthetic) == 0:
        return {"pmse": None, "pmse_ratio": None, "status": "NOT_EVALUATED"}

    # 서브샘플링으로 빠른 연산 보장
    max_samples = max(1, int(max_samples))
    n_ori = min(max_samples, len(original))
    n_syn = min(max_samples, len(synthetic))
    df_ori = original[eval_cols].sample(n=n_ori, random_state=42) if len(original) > n_ori else original[eval_cols]
    df_syn = synthetic[eval_cols].sample(n=n_syn, random_state=42) if len(synthetic) > n_syn else synthetic[eval_cols]

    # 결합 데이터프레임 (원본: 0, 합성: 1)
    df_combined = pd.concat([df_ori, df_syn], axis=0, ignore_index=True)
    y = np.array([0] * len(df_ori) + [1] * len(df_syn))

    num_cols = [c for c in plan.numerical if c in eval_cols]
    cat_cols = [c for c in plan.categorical if c in eval_cols]

    # 전처리 파이프라인 (결측치 대체 및 스케일링/원핫인코딩)
    transformers = []
    if num_cols:
        # 수치형 결측 중앙값 대체
        for c in num_cols:
            df_combined[c] = pd.to_numeric(df_combined[c], errors="coerce")
            df_combined[c] = df_combined[c].fillna(df_combined[c].median() if df_combined[c].notna().any() else 0)
        transformers.append(("num", StandardScaler(), num_cols))

    if cat_cols:
        for c in cat_cols:
            df_combined[c] = df_combined[c].astype("object").where(df_combined[c].notna(), "missing").astype(str)
        try:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False, max_categories=10)
        except TypeError:  # scikit-learn < 1.2
            encoder = OneHotEncoder(handle_unknown="ignore", sparse=False, max_categories=10)
        transformers.append(("cat", encoder, cat_cols))

    if not transformers:
        return {"pmse": None, "pmse_ratio": None, "status": "NOT_EVALUATED"}

    preprocessor = ColumnTransformer(transformers=transformers)
    try:
        X = preprocessor.fit_transform(df_combined)
        # 로지스틱 회귀 모델 학습
        clf = LogisticRegression(max_iter=300, random_state=42, C=1.0)
        clf.fit(X, y)

        # 성향점수 e_i
        probs = clf.predict_proba(X)[:, 1]
        c = float(len(df_syn) / len(df_combined))  # 기저 확률 (대개 0.5)
        pmse = float(np.mean((probs - c) ** 2))

        # 기대 pMSE (이상적인 동일 분포일 때의 우연 오차)
        k = max(int(X.shape[1]), 1)
        N = len(df_combined)
        expected_pmse = (k * ((1 - c) ** 2) * c) / max(N, 1)
        pmse_ratio = float(pmse / expected_pmse) if expected_pmse > 0 else 1.0

        # 판정 상태는 명세의 pMSE Ratio 기준을 우선한다.
        status = "PASS" if pmse_ratio <= 3.0 else ("REVIEW" if pmse_ratio <= 5.0 else "FAIL")

        return {
            "pmse": round(pmse, 5),
            "pmse_ratio": round(pmse_ratio, 3),
            "pMSE_Ratio": round(pmse_ratio, 3),
            "expected_pmse": round(expected_pmse, 5),
            "class_prior": round(c, 5),
            "degrees_of_freedom": k,
            "status": status,
            "feature_count": k,
            "sample_size": N,
        }
    except Exception:
        return {"pmse": None, "pmse_ratio": None, "status": "ERROR"}


def evaluate_spearman_correlations(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    numerical_columns: list[str]
) -> dict[str, Any]:
    """수치형 변수 간 Spearman 순위상관계수를 비교함"""
    num_cols = [c for c in numerical_columns if c in original.columns and c in synthetic.columns]
    if len(num_cols) < 2:
        return {"spearman_score": 1.0, "spearman_preservation_rate": 1.0, "spearman_mae": 0.0, "pairs_evaluated": 0, "pair_metrics": {}}

    ori_num = original[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
    syn_num = synthetic[num_cols].apply(pd.to_numeric, errors="coerce").dropna()

    if len(ori_num) < 5 or len(syn_num) < 5:
        return {"spearman_score": 1.0, "spearman_preservation_rate": 1.0, "spearman_mae": 0.0, "pairs_evaluated": 0, "pair_metrics": {}}

    corr_ori, _ = spearmanr(ori_num)
    corr_syn, _ = spearmanr(syn_num)

    # 단일 컬럼 쌍인 경우 2x2 행렬
    if isinstance(corr_ori, float) or np.isscalar(corr_ori):
        corr_ori = np.array([[1.0, corr_ori], [corr_ori, 1.0]])
        corr_syn = np.array([[1.0, corr_syn], [corr_syn, 1.0]])

    corr_ori = np.nan_to_num(corr_ori, nan=0.0)
    corr_syn = np.nan_to_num(corr_syn, nan=0.0)

    diff = np.abs(corr_ori - corr_syn)
    n = len(num_cols)
    triu_indices = np.triu_indices(n, k=1)
    if len(triu_indices[0]) > 0:
        mae = float(np.mean(diff[triu_indices]))
        score = max(0.0, min(1.0, 1.0 - (mae / 2.0)))
        pair_metrics = {}
        for i, j in zip(*triu_indices):
            pair_metrics[f"{num_cols[i]} x {num_cols[j]}"] = {
                "original": round(float(corr_ori[i, j]), 4),
                "synthetic": round(float(corr_syn[i, j]), 4),
                "absolute_error": round(float(diff[i, j]), 4),
                "preservation_rate": round(max(0.0, 1.0 - float(diff[i, j]) / 2.0), 4),
            }
        return {
            "spearman_score": round(score, 4),
            "spearman_preservation_rate": round(score, 4),
            "spearman_mae": round(mae, 4),
            "pairs_evaluated": int(len(triu_indices[0])),
            "pair_metrics": pair_metrics,
        }
    return {"spearman_score": 1.0, "spearman_preservation_rate": 1.0, "spearman_mae": 0.0, "pairs_evaluated": 0, "pair_metrics": {}}


def evaluate_categorical_associations_with_significance(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    categorical_columns: list[str],
    significance_threshold: float = 0.15
) -> dict[str, Any]:
    """
    범주형 변수 간 Cramér's V 연관성을 전수 평가하고,
    원본에서 유의한 연관성(V >= threshold)을 가진 핵심 변수 쌍들이
    합성데이터에서 얼마나 유지되었는지(유의 연관 보존율)를 평가함.
    """
    cat_cols = [c for c in categorical_columns if c in original.columns and c in synthetic.columns]
    if len(cat_cols) < 2:
        return {
            "cramers_v_score": 1.0,
            "cramers_v_mae": 0.0,
            "significant_pairs_original": 0,
            "significant_pairs_preserved": 0,
            "significant_preservation_rate": 1.0,
            "significant_pairs": [],
            "lost_significant_pairs": [],
        }

    n_sub = min(3000, len(original), len(synthetic))
    ori_sub = original[cat_cols].sample(n=n_sub, random_state=42) if len(original) > n_sub else original[cat_cols]
    syn_sub = synthetic[cat_cols].sample(n=n_sub, random_state=42) if len(synthetic) > n_sub else synthetic[cat_cols]

    ori_codes = {}
    ori_uniques = {}
    syn_codes = {}
    syn_uniques = {}

    for c in cat_cols:
        codes_o, un_o = pd.factorize(ori_sub[c].astype(str))
        ori_codes[c] = codes_o
        ori_uniques[c] = len(un_o)
        codes_s, un_s = pd.factorize(syn_sub[c].astype(str))
        syn_codes[c] = codes_s
        syn_uniques[c] = len(un_s)

    diffs = []
    significant_orig = []
    preserved_count = 0
    lost_pairs = []

    for i in range(len(cat_cols)):
        col_i = cat_cols[i]
        for j in range(i + 1, len(cat_cols)):
            col_j = cat_cols[j]
            v_ori = fast_cramers_v(ori_codes[col_i], ori_codes[col_j], ori_uniques[col_i], ori_uniques[col_j])
            v_syn = fast_cramers_v(syn_codes[col_i], syn_codes[col_j], syn_uniques[col_i], syn_uniques[col_j])

            diffs.append(abs(v_ori - v_syn))

            # 원본에서 유의한 연관성이 있는 변수 쌍
            if v_ori >= significance_threshold:
                pair_name = f"{col_i} x {col_j}"
                significant_orig.append(pair_name)
                # 합성에서도 최소 원본의 40% 이상 연관성을 유지하고 있는지 확인
                if v_syn >= max(0.08, v_ori * 0.4):
                    preserved_count += 1
                else:
                    lost_pairs.append({
                        "pair": pair_name,
                        "original_v": round(v_ori, 3),
                        "synthetic_v": round(v_syn, 3),
                    })

    mae = float(np.mean(diffs)) if diffs else 0.0
    score = max(0.0, min(1.0, 1.0 - mae))
    preservation_rate = float(preserved_count / max(len(significant_orig), 1)) if significant_orig else 1.0

    return {
        "cramers_v_score": round(score, 4),
        "cramers_v_mae": round(mae, 4),
        "significant_pairs_original": len(significant_orig),
        "significant_pairs_preserved": preserved_count,
        "significant_pairs": significant_orig,
        "significant_preservation_rate": round(preservation_rate, 4),
        "lost_significant_pairs": lost_pairs[:10],  # 상위 10개 보고
    }


def evaluate_comprehensive_utility(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan
) -> dict[str, Any]:
    """유용성 종합 평가 (단변량, 연속형 상관관계, 범주형 연관성, pMSE)"""
    pmse_report = compute_pmse(original, synthetic, plan)
    spearman_report = evaluate_spearman_correlations(original, synthetic, plan.numerical)
    cat_assoc_report = evaluate_categorical_associations_with_significance(original, synthetic, plan.categorical)

    return {
        "pmse_metrics": pmse_report,
        "spearman_metrics": spearman_report,
        "categorical_association_metrics": cat_assoc_report,
    }
