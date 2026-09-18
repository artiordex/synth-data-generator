# -*- coding: utf-8 -*-
"""Post-DP domain projection using public or explicitly supplied metadata."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..common.catalog import DomainCatalog
from ..common.types import ColumnPlan
from ..rules.base import DatasetSchemaConfig, RuleType


def _merge_spec(target: dict[str, Any], source: Any) -> None:
    if isinstance(source, dict):
        target.update({key: value for key, value in source.items() if value is not None})
    elif isinstance(source, (tuple, list)) and len(source) >= 2:
        target.update({"min": source[0], "max": source[1]})


def _schema_spec(schema: DatasetSchemaConfig | Any, column: str) -> dict[str, Any]:
    if schema is None:
        return {}
    result: dict[str, Any] = {}
    for attribute in ("public_bounds", "domain_constraints"):
        _merge_spec(result, getattr(schema, attribute, {}).get(column))
    for rule in getattr(schema, "rules", []) or []:
        if column not in getattr(rule, "columns", []):
            continue
        params = dict(getattr(rule, "params", {}) or {})
        if rule.rule_type == RuleType.MIN_MAX or "min" in params or "max" in params:
            _merge_spec(result, params)
    return result


def _public_catalog_spec(column: str) -> dict[str, Any]:
    try:
        domain = DomainCatalog.infer_domain_by_name(column)
    except Exception:
        return {}
    rule = domain.get("rule", {}) if isinstance(domain, dict) else {}
    if not isinstance(rule, dict) or not ({"min", "max", "allowed_values"} & set(rule)):
        return {}
    result = dict(rule)
    result["source"] = "public_catalog"
    return result


def _resolve_spec(
    column: str,
    plan: ColumnPlan,
    schema: DatasetSchemaConfig | None,
) -> tuple[dict[str, Any], str]:
    schema_spec = _schema_spec(schema, column)
    if schema_spec:
        return schema_spec, "schema_or_policy"

    plan_spec = plan.rules.get(column, {}) if isinstance(plan.rules, dict) else {}
    if isinstance(plan_spec, dict):
        for key in ("public_bound", "public_bounds", "domain", "bounds"):
            if key in plan_spec:
                public_spec: dict[str, Any] = {}
                _merge_spec(public_spec, plan_spec[key])
                public_spec.update({k: v for k, v in plan_spec.items() if k in {"integer", "non_negative", "allowed_values"}})
                if public_spec:
                    return public_spec, "user_or_public_metadata"
        explicit = {key: value for key, value in plan_spec.items() if key in {
            "min", "max", "integer", "non_negative", "allowed_values", "dp_min", "dp_max",
        }}
        if explicit:
            if "dp_min" in explicit or "dp_max" in explicit:
                explicit.setdefault("min", explicit.pop("dp_min", None))
                explicit.setdefault("max", explicit.pop("dp_max", None))
                return explicit, "dp_safe_metadata"
            return explicit, "user_or_public_metadata"

    catalog_spec = _public_catalog_spec(column)
    if catalog_spec:
        return catalog_spec, "public_catalog"
    return {}, "no_bound"


def project_domain_constraints(
    df: pd.DataFrame,
    plan: ColumnPlan,
    schema: DatasetSchemaConfig | None = None,
    return_report: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
    """Project generated values onto explicitly known domains.

    Raw data is intentionally not an argument: exact raw minima/maxima are not
    a permissible fallback bound.  With no public or user constraint, values
    remain untouched except for no-op type normalization.
    """
    output = df.copy()
    report: dict[str, Any] = {
        "columns": {},
        "raw_exact_minmax_used": False,
        "status": "PASS",
    }
    columns = list(dict.fromkeys((plan.numerical or []) + (plan.categorical or [])))
    for column in columns:
        if column not in output.columns:
            continue
        spec, source = _resolve_spec(column, plan, schema)
        if not spec:
            continue
        before = output[column].copy()
        numeric = column in (plan.numerical or []) or pd.api.types.is_numeric_dtype(output[column])
        info = {
            "source": source,
            "violations_before": 0,
            "violations_after": 0,
            "integer": bool(spec.get("integer", False)),
        }
        if numeric:
            values = pd.to_numeric(output[column], errors="coerce")
            valid = values.notna()
            minimum = spec.get("min")
            maximum = spec.get("max")
            if spec.get("non_negative") and minimum is None:
                minimum = 0
            if minimum is not None:
                info["violations_before"] += int((valid & (values < float(minimum))).sum())
            if maximum is not None:
                info["violations_before"] += int((valid & (values > float(maximum))).sum())
            if spec.get("integer"):
                values = values.round()
            if minimum is not None:
                values = values.clip(lower=float(minimum))
            if maximum is not None:
                values = values.clip(upper=float(maximum))
            allowed = spec.get("allowed_values")
            if allowed:
                allowed_numbers = np.asarray(allowed, dtype=float)
                invalid = values.notna() & ~values.isin(allowed_numbers)
                if invalid.any():
                    values.loc[invalid] = values.loc[invalid].map(
                        lambda value: float(allowed_numbers[np.argmin(np.abs(allowed_numbers - float(value)))])
                    )
            if spec.get("integer"):
                output[column] = values.astype("Int64")
            else:
                output[column] = values
            final_values = pd.to_numeric(output[column], errors="coerce")
            final_valid = final_values.notna()
            if minimum is not None:
                info["violations_after"] += int((final_valid & (final_values < float(minimum))).sum())
            if maximum is not None:
                info["violations_after"] += int((final_valid & (final_values > float(maximum))).sum())
        else:
            allowed = list(spec.get("allowed_values") or [])
            if allowed:
                valid = output[column].isin(allowed) | output[column].isna()
                info["violations_before"] = int((~valid).sum())
                fallback = allowed[0]
                output.loc[~valid, column] = fallback
                info["violations_after"] = int((~(output[column].isin(allowed) | output[column].isna())).sum())
        report["columns"][column] = info

    if any(info["violations_after"] for info in report["columns"].values()):
        report["status"] = "FAIL_SAFE"
    return (output, report) if return_report else output


__all__ = ["project_domain_constraints"]
