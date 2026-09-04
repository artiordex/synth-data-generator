# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan

class PrivacyGuardrails:
    """Privacy guardrails to detect training data memorization, exact clones, and proximity risks."""

    @staticmethod
    def filter_exact_duplicates(
        raw: pd.DataFrame,
        synthetic: pd.DataFrame,
        columns: list[str] | None = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Identify and remove synthetic records that exactly match training rows."""
        eval_cols = [c for c in (columns or list(raw.columns)) if c in raw.columns and c in synthetic.columns]
        if not eval_cols or len(raw) == 0 or len(synthetic) == 0:
            return synthetic, {"exact_duplicates_found": 0, "exact_duplicate_rate": 0.0, "status": "PASS"}

        # Compare values, not display strings (1 and 1.0 are the same value).
        # Normalize pandas/NumPy missing sentinels so nulls also compare equally.
        raw_clean = raw[eval_cols].astype(object).where(raw[eval_cols].notna(), None)
        syn_clean = synthetic[eval_cols].astype(object).where(synthetic[eval_cols].notna(), None)

        raw_tuples = set(map(tuple, raw_clean.values))
        is_duplicate = [tuple(row) in raw_tuples for row in syn_clean.values]

        duplicates_found = int(sum(is_duplicate))
        duplicate_rate = float(duplicates_found / max(len(synthetic), 1))

        # Filter out exact duplicates if any
        if duplicates_found > 0:
            filtered_synthetic = synthetic.loc[[not d for d in is_duplicate]].reset_index(drop=True)
        else:
            filtered_synthetic = synthetic

        status = "PASS" if duplicate_rate <= 0.01 else ("REVIEW" if duplicate_rate <= 0.05 else "FAIL")

        return filtered_synthetic, {
            "exact_duplicates_found": duplicates_found,
            "exact_duplicate_rate": round(duplicate_rate, 4),
            "status": status,
            "rows_before": len(synthetic),
            "rows_after": len(filtered_synthetic)
        }

    @staticmethod
    def evaluate_dcr(
        raw: pd.DataFrame,
        synthetic: pd.DataFrame,
        plan: ColumnPlan,
        sample_size: int = 500
    ) -> dict[str, Any]:
        """Compute Distance to Closest Record (DCR) to evaluate memorization and nearest-neighbor proximity."""
        num_cols = [c for c in plan.numerical if c in raw.columns and c in synthetic.columns]
        if not num_cols or len(raw) < 5 or len(synthetic) < 5:
            return {
                "median_dcr": None,
                "min_dcr": None,
                "memorization_risk_rate": None,
                "status": "NOT_EVALUATED",
                "evaluated": False
            }

        # Subsample for fast computation if tables are large
        raw_sample = raw[num_cols].apply(pd.to_numeric, errors="coerce").dropna().head(sample_size).values
        syn_sample = synthetic[num_cols].apply(pd.to_numeric, errors="coerce").dropna().head(sample_size).values

        if len(raw_sample) < 5 or len(syn_sample) < 5:
            return {"median_dcr": None, "min_dcr": None, "memorization_risk_rate": None, "status": "NOT_EVALUATED", "evaluated": False}

        # Min-max normalize numerical features using raw reference
        col_min = np.nanmin(raw_sample, axis=0)
        col_max = np.nanmax(raw_sample, axis=0)
        col_range = np.where((col_max - col_min) == 0, 1.0, col_max - col_min)

        norm_raw = (raw_sample - col_min) / col_range
        norm_syn = (syn_sample - col_min) / col_range

        # Compute DCR for each synthetic row (vectorized batch chunking)
        dcrs = []
        for i in range(len(norm_syn)):
            diff = norm_raw - norm_syn[i]
            dists = np.sqrt(np.sum(diff ** 2, axis=1))
            dcrs.append(float(np.min(dists)))

        dcrs_arr = np.array(dcrs)
        min_dcr = float(np.min(dcrs_arr))
        median_dcr = float(np.median(dcrs_arr))
        # Records with normalized Euclidean distance < 0.05 are flagged as memorization risk
        risk_rate = float(np.mean(dcrs_arr < 0.05))

        status = "PASS" if risk_rate <= 0.05 else ("REVIEW" if risk_rate <= 0.15 else "FAIL")

        return {
            "median_dcr": round(median_dcr, 4),
            "min_dcr": round(min_dcr, 4),
            "memorization_risk_rate": round(risk_rate, 4),
            "status": status,
            "evaluated": True
        }
