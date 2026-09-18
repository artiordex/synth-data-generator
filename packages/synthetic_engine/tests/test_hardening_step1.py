# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from synthetic_engine.rules.engine import DatasetRuleEngine, sample_empirical_lags


def test_empirical_lag_sampling_preserves_variation():
    original = pd.DataFrame({
        "start": pd.date_range("2024-01-01", periods=80, freq="D"),
        "end": pd.date_range("2024-01-03", periods=80, freq="D")
        + pd.to_timedelta(np.tile(np.arange(1, 21), 4), unit="D"),
    })

    sampled = sample_empirical_lags(original, "start", "end", size=200, random_state=7)

    assert len(sampled) == 200
    assert np.unique(sampled).size > 5
    assert float(np.std(sampled)) > 0


def test_postprocess_does_not_create_fixed_lag_spike():
    original = pd.DataFrame({
        "입주일자": pd.date_range("2024-01-01", periods=90, freq="D"),
        "퇴거일자": pd.date_range("2024-01-03", periods=90, freq="D")
        + pd.to_timedelta(np.tile(np.arange(1, 31), 3), unit="D"),
    })
    synthetic = pd.DataFrame({
        "입주일자": pd.date_range("2025-01-01", periods=60, freq="D"),
        "퇴거일자": pd.date_range("2024-12-01", periods=60, freq="D"),
    })

    processed = DatasetRuleEngine.postprocess(
        synthetic,
        original=original,
        random_state=17,
    )
    lags = (
        pd.to_datetime(processed["퇴거일자"])
        - pd.to_datetime(processed["입주일자"])
    ).dt.days

    assert (lags > 0).all()
    assert lags.nunique() > 1
    assert int(lags.value_counts().max()) < len(lags)


def test_lag_sampling_respects_positive_and_domain_bounds():
    original = pd.DataFrame({
        "start": pd.date_range("2024-01-01", periods=40, freq="D"),
        "end": pd.date_range("2024-01-01", periods=40, freq="D")
        + pd.to_timedelta(np.arange(1, 41), unit="D"),
    })

    sampled = sample_empirical_lags(
        original,
        "start",
        "end",
        size=500,
        random_state=3,
        min_days=2,
        max_days=10,
    )

    assert (sampled >= 2).all()
    assert (sampled <= 10).all()


def test_lag_sampling_fallback_is_reproducible_with_seed():
    first = sample_empirical_lags(None, "missing_start", "missing_end", 50, random_state=42)
    second = sample_empirical_lags(None, "missing_start", "missing_end", 50, random_state=42)

    np.testing.assert_array_equal(first, second)
    assert (first >= 1).all()
    assert (first <= 60).all()
