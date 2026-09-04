# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
import pandas as pd

def jsd(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> float:
    p = np.asarray(p, dtype=float) + eps
    q = np.asarray(q, dtype=float) + eps
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))

def categorical_jsd(original: pd.Series, synthetic: pd.Series) -> float:
    original_counts = original.astype("string").value_counts(normalize=True, dropna=False)
    synthetic_counts = synthetic.astype("string").value_counts(normalize=True, dropna=False)
    index = original_counts.index.union(synthetic_counts.index)
    return jsd(
        original_counts.reindex(index, fill_value=0).values,
        synthetic_counts.reindex(index, fill_value=0).values,
    )

def numerical_jsd(original: pd.Series, synthetic: pd.Series, bins: int = 20) -> float:
    if not len(original) or not len(synthetic):
        return float("nan")
    original_numeric = pd.to_numeric(original, errors="coerce")
    synthetic_numeric = pd.to_numeric(synthetic, errors="coerce")
    original_values = original_numeric.dropna()
    synthetic_values = synthetic_numeric.dropna()
    combined = pd.concat([original_values, synthetic_values])

    if combined.nunique() <= 1:
        return jsd([len(original_values), original_numeric.isna().sum()],
                   [len(synthetic_values), synthetic_numeric.isna().sum()])
    edges = np.linspace(float(combined.min()), float(combined.max()), bins + 1)
    original_hist, _ = np.histogram(original_values, bins=edges)
    synthetic_hist, _ = np.histogram(synthetic_values, bins=edges)
    return jsd(np.append(original_hist, original_numeric.isna().sum()),
               np.append(synthetic_hist, synthetic_numeric.isna().sum()))

def binned_keys(df: pd.DataFrame, categorical: list[str], numerical: list[str], bins: int, reference: pd.DataFrame | None = None) -> pd.Series:
    reference = df if reference is None else reference
    parts = []
    for column in categorical:
        if column in df.columns:
            parts.append(df[column].astype("string").fillna("__NA__"))

    for column in numerical:
        if column not in df.columns: continue
        series = pd.to_numeric(df[column], errors="coerce")
        reference_series = pd.to_numeric(reference[column], errors="coerce") if column in reference.columns else series
        valid_reference = reference_series.dropna()
        quantiles = np.linspace(0, 1, bins + 1)
        edges = np.unique(np.nanquantile(valid_reference, quantiles)) if len(valid_reference) else np.array([])
        if len(edges) < 3:
            binned = series.round(0).astype("Int64").astype("string").fillna("__NA__")
        else:
            binned_values = np.digitize(series, bins=edges[1:-1], right=True)
            binned = pd.Series(binned_values, index=series.index).astype("Int64").astype("string")
            binned = binned.mask(series.isna(), "__NA__")
        parts.append(binned.fillna("__NA__"))

    if not parts: return pd.Series([""] * len(df), index=df.index)
    return pd.concat(parts, axis=1).astype(str).agg("||".join, axis=1)
