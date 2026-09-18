# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: guardrails.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/guardrails.py
# 목적: 합성 결과의 복제·근접성·재식별 위험을 점검함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
import math
from collections import Counter
from typing import Any
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan
from ..rules.profile_registry import default_engine_settings


_GUARDRAIL_SETTINGS = default_engine_settings()["guardrails"]
_GENERALIZATION_LABEL = str(_GUARDRAIL_SETTINGS["generalization_label"])
_GENERALIZED_LABEL_SUFFIX = str(_GUARDRAIL_SETTINGS["generalized_label_suffix"])
_KNOWN_GENERALIZATION_LABELS = {
    str(label).strip().lower()
    for label in _GUARDRAIL_SETTINGS["known_generalization_labels"]
}


def _clone_value(value: Any) -> Any:
    """Normalize scalar values for stable clone/QI comparisons."""
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return int(numeric) if numeric.is_integer() else numeric
    return value


def _frame_keys(frame: pd.DataFrame, columns: list[str]) -> list[tuple[Any, ...]]:
    return [
        tuple(_clone_value(value) for value in row)
        for row in frame[columns].astype(object).to_numpy()
    ]


def _bound_for(bounds: dict[str, Any] | None, column: str) -> tuple[float | None, float | None]:
    if not bounds or column not in bounds:
        return None, None
    spec = bounds[column]
    if isinstance(spec, dict):
        return spec.get("min"), spec.get("max")
    if isinstance(spec, (tuple, list)) and len(spec) >= 2:
        return spec[0], spec[1]
    return None, None


