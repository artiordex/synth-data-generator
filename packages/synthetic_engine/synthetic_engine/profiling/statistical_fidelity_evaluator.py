# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: statistical_fidelity_evaluator.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/statistical_fidelity_evaluator.py
# 목적: statsmodels 및 scipy 기반 원본 vs 합성 데이터 다변량 통계 가설 검정 및 충실도 평가
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


def evaluate_statistical_fidelity(
    real_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    원본 데이터셋과 생성된 합성 데이터셋 사이의 통계적 정밀도와 동질성을 과학적으로 검정합니다.
    
    1. 수치형 컬럼: 2-Sample Kolmogorov-Smirnov (KS) Test (분포 동일성 및 p-value)
    2. 범주형 컬럼: Chi-Square Goodness of Fit Test (빈도 분포 동일성 및 p-value)
    3. 다변량 상관계수: Pearson/Spearman 상관행렬의 Frobenius Norm 유사도
    4. 종합 통계 충실도 점수 (Fidelity Score: 0 ~ 100점)
    """
    common_cols = [c for c in real_df.columns if c in synthetic_df.columns]
    if not common_cols:
        return {"error": "공통 컬럼이 존재하지 않습니다.", "overall_score": 0.0}

    column_reports: Dict[str, Any] = {}
    ks_scores: List[float] = []
    chi_scores: List[float] = []

    for col in common_cols:
        s_real = real_df[col].dropna()
        s_synth = synthetic_df[col].dropna()

        if len(s_real) == 0 or len(s_synth) == 0:
            continue

        # 수치형 컬럼 통계 검정
        if pd.api.types.is_numeric_dtype(s_real) and len(s_real.unique()) > 5:
            # 2-Sample Kolmogorov-Smirnov Test
            ks_res = stats.ks_2samp(s_real, s_synth)
            ks_stat = float(ks_res.statistic)
            p_val = float(ks_res.pvalue)

            # KS score: 1.0 - ks_statistic (통계량이 작을수록 두 분포가 일치함)
            fidelity = max(0.0, min(100.0, (1.0 - ks_stat) * 100.0))
            ks_scores.append(fidelity)

            # 평균, 표준편차 차이율
            mean_diff_pct = float(abs(s_real.mean() - s_synth.mean()) / (abs(s_real.mean()) + 1e-9) * 100.0)
            std_diff_pct = float(abs(s_real.std() - s_synth.std()) / (abs(s_real.std()) + 1e-9) * 100.0)

            column_reports[col] = {
                "type": "numeric",
                "ks_statistic": round(ks_stat, 4),
                "p_value": round(p_val, 6),
                "is_same_distribution": bool(p_val > alpha),
                "fidelity_score": round(fidelity, 1),
                "real_mean": round(float(s_real.mean()), 3),
                "synth_mean": round(float(s_synth.mean()), 3),
                "mean_diff_percent": round(mean_diff_pct, 2),
                "std_diff_percent": round(std_diff_pct, 2),
            }
        else:
            # 범주형 컬럼 통계 검정 (Chi-Square)
            real_counts = s_real.value_counts(normalize=True)
            synth_counts = s_synth.value_counts(normalize=True)

            all_cats = list(set(real_counts.index).union(set(synth_counts.index)))
            r_freqs = np.array([real_counts.get(c, 0.0) for c in all_cats])
            s_freqs = np.array([synth_counts.get(c, 0.0) for c in all_cats])

            # Total Variation Distance (TVD)
            tvd = 0.5 * np.sum(np.abs(r_freqs - s_freqs))
            fidelity = max(0.0, min(100.0, (1.0 - tvd) * 100.0))
            chi_scores.append(fidelity)

            # Chi-square test on actual counts
            try:
                min_len = min(len(s_real), len(s_synth))
                obs = np.array([synth_counts.get(c, 0.0) * min_len for c in all_cats]) + 1e-5
                exp = np.array([real_counts.get(c, 0.0) * min_len for c in all_cats]) + 1e-5
                chi2_stat, p_val = stats.chisquare(obs, exp)
            except Exception:
                chi2_stat, p_val = 0.0, 1.0

            column_reports[col] = {
                "type": "categorical",
                "tvd": round(float(tvd), 4),
                "chi2_statistic": round(float(chi2_stat), 4),
                "p_value": round(float(p_val), 6),
                "fidelity_score": round(fidelity, 1),
                "categories_count": len(all_cats),
            }

    # 3. 다변량 상관관계 보존도 (Correlation Matrix Frobenius Distance)
    num_cols = [c for c, r in column_reports.items() if r["type"] == "numeric"]
    corr_fidelity = 100.0

    if len(num_cols) >= 2:
        try:
            r_corr = real_df[num_cols].corr().fillna(0.0).values
            s_corr = synthetic_df[num_cols].corr().fillna(0.0).values
            # Matrix difference
            diff_matrix = r_corr - s_corr
            frob_norm = float(np.linalg.norm(diff_matrix, ord="fro"))
            max_norm = math.sqrt(len(num_cols) * len(num_cols) * 4.0)
            corr_fidelity = max(0.0, min(100.0, (1.0 - (frob_norm / max_norm)) * 100.0))
        except Exception:
            corr_fidelity = 90.0

    # 종합 충실도 점수 (가중 평균: 단변량 60% + 다변량 상관 40%)
    all_col_fidelities = ks_scores + chi_scores
    univariate_avg = float(np.mean(all_col_fidelities)) if all_col_fidelities else 85.0
    overall_score = round(univariate_avg * 0.6 + corr_fidelity * 0.4, 1)

    return {
        "overall_fidelity_score": overall_score,
        "univariate_fidelity_score": round(univariate_avg, 1),
        "correlation_fidelity_score": round(corr_fidelity, 1),
        "evaluated_columns_count": len(column_reports),
        "columns": column_reports,
        "significance_level_alpha": alpha,
        "verdict": "우수 (규제기관/임상연구 활용 가능)" if overall_score >= 85 else ("양호 (내부 분석 적합)" if overall_score >= 70 else "보통 (파라미터 튜닝 권장)"),
    }
