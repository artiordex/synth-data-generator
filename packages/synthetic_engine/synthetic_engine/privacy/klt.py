"""Group-based k-anonymity, l-diversity and t-closeness diagnostics."""
from __future__ import annotations

from typing import Any
import pandas as pd


def evaluate_klt(
    frame: pd.DataFrame,
    quasi_identifiers: list[str],
    sensitive_columns: list[str],
    *,
    k_threshold: int = 5,
    l_threshold: int = 2,
    t_threshold: float = 0.2,
) -> dict[str, Any]:
    quasi = [c for c in quasi_identifiers if c in frame.columns]
    sensitive = [c for c in sensitive_columns if c in frame.columns]
    if not quasi:
        return {"status": "NOT_EVALUATED", "reason": "준식별자를 선택하지 않았습니다.",
                "quasi_identifiers": [], "sensitive_columns": sensitive}

    normalized = frame.copy()
    for column in quasi + sensitive:
        normalized[column] = normalized[column].astype("string").fillna("<NULL>")
    groups = normalized.groupby(quasi, dropna=False, sort=False)
    sizes = groups.size()
    k_value = int(sizes.min()) if len(sizes) else 0
    unique_rate = float((sizes == 1).sum() / max(len(sizes), 1))

    l_by_column: dict[str, int] = {}
    t_by_column: dict[str, float] = {}
    for column in sensitive:
        diversity = groups[column].nunique(dropna=False)
        l_by_column[column] = int(diversity.min()) if len(diversity) else 0
        global_dist = normalized[column].value_counts(normalize=True, dropna=False)
        max_distance = 0.0
        for _, group in groups:
            local = group[column].value_counts(normalize=True, dropna=False)
            categories = global_dist.index.union(local.index)
            distance = 0.5 * sum(abs(float(local.get(v, 0.0)) - float(global_dist.get(v, 0.0))) for v in categories)
            max_distance = max(max_distance, distance)
        t_by_column[column] = round(max_distance, 6)

    l_value = min(l_by_column.values()) if l_by_column else None
    t_value = max(t_by_column.values()) if t_by_column else None
    passed = k_value >= k_threshold
    if l_value is not None:
        passed = passed and l_value >= l_threshold
    if t_value is not None:
        passed = passed and t_value <= t_threshold
    return {
        "status": "PASS" if passed else "REVIEW",
        "quasi_identifiers": quasi,
        "sensitive_columns": sensitive,
        "group_count": int(len(sizes)),
        "k": k_value,
        "k_threshold": k_threshold,
        "unique_group_rate": round(unique_rate, 6),
        "l": l_value,
        "l_threshold": l_threshold,
        "l_by_column": l_by_column,
        "t": t_value,
        "t_threshold": t_threshold,
        "t_by_column": t_by_column,
    }

