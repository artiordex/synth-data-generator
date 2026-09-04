# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd

class DifferentialPrivacyManager:
    @staticmethod
    def apply_laplace_noise(
        df: pd.DataFrame,
        numerical_cols: list[str],
        epsilon: float = 1.0,
        delta: float = 1e-5,
        seed: int = 42,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        if epsilon <= 0:
            return df, {"enabled": False, "epsilon": epsilon, "delta": delta}

        np.random.seed(seed)
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

            col_min = float(valid.min())
            col_max = float(valid.max())
            col_range = col_max - col_min
            if col_range <= 0:
                col_range = 1.0

            sensitivity = col_range / math.sqrt(n_rows)
            scale = max(sensitivity / max(epsilon, 0.01), 1e-6)

            noise = np.random.laplace(loc=0.0, scale=scale, size=len(output))
            noise = np.where(series.isna(), np.nan, noise)

            perturbed = series + noise
            perturbed = perturbed.clip(lower=col_min - 0.1 * col_range, upper=col_max + 0.1 * col_range)

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
