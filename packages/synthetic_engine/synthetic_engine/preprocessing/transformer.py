# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan

def constraint_null_columns(constraints: list[dict[str, Any]]) -> set[str]:
    return {
        constraint["column"]
        for constraint in constraints
        if constraint.get("type") == "null_indicator" and "column" in constraint
    }

def prepare_training_frame(df: pd.DataFrame, plan: ColumnPlan, constraints: list[dict[str, Any]], reference: pd.DataFrame | None = None) -> pd.DataFrame:
    training = pd.DataFrame(index=df.index)
    preserve_nulls = constraint_null_columns(constraints)

    for column in plan.categorical:
        if column in plan.rules:
            continue
        training[column] = df[column].astype("string")

    for column in plan.numerical:
        if column in plan.rules:
            continue
        training[column] = pd.to_numeric(df[column], errors="coerce")
        if column not in preserve_nulls and training[column].isna().any():
            median = pd.to_numeric(reference[column], errors='coerce').median() if reference is not None else training[column].median()
            training[column] = training[column].fillna(0 if pd.isna(median) else median)

    return training

def apply_constraints_before_training(df: pd.DataFrame, constraints: list[dict[str, Any]], plan: ColumnPlan) -> tuple[pd.DataFrame, ColumnPlan]:
    output = df.copy()
    categorical = list(plan.categorical)

    for constraint in constraints:
        if constraint.get("type") != "null_indicator":
            continue

        column = constraint["column"]
        indicator = constraint["indicator_column"]
        null_label = constraint.get("null_label", "비적용")
        not_null_label = constraint.get("not_null_label", "적용")

        if column not in output.columns or column not in plan.categorical + plan.numerical:
            raise ValueError(f"결측 의미 보존 대상이 학습 컬럼에 없습니다: {column}")
        if column in output.columns:
            if column in plan.numerical:
                output[column] = pd.to_numeric(output[column], errors="coerce")
            output[indicator] = np.where(output[column].isna(), null_label, not_null_label)
            if indicator not in categorical:
                categorical.append(indicator)

    return output, ColumnPlan(categorical, plan.numerical, plan.ignored, plan.pii, plan.rules)

def apply_constraints_after_generation(df: pd.DataFrame, constraints: list[dict[str, Any]]) -> pd.DataFrame:
    output = df.copy()

    for constraint in constraints:
        c_type = constraint.get("type")
        if c_type == "null_indicator":
            continue  # Enforce after all value repairs below.

        elif c_type in {"greater_than", "inequality"}:
            high_col = constraint.get("high_column") or constraint.get("greater_column")
            low_col = constraint.get("low_column") or constraint.get("less_column")
            if high_col in output.columns and low_col in output.columns:
                val_high = pd.to_numeric(output[high_col], errors="coerce")
                val_low = pd.to_numeric(output[low_col], errors="coerce")
                mask = val_high < val_low
                if mask.any():
                    output.loc[mask, [high_col, low_col]] = output.loc[mask, [low_col, high_col]].values

        elif c_type == "range":
            col = constraint.get("column")
            if col in output.columns:
                min_v = constraint.get("min")
                max_v = constraint.get("max")
                num_series = pd.to_numeric(output[col], errors="coerce")
                if min_v is not None:
                    num_series = num_series.clip(lower=min_v)
                if max_v is not None:
                    num_series = num_series.clip(upper=max_v)
                output[col] = num_series

        elif c_type == "implication":
            if_col = constraint.get("if_column")
            if_val = constraint.get("if_value")
            then_col = constraint.get("then_column")
            then_val = constraint.get("then_value")
            if if_col in output.columns and then_col in output.columns:
                output.loc[output[if_col].astype(str) == str(if_val), then_col] = then_val

    if "수축기혈압" in output.columns and "이완기혈압" in output.columns:
        sys_bp = pd.to_numeric(output["수축기혈압"], errors="coerce")
        dia_bp = pd.to_numeric(output["이완기혈압"], errors="coerce")
        swap_mask = (sys_bp.notna()) & (dia_bp.notna()) & (sys_bp < dia_bp)
        if swap_mask.any():
            output.loc[swap_mask, ["수축기혈압", "이완기혈압"]] = output.loc[swap_mask, ["이완기혈압", "수축기혈압"]].values

    # Other repairs can change a null-constrained column; enforce its meaning
    # on the final candidate before it is accepted.
    for constraint in constraints:
        if constraint.get("type") == "null_indicator":
            column, indicator = constraint["column"], constraint["indicator_column"]
            if column not in output or indicator not in output:
                raise ValueError(f"결측 제약조건 컬럼이 생성 결과에 없습니다: {column}, {indicator}")
            null_label = constraint.get("null_label", "비적용")
            not_null_label = constraint.get("not_null_label", "적용")
            output.loc[output[indicator] == null_label, column] = np.nan
            valid = output[indicator].isin([null_label, not_null_label])
            invalid = (output[indicator] == not_null_label) & output[column].isna()
            output = output.loc[valid & ~invalid].copy()
    return output
