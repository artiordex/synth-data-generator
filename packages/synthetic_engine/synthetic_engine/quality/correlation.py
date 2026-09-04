# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan

def fast_cramers_v(x_codes: np.ndarray, y_codes: np.ndarray, n_x: int, n_y: int) -> float:
    """Vectorized calculation of Cramér's V from factorized categorical codes using 2D bincount."""
    if n_x <= 1 or n_y <= 1 or len(x_codes) == 0:
        return 0.0

    flat_idx = x_codes * n_y + y_codes
    counts = np.bincount(flat_idx, minlength=n_x * n_y).reshape(n_x, n_y)

    n = len(x_codes)
    row_sums = counts.sum(axis=1)
    col_sums = counts.sum(axis=0)

    expected = np.outer(row_sums, col_sums) / n
    mask = expected > 0
    if not np.any(mask):
        return 0.0

    chi2 = np.sum(((counts[mask] - expected[mask]) ** 2) / expected[mask])

    r, k = n_x, n_y
    phi2 = chi2 / n
    phi2corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / (n - 1)) if n > 1 else 0.0
    rcorr = r - ((r - 1) ** 2) / (n - 1) if n > 1 else r
    kcorr = k - ((k - 1) ** 2) / (n - 1) if n > 1 else k
    denom = min(kcorr - 1, rcorr - 1)
    if denom <= 0:
        return 0.0
    return float(np.sqrt(phi2corr / denom))

def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Calculate Cramér's V statistic for categorical-categorical association."""
    x_codes, x_uniques = pd.factorize(x.astype(str))
    y_codes, y_uniques = pd.factorize(y.astype(str))
    return fast_cramers_v(x_codes, y_codes, len(x_uniques), len(y_uniques))

class CorrelationEvaluator:
    """Evaluates 2D correlation and pairwise association preservation across all variables."""

    @staticmethod
    def evaluate_correlations(
        original: pd.DataFrame,
        synthetic: pd.DataFrame,
        plan: ColumnPlan
    ) -> dict[str, Any]:
        result = {
            "numerical_correlation_score": 1.0,
            "categorical_association_score": 1.0,
            "overall_correlation_score": 1.0,
            "status": "PASS",
        }

        # 1. Numerical Pearson Correlation Matrix Comparison (All Pairs)
        num_cols = [c for c in plan.numerical if c in original.columns and c in synthetic.columns]
        if len(num_cols) >= 2:
            ori_num = original[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
            syn_num = synthetic[num_cols].apply(pd.to_numeric, errors="coerce").dropna()

            if len(ori_num) >= 5 and len(syn_num) >= 5:
                corr_ori = ori_num.corr(method="pearson").fillna(0.0)
                corr_syn = syn_num.corr(method="pearson").fillna(0.0)

                diff = np.abs(corr_ori.values - corr_syn.values)
                n = len(num_cols)
                triu_indices = np.triu_indices(n, k=1)
                if len(triu_indices[0]) > 0:
                    mae = float(np.mean(diff[triu_indices]))
                    num_score = max(0.0, min(1.0, 1.0 - (mae / 2.0)))
                    result["numerical_correlation_score"] = round(num_score, 4)
                    result["numerical_mae"] = round(mae, 4)
                    result["numerical_pairs_evaluated"] = int(len(triu_indices[0]))

        # 2. Categorical Cramér's V Pairwise Association Comparison (ALL Pairs)
        cat_cols = [c for c in plan.categorical if c in original.columns and c in synthetic.columns]
        if len(cat_cols) >= 2:
            n_sub = min(3000, len(original), len(synthetic))
            ori_cat_sub = original[cat_cols].sample(n=n_sub, random_state=42) if len(original) > n_sub else original[cat_cols]
            syn_cat_sub = synthetic[cat_cols].sample(n=n_sub, random_state=42) if len(synthetic) > n_sub else synthetic[cat_cols]

            ori_encoded = {}
            for col in cat_cols:
                codes, uniques = pd.factorize(ori_cat_sub[col].astype(str))
                ori_encoded[col] = (codes, len(uniques))

            syn_encoded = {}
            for col in cat_cols:
                codes, uniques = pd.factorize(syn_cat_sub[col].astype(str))
                syn_encoded[col] = (codes, len(uniques))

            cat_diffs = []
            pairwise_details = {}
            for i in range(len(cat_cols)):
                col_a = cat_cols[i]
                for j in range(i + 1, len(cat_cols)):  # All pairs evaluated without artificial limit
                    col_b = cat_cols[j]
                    v_ori = fast_cramers_v(ori_encoded[col_a][0], ori_encoded[col_b][0], ori_encoded[col_a][1], ori_encoded[col_b][1])
                    v_syn = fast_cramers_v(syn_encoded[col_a][0], syn_encoded[col_b][0], syn_encoded[col_a][1], syn_encoded[col_b][1])
                    diff = abs(v_ori - v_syn)
                    cat_diffs.append(diff)
                    if len(pairwise_details) < 50:
                        pairwise_details[f"{col_a}__x__{col_b}"] = {
                            "original_v": round(v_ori, 4),
                            "synthetic_v": round(v_syn, 4),
                            "diff": round(diff, 4)
                        }

            if cat_diffs:
                cat_mae = float(np.mean(cat_diffs))
                cat_score = max(0.0, min(1.0, 1.0 - cat_mae))
                result["categorical_association_score"] = round(cat_score, 4)
                result["categorical_mae"] = round(cat_mae, 4)
                result["categorical_pairs_evaluated"] = len(cat_diffs)
                result["categorical_pairwise_details"] = pairwise_details

        # 3. Overall combined correlation fidelity score
        scores = []
        if len(num_cols) >= 2:
            scores.append(result["numerical_correlation_score"])
        if len(cat_cols) >= 2:
            scores.append(result["categorical_association_score"])

        overall = float(np.mean(scores)) if scores else 1.0
        result["overall_correlation_score"] = round(overall, 4)
        result["status"] = "PASS" if overall >= 0.80 else ("REVIEW" if overall >= 0.65 else "FAIL")

        return result