def _robust_scale(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if not len(values):
        return 1.0
    q25, q75 = np.quantile(values, [0.25, 0.75])
    iqr_scale = float((q75 - q25) / 1.349)
    median = float(np.median(values))
    mad_scale = float(1.4826 * np.median(np.abs(values - median)))
    return max(iqr_scale, mad_scale, abs(median) * 0.01, 1e-6)


def escape_unique_clones(
    raw: pd.DataFrame,
    synthetic: pd.DataFrame,
    qi_columns: list[str] | None = None,
    non_qi_columns: list[str] | None = None,
    random_state: int | np.random.Generator | None = 42,
    bounds: dict[str, Any] | None = None,
    return_report: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
    """Escape exact clones while explicitly handling unique QI combinations."""
    output = synthetic.copy()
    common = [column for column in raw.columns if column in output.columns]
    qi = [column for column in (qi_columns or []) if column in raw.columns and column in output.columns]
    numeric_candidates = [
        column for column in (non_qi_columns or [])
        if column in common and column not in qi and pd.api.types.is_numeric_dtype(output[column])
    ]
    if not non_qi_columns:
        numeric_candidates = [
            column for column in common
            if column not in qi and pd.api.types.is_numeric_dtype(output[column])
        ]

    report: dict[str, Any] = {
        "full_clone_candidates": 0,
        "escaped_full_clones": 0,
        "unique_qi_candidates": 0,
        "unsafe_unique_qi_rows": 0,
        "generalized_qi_rows": 0,
        "dropped_rows": 0,
        "status": "PASS",
    }
    if not common or output.empty or raw.empty:
        report.update({"status": "NOT_EVALUATED", "reason": "비교 가능한 컬럼 또는 행이 없습니다."})
        return (output, report) if return_report else output

    rng = random_state if isinstance(random_state, np.random.Generator) else np.random.default_rng(random_state)
    raw_all_keys = set(_frame_keys(raw, common))
    raw_qi_counts = Counter(_frame_keys(raw, qi)) if qi else Counter()
    raw_unique_qi_keys = {key for key, count in raw_qi_counts.items() if count == 1}

    drop_indices: list[Any] = []
    for index in list(output.index):
        current_key = tuple(_clone_value(output.at[index, column]) for column in common)
        if current_key in raw_all_keys:
            report["full_clone_candidates"] += 1
            escaped = False
            for column in numeric_candidates:
                numeric = pd.to_numeric(output.at[index, column], errors="coerce")
                if pd.isna(numeric):
                    continue
                scale = _robust_scale(pd.concat([raw[column], output[column]], ignore_index=True))
                lower, upper = _bound_for(bounds, column)
                integer = pd.api.types.is_integer_dtype(output[column])
                for attempt in range(8):
                    if integer:
                        delta = int(max(1, round(scale * (0.05 + attempt * 0.05))))
                        candidate = round(float(numeric) + int(rng.choice([-delta, delta])))
                    else:
                        delta = float(rng.normal(0.0, max(scale * (0.05 + attempt * 0.05), 1e-6)))
                        candidate = float(numeric) + (delta if delta else scale * 0.05)
                    if lower is not None:
                        candidate = max(float(lower), candidate)
                    if upper is not None:
                        candidate = min(float(upper), candidate)
                    if _clone_value(candidate) == _clone_value(numeric):
                        continue
                    output.at[index, column] = candidate
                    candidate_key = tuple(_clone_value(output.at[index, name]) for name in common)
                    if candidate_key not in raw_all_keys:
                        escaped = True
                        report["escaped_full_clones"] += 1
                        break
                if escaped:
                    break
            if not escaped:
                drop_indices.append(index)
                continue

        if qi:
            qi_key = tuple(_clone_value(output.at[index, column]) for column in qi)
            if qi_key in raw_unique_qi_keys:
                report["unique_qi_candidates"] += 1
                report["unsafe_unique_qi_rows"] += 1
                generalized = False
                for column in qi:
                    if pd.api.types.is_numeric_dtype(output[column]):
                        value = pd.to_numeric(output.at[index, column], errors="coerce")
                        if pd.isna(value):
                            continue
                        scale = _robust_scale(pd.concat([raw[column], output[column]], ignore_index=True))
                        lower, upper = _bound_for(bounds, column)
                        for attempt in range(8):
                            candidate = float(value) + float(rng.normal(0, max(scale * (0.1 + attempt * 0.05), 1e-6)))
                            if lower is not None:
                                candidate = max(float(lower), candidate)
                            if upper is not None:
                                candidate = min(float(upper), candidate)
                            output.at[index, column] = candidate
                            new_key = tuple(_clone_value(output.at[index, name]) for name in qi)
                            if new_key not in raw_unique_qi_keys:
                                generalized = True
                                break
                    else:
                        current = output.at[index, column]
                        replacement = _GENERALIZATION_LABEL
                        if str(current).strip().lower() in _KNOWN_GENERALIZATION_LABELS:
                            replacement = f"{_GENERALIZATION_LABEL}{_GENERALIZED_LABEL_SUFFIX}"
                        output.at[index, column] = replacement
                        new_key = tuple(_clone_value(output.at[index, name]) for name in qi)
                        if new_key not in raw_unique_qi_keys:
                            generalized = True
                    if generalized:
                        report["generalized_qi_rows"] += 1
                        break
                if not generalized:
                    drop_indices.append(index)

    if drop_indices:
        output = output.drop(index=drop_indices).reset_index(drop=True)
        report["dropped_rows"] = len(drop_indices)
    report["exact_clone_rate_after"] = float(
        sum(key in raw_all_keys for key in _frame_keys(output, common)) / max(len(output), 1)
    )
    report["status"] = "REVIEW" if report["unsafe_unique_qi_rows"] else "PASS"
    return (output, report) if return_report else output


def _subspace_not_evaluated(status: str, reason: str, qi_columns: list[str]) -> dict[str, Any]:
    return {
        "sample_size_raw": 0,
        "sample_size_synthetic": 0,
        "qi_columns": qi_columns,
        "dcr_p05": None,
        "dcr_median": None,
        "nndr_p05": None,
        "nndr_median": None,
        "nndr_low_ratio": None,
        "exact_qi_match_rate": None,
        "relative_privacy_risk": None,
        "holdout_dcr_median": None,
        "status": status,
        "safe": None,
        "evaluated": False,
        "reason": reason,
    }


def _mixed_distance_matrix(
    left: pd.DataFrame,
    right: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
    reference: pd.DataFrame,
) -> np.ndarray:
    components: list[np.ndarray] = []
    for column in numeric_columns:
        ref_values = pd.to_numeric(reference[column], errors="coerce")
        median = float(ref_values.median()) if ref_values.notna().any() else 0.0
        quantiles = ref_values.dropna().quantile([0.25, 0.75]).to_numpy() if ref_values.notna().any() else np.array([0.0, 0.0])
        q25, q75 = quantiles
        mad = float(np.median(np.abs(ref_values.dropna().to_numpy(dtype=float) - median))) if ref_values.notna().any() else 0.0
        scale = max(float((q75 - q25) / 1.349), 1.4826 * mad, 1e-9)
        left_values = pd.to_numeric(left[column], errors="coerce").fillna(median).to_numpy(dtype=float)
        right_values = pd.to_numeric(right[column], errors="coerce").fillna(median).to_numpy(dtype=float)
        components.append(np.abs(left_values[:, None] - right_values[None, :]) / scale)
    for column in categorical_columns:
        left_values = left[column].astype(object).where(left[column].notna(), "__NA__").astype(str).to_numpy()
        right_values = right[column].astype(object).where(right[column].notna(), "__NA__").astype(str).to_numpy()
        components.append((left_values[:, None] != right_values[None, :]).astype(float))
    if not components:
        return np.empty((len(left), len(right)))
    return np.sqrt(np.mean(np.stack(components, axis=2) ** 2, axis=2))


def evaluate_subspace_dcr(
    raw_train: pd.DataFrame,
    synthetic: pd.DataFrame,
    qi_columns: list[str],
    raw_holdout: pd.DataFrame | None = None,
    sample_size: int = 500,
    random_state: int | None = None,
) -> dict[str, Any]:
    """Evaluate DCR/NNDR in a numeric, categorical, or mixed QI subspace."""
    qi = list(dict.fromkeys(qi_columns or []))
    if not isinstance(raw_train, pd.DataFrame) or not isinstance(synthetic, pd.DataFrame):
        return _subspace_not_evaluated("NOT_EVALUATED", "입력 데이터프레임이 없습니다.", qi)
    missing = [column for column in qi if column not in raw_train.columns or column not in synthetic.columns]
    if missing:
        return _subspace_not_evaluated("NOT_EVALUATED", f"QI 컬럼이 없습니다: {missing}", qi)
    if len(qi) == 0 or len(raw_train) < 2 or len(synthetic) < 1:
        return _subspace_not_evaluated("NOT_EVALUATED", "QI 컬럼 또는 평가 표본이 부족합니다.", qi)

    try:
        limit = max(1, int(sample_size))
        raw_sample = raw_train[qi].sample(n=min(limit, len(raw_train)), random_state=random_state).reset_index(drop=True)
        syn_sample = synthetic[qi].sample(n=min(limit, len(synthetic)), random_state=random_state).reset_index(drop=True)
        if len(raw_sample) < 2 or len(syn_sample) < 1:
            return _subspace_not_evaluated("NOT_EVALUATED", "평가 표본이 부족합니다.", qi)
        numeric = [column for column in qi if pd.api.types.is_numeric_dtype(raw_sample[column])]
        categorical = [column for column in qi if column not in numeric]
        distance = _mixed_distance_matrix(syn_sample, raw_sample, numeric, categorical, raw_sample)
        if distance.size == 0 or not np.isfinite(distance).all():
            return _subspace_not_evaluated("ERROR", "QI 거리 계산 결과가 유효하지 않습니다.", qi)

        nearest = np.sort(distance, axis=1)
        d1 = nearest[:, 0]
        d2 = nearest[:, 1] if distance.shape[1] > 1 else np.ones(len(d1))
        nndr = d1 / np.maximum(d2, 1e-12)
        exact_matches = np.any(distance <= 1e-12, axis=1)

        holdout_median = None
        holdout_p05 = None
        relative_risk = None
        if isinstance(raw_holdout, pd.DataFrame):
            holdout_missing = [column for column in qi if column not in raw_holdout.columns]
            if not holdout_missing and len(raw_holdout):
                holdout_sample = raw_holdout[qi].sample(
                    n=min(limit, len(raw_holdout)), random_state=random_state
                ).reset_index(drop=True)
                holdout_distance = _mixed_distance_matrix(
                    holdout_sample,
                    raw_sample,
                    numeric,
                    categorical,
                    raw_sample,
                )
                if holdout_distance.size and np.isfinite(holdout_distance).all():
                    holdout_d1 = np.min(holdout_distance, axis=1)
                    holdout_median = float(np.median(holdout_d1))
                    holdout_p05 = float(np.percentile(holdout_d1, 5))
                    relative_risk = float(np.median(d1) / max(holdout_median, 1e-12))

        dcr_p05 = float(np.percentile(d1, 5))
        dcr_median = float(np.median(d1))
        nndr_p05 = float(np.percentile(nndr, 5))
        nndr_median = float(np.median(nndr))
        nndr_low_ratio = float(np.mean(nndr < 0.2))
        exact_rate = float(np.mean(exact_matches))
        if exact_rate > 0 or dcr_p05 <= 1e-12 or nndr_low_ratio > 0.15:
            status = "FAIL"
        elif relative_risk is not None and relative_risk < 0.5:
            status = "REVIEW"
        elif nndr_low_ratio > 0.05:
            status = "REVIEW"
        else:
            status = "PASS"
        return {
            "sample_size_raw": int(len(raw_sample)),
            "sample_size_synthetic": int(len(syn_sample)),
            "qi_columns": qi,
            "numeric_qi_columns": numeric,
            "categorical_qi_columns": categorical,
            "dcr_p05": round(dcr_p05, 6),
            "dcr_median": round(dcr_median, 6),
            "nndr_p05": round(nndr_p05, 6),
            "nndr_median": round(nndr_median, 6),
            "nndr_low_ratio": round(nndr_low_ratio, 6),
            "exact_qi_match_rate": round(exact_rate, 6),
            "relative_privacy_risk": round(relative_risk, 6) if relative_risk is not None else None,
            "holdout_dcr_median": round(holdout_median, 6) if holdout_median is not None else None,
            "holdout_dcr_p05": round(holdout_p05, 6) if holdout_p05 is not None else None,
            "status": status,
            "safe": status == "PASS",
            "evaluated": True,
        }
    except Exception as exc:
        return _subspace_not_evaluated("ERROR", f"QI 거리 계산 실패: {exc}", qi)


class PrivacyGuardrails:
    """Privacy guardrails to detect training data memorization, exact clones, and proximity risks."""

    @staticmethod
    def escape_unique_clones(*args, **kwargs):
        """Class-level facade for :func:`escape_unique_clones`."""
        return escape_unique_clones(*args, **kwargs)

    @staticmethod
    def evaluate_subspace_dcr(*args, **kwargs):
        """Class-level facade for :func:`evaluate_subspace_dcr`."""
        return evaluate_subspace_dcr(*args, **kwargs)

    @staticmethod
    def filter_exact_duplicates(
        raw: pd.DataFrame,
        synthetic: pd.DataFrame,
        columns: list[str] | None = None,
        filter_raw_unique_only: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Identify and remove synthetic records that match training rows, with strict blocking of raw unique records."""
        eval_cols = [c for c in (columns or list(raw.columns)) if c in raw.columns and c in synthetic.columns]
        if not eval_cols or len(raw) == 0 or len(synthetic) == 0:
            return synthetic, {
                "exact_duplicates_found": 0,
                "exact_duplicate_rate": 0.0,
                "raw_unique_duplicates_found": 0,
                "raw_unique_duplicate_rate": 0.0,
                "status": "NOT_EVALUATED",
                "evaluated": False,
                "reason": "비교 가능한 컬럼 또는 평가 행이 없습니다.",
            }

        raw_clean = raw[eval_cols].astype(object).where(raw[eval_cols].notna(), None)
        syn_clean = synthetic[eval_cols].astype(object).where(synthetic[eval_cols].notna(), None)

        raw_counts = Counter(map(tuple, raw_clean.values))
        raw_unique_tuples = {k for k, v in raw_counts.items() if v == 1}
        raw_all_tuples = set(raw_counts.keys())

        is_raw_unique_dup = [tuple(row) in raw_unique_tuples for row in syn_clean.values]
        is_exact_dup = [tuple(row) in raw_all_tuples for row in syn_clean.values]

        unique_dups_found = int(sum(is_raw_unique_dup))
        total_dups_found = int(sum(is_exact_dup))

        unique_dup_rate = float(unique_dups_found / max(len(synthetic), 1))
        total_dup_rate = float(total_dups_found / max(len(synthetic), 1))

        # Strict policy: raw unique records MUST be filtered 100%
        # If filter_raw_unique_only is False, all exact duplicates are filtered
        to_filter = is_raw_unique_dup if filter_raw_unique_only else is_exact_dup

        if any(to_filter):
            filtered_synthetic = synthetic.loc[[not d for d in to_filter]].reset_index(drop=True)
        else:
            filtered_synthetic = synthetic

        # Status: Any raw-unique duplicate is a FAIL. Total duplicate rate > 1% is REVIEW, > 5% is FAIL
        if unique_dups_found > 0:
            status = "FAIL"
        elif total_dup_rate <= 0.01:
            status = "PASS"
        elif total_dup_rate <= 0.05:
            status = "REVIEW"
        else:
            status = "FAIL"

        return filtered_synthetic, {
            "exact_duplicates_found": total_dups_found,
            "exact_duplicate_rate": round(total_dup_rate, 4),
            "raw_unique_duplicates_found": unique_dups_found,
            "raw_unique_duplicate_rate": round(unique_dup_rate, 4),
            "status": status,
            "rows_before": len(synthetic),
            "rows_after": len(filtered_synthetic),
            "filter_raw_unique_only": filter_raw_unique_only,
            "evaluated": True,
        }

    @staticmethod
    def evaluate_dcr(
        raw: pd.DataFrame,
        synthetic: pd.DataFrame,
        plan: ColumnPlan,
        sample_size: int = 500,
        random_state: int | None = 42,
    ) -> dict[str, Any]:
        """Compute Distance to Closest Record (DCR) and NNDR for both synthetic-to-raw and raw-internal baseline."""
        num_cols = [c for c in plan.numerical if c in raw.columns and c in synthetic.columns]
        if not num_cols or len(raw) < 2 or len(synthetic) < 1:
            return {
                "median_dcr": None,
                "min_dcr": None,
                "dcr_5th_percentile": None,
                "raw_internal_dcr_median": None,
                "raw_internal_dcr_5th_percentile": None,
                "nndr_median": None,
                "nndr_risk_rate": None,
                "memorization_risk_rate": None,
                "status": "NOT_EVALUATED",
                "evaluated": False,
            }

        # Subsample for efficient computation
        sample_size = max(1, int(sample_size))
        raw_numeric = raw[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
        syn_numeric = synthetic[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
        raw_sample = raw_numeric.sample(n=min(sample_size, len(raw_numeric)), random_state=random_state).values
        syn_sample = syn_numeric.sample(n=min(sample_size, len(syn_numeric)), random_state=random_state).values

        if len(raw_sample) < 2 or len(syn_sample) < 1:
            return {
                "median_dcr": None,
                "min_dcr": None,
                "dcr_5th_percentile": None,
                "raw_internal_dcr_median": None,
                "raw_internal_dcr_5th_percentile": None,
                "nndr_median": None,
                "nndr_risk_rate": None,
                "memorization_risk_rate": None,
                "status": "NOT_EVALUATED",
                "evaluated": False,
            }

        # Min-max normalize numerical features using raw reference
        col_min = np.nanmin(raw_sample, axis=0)
        col_max = np.nanmax(raw_sample, axis=0)
        col_range = np.where((col_max - col_min) == 0, 1.0, col_max - col_min)

        norm_raw = (raw_sample - col_min) / col_range
        norm_syn = (syn_sample - col_min) / col_range

        # 1. Synthetic-to-Raw DCR & NNDR
        syn_dcrs = []
        syn_nndrs = []
        for i in range(len(norm_syn)):
            diff = norm_raw - norm_syn[i]
            dists = np.sqrt(np.sum(diff ** 2, axis=1))
            if len(dists) >= 2:
                smallest_two = np.partition(dists, 1)[:2]
                d1 = float(smallest_two[0])
                d2 = float(smallest_two[1])
                ratio = d1 / (d2 + 1e-9)
            else:
                d1 = float(np.min(dists))
                ratio = 1.0
            syn_dcrs.append(d1)
            syn_nndrs.append(ratio)

        syn_dcrs_arr = np.array(syn_dcrs)
        syn_nndrs_arr = np.array(syn_nndrs)

        # 2. Raw-internal baseline DCR (exclude self distance 0)
        raw_internal_dcrs = []
        n_raw = len(norm_raw)
        for i in range(n_raw):
            diff = norm_raw - norm_raw[i]
            dists = np.sqrt(np.sum(diff ** 2, axis=1))
            other_dists = np.delete(dists, i)
            if len(other_dists) > 0:
                raw_internal_dcrs.append(float(np.min(other_dists)))

        raw_dcrs_arr = np.array(raw_internal_dcrs) if raw_internal_dcrs else np.array([0.0])

        min_dcr = float(np.min(syn_dcrs_arr))
        median_dcr = float(np.median(syn_dcrs_arr))
        dcr_5th = float(np.percentile(syn_dcrs_arr, 5))

        raw_median_dcr = float(np.median(raw_dcrs_arr))
        raw_5th_dcr = float(np.percentile(raw_dcrs_arr, 5))

        nndr_median = float(np.median(syn_nndrs_arr))
        nndr_risk_rate = float(np.mean(syn_nndrs_arr < 0.2))

        # Proximity risk
        abs_risk_rate = float(np.mean(syn_dcrs_arr < 0.05))
        rel_risk_rate = float(np.mean(syn_dcrs_arr < (raw_5th_dcr * 0.5))) if raw_5th_dcr > 0 else abs_risk_rate
        combined_risk_rate = max(abs_risk_rate, rel_risk_rate)

        if min_dcr < 1e-4 or combined_risk_rate > 0.15 or nndr_risk_rate > 0.15:
            status = "FAIL"
        elif combined_risk_rate <= 0.05 and nndr_risk_rate <= 0.05:
            status = "PASS"
        else:
            status = "REVIEW"

        return {
            "median_dcr": round(median_dcr, 4),
            "min_dcr": round(min_dcr, 4),
            "dcr_5th_percentile": round(dcr_5th, 4),
            "raw_internal_dcr_median": round(raw_median_dcr, 4),
            "raw_internal_dcr_5th_percentile": round(raw_5th_dcr, 4),
            "nndr_median": round(nndr_median, 4),
            "nndr_risk_rate": round(nndr_risk_rate, 4),
            "absolute_proximity_risk_rate": round(abs_risk_rate, 4),
            "relative_proximity_risk_rate": round(rel_risk_rate, 4),
            "memorization_risk_rate": round(combined_risk_rate, 4),
            "status": status,
            "evaluated": True,
        }

    @staticmethod
    def evaluate_cap(
        raw: pd.DataFrame,
        synthetic: pd.DataFrame,
        plan: ColumnPlan,
        qi_columns: list[str] | None = None,
        sensitive_columns: list[str] | None = None,
        sample_size: int = 300,
    ) -> dict[str, Any]:
        """
        Evaluate Correct Attribution Probability (CAP) - Attribute Inference Risk.
        Assesses whether an attacker matching Quasi-Identifiers (QI) can correctly
        infer sensitive attributes of raw records using the synthetic dataset.
        """
        available_cols = set(raw.columns).intersection(synthetic.columns)
        if not available_cols:
            return {"status": "NOT_EVALUATED", "evaluated": False}

        # Auto-detect Quasi-Identifiers if not provided
        if not qi_columns:
            cand_qi = [c for c in plan.categorical if c in available_cols and 2 <= raw[c].nunique(dropna=True) <= 50]
            qi_columns = cand_qi[:3] if cand_qi else []
        else:
            qi_columns = [c for c in qi_columns if c in available_cols]

        # Auto-detect Sensitive Attribute candidate
        if not sensitive_columns:
            sensitive_keywords = ["질환", "소득", "자산", "금액", "등급", "병명", "사망", "체납", "임금", "보증금", "진단"]
            cand_sa = [c for c in available_cols if any(kw in c for kw in sensitive_keywords) and c not in qi_columns]
            if not cand_sa:
                cand_sa = [c for c in plan.categorical if c in available_cols and c not in qi_columns]
            sensitive_columns = cand_sa[:1] if cand_sa else []
        else:
            sensitive_columns = [c for c in sensitive_columns if c in available_cols]

        if not qi_columns or not sensitive_columns:
            return {
                "status": "SKIPPED",
                "evaluated": False,
                "reason": "적절한 준식별자(QI) 또는 민감속성(SA) 컬럼이 없습니다.",
            }

        target_sa = sensitive_columns[0]
        raw_eval = raw.dropna(subset=qi_columns + [target_sa]).head(sample_size)
        syn_eval = synthetic.dropna(subset=qi_columns + [target_sa])

        if len(raw_eval) < 1 or len(syn_eval) < 1:
            return {"status": "SKIPPED", "evaluated": False, "reason": "평가 행수 부족"}

        most_frequent_sa = raw[target_sa].mode().iloc[0] if len(raw[target_sa].mode()) > 0 else None
        baseline_success = (raw_eval[target_sa] == most_frequent_sa).mean()

        syn_grouped = syn_eval.groupby(qi_columns)[target_sa].agg(
            lambda s: s.mode().iloc[0] if len(s.mode()) > 0 else None
        ).to_dict()

        correct_attributions = 0
        matches_found = 0

        for _, row in raw_eval.iterrows():
            key = tuple(row[qi_columns].values)
            if len(qi_columns) == 1:
                key = key[0]

            inferred_sa = syn_grouped.get(key, None)
            if inferred_sa is not None:
                matches_found += 1
                if str(inferred_sa) == str(row[target_sa]):
                    correct_attributions += 1
            else:
                if str(most_frequent_sa) == str(row[target_sa]):
                    correct_attributions += 1

        cap = float(correct_attributions / len(raw_eval))
        inference_advantage = cap - float(baseline_success)

        if inference_advantage > 0.15:
            status = "FAIL"
        elif inference_advantage > 0.05:
            status = "REVIEW"
        else:
            status = "PASS"

        return {
            "cap": round(cap, 4),
            "baseline_cap": round(float(baseline_success), 4),
            "inference_advantage": round(inference_advantage, 4),
            "qi_columns": qi_columns,
            "sensitive_column": target_sa,
            "matches_found_rate": round(matches_found / len(raw_eval), 4),
            "status": status,
            "evaluated": True,
        }
