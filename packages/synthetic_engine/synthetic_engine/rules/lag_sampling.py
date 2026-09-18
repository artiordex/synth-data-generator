# -*- coding: utf-8 -*-
"""Reproducible, data-aware sampling of positive temporal lags."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..preprocessing.transformer import _parse_date_series


def _make_rng(random_state: int | np.random.Generator | None) -> np.random.Generator:
    if isinstance(random_state, np.random.Generator):
        return random_state
    return np.random.default_rng(random_state)


def sample_empirical_lags(
    original: pd.DataFrame | None,
    start_column: str,
    end_column: str,
    size: int,
    random_state: int | np.random.Generator | None = None,
    min_days: float = 1.0,
    max_days: float | None = None,
    return_metadata: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Sample positive day lags without introducing a fixed repair spike.

    The source distribution is used directly when at least 30 valid lags are
    available.  Smaller samples use a robust log-normal approximation, while
    missing reference information falls back to a bounded uniform distribution.
    ``max_days`` is intentionally optional: real public-service intervals can
    be longer than 60 days, but the no-reference fallback is always bounded to
    one through sixty days.
    """
    requested = max(0, int(size))
    lower = max(float(min_days), np.nextafter(0.0, 1.0))
    rng = _make_rng(random_state)
    metadata: dict[str, Any] = {
        "strategy": "bounded_generic_fallback",
        "source_count": 0,
        "min_days": lower,
        "max_days": float(max_days) if max_days is not None else None,
        "fallback_used": True,
    }

    if requested == 0:
        result = np.array([], dtype=float)
        return (result, metadata) if return_metadata else result

    lags: np.ndarray | None = None
    if (
        isinstance(original, pd.DataFrame)
        and start_column in original.columns
        and end_column in original.columns
    ):
        starts = _parse_date_series(original[start_column])
        ends = _parse_date_series(original[end_column])
        valid = starts.notna() & ends.notna()
        if valid.any():
            candidate = (ends[valid] - starts[valid]).dt.total_seconds().to_numpy() / 86400.0
            candidate = candidate[np.isfinite(candidate) & (candidate > 0)]
            if len(candidate):
                lags = candidate.astype(float)

    if lags is not None and len(lags) >= 30:
        upper_empirical = float(np.quantile(lags, 0.995))
        clipped = np.clip(lags, lower, max(upper_empirical, lower))
        if max_days is not None:
            clipped = np.clip(clipped, lower, float(max_days))
        sampled = rng.choice(clipped, size=requested, replace=True).astype(float)
        metadata.update({
            "strategy": "empirical_bootstrap",
            "source_count": int(len(lags)),
            "fallback_used": False,
            "winsorized_upper": upper_empirical,
        })
    elif lags is not None and len(lags) > 0:
        # Robust fit on log-lags.  MAD is stable for the small samples that
        # commonly occur in a newly uploaded public dataset.
        log_lags = np.log(np.maximum(lags, lower))
        center = float(np.median(log_lags))
        mad = float(np.median(np.abs(log_lags - center)))
        robust_sigma = 1.4826 * mad
        if robust_sigma <= 1e-8:
            q25, q75 = np.quantile(log_lags, [0.25, 0.75])
            robust_sigma = max(float((q75 - q25) / 1.349), 0.05)
        sampled = rng.lognormal(mean=center, sigma=robust_sigma, size=requested)
        metadata.update({
            "strategy": "robust_lognormal_fallback",
            "source_count": int(len(lags)),
            "fallback_used": True,
            "median_days": float(np.median(lags)),
            "mad_log_days": mad,
        })
    else:
        # Do not infer a private bound from the missing raw reference.  This
        # explicit bounded fallback is deliberately conservative and reported.
        fallback_upper = 60.0
        fallback_lower = max(lower, 1.0)
        sampled = rng.uniform(fallback_lower, fallback_upper + 1.0, size=requested)
        metadata.update({
            "source_count": 0,
            "fallback_min_days": fallback_lower,
            "fallback_max_days": fallback_upper,
        })

    upper = float(max_days) if max_days is not None else None
    if upper is not None and upper < lower:
        raise ValueError("max_days must be greater than or equal to min_days")
    if upper is None and metadata["strategy"] == "bounded_generic_fallback":
        upper = 60.0
    sampled = np.maximum(np.asarray(sampled, dtype=float), lower)
    if upper is not None:
        sampled = np.minimum(sampled, upper)
    # Dates are day-granular in the supported tabular rules.  Preserve a small
    # fractional component only when it is necessary to avoid a boundary tie.
    sampled = np.round(sampled, 3)
    metadata["effective_max_days"] = upper
    return (sampled, metadata) if return_metadata else sampled


__all__ = ["sample_empirical_lags"]
