# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: dp.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/dp.py
# 목적: 수치형 데이터에 차분 프라이버시 노이즈를 적용함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd

class DifferentialPrivacyManager:
    """차분 프라이버시 적용을 위한 노이즈 처리를 제공함"""
    # apply laplace 노이즈 작업을 수행함
    @staticmethod
    def apply_laplace_noise(
        df: pd.DataFrame,
        numerical_cols: list[str],
        epsilon: float = 1.0,
        delta: float = 1e-5,
        seed: int = 42,
        public_bounds: dict[str, Any] | None = None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """수치형 컬럼에 라플라스 노이즈를 적용한 결과와 통계를 반환함"""
        if epsilon <= 0:
            return df, {"enabled": False, "epsilon": epsilon, "delta": delta}

        rng = np.random.default_rng(seed)
        output = df.copy()
        n_rows = max(len(output), 1)
        noise_stats = {}

        for col in numerical_cols:
            if col not in output.columns:
                continue
            series = pd.to_numeric(output[col], errors="coerce")
            valid = series.dropna()
            if valid.empty:
                continue

            bound_spec = (public_bounds or {}).get(col, {})
            if isinstance(bound_spec, dict) and bound_spec.get("min") is not None and bound_spec.get("max") is not None:
                col_range = float(bound_spec["max"]) - float(bound_spec["min"])
                bound_source = "public_bound"
            else:
                q25, q75 = valid.quantile([0.25, 0.75]).to_numpy()
                col_range = float(q75 - q25)
                bound_source = "robust_scale_no_raw_bound"
            if col_range <= 0:
                col_range = 1.0

            sensitivity = col_range / math.sqrt(n_rows)
            scale = max(sensitivity / max(epsilon, 0.01), 1e-6)

            noise = rng.laplace(loc=0.0, scale=scale, size=len(output))
            noise = np.where(series.isna(), np.nan, noise)

            perturbed = series + noise
            # Do not clip to raw exact min/max here.  Domain projection is a
            # separate post-DP stage and may only use public/schema bounds.

            is_integer = bool((valid % 1 == 0).all())
            if is_integer:
                perturbed = perturbed.round()
                if not perturbed.isna().any():
                    try:
                        perturbed = perturbed.astype(df[col].dtype)
                    except Exception:
                        perturbed = perturbed.astype("int64")
                else:
                    try:
                        perturbed = perturbed.astype("Int64")
                    except Exception:
                        pass

            output[col] = perturbed
            noise_stats[col] = {
                "scale": round(scale, 4),
                "sensitivity": round(sensitivity, 4),
                "bound_source": bound_source,
                "original_mean": round(float(valid.mean()), 4),
                "perturbed_mean": round(float(perturbed.dropna().mean()), 4),
            }

        return output, {
            "enabled": True,
            "epsilon": epsilon,
            "delta": delta,
            "columns_perturbed": list(noise_stats.keys()),
            "noise_stats": noise_stats,
        }

apply_differential_privacy_noise = DifferentialPrivacyManager.apply_laplace_noise
