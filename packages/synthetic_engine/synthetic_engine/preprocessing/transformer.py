# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: transformer.py
# 경로: packages/synthetic_engine/synthetic_engine/preprocessing/transformer.py
# 목적: 학습 전후 데이터 제약조건과 변환을 처리함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
from typing import Any
import re
import warnings
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan
from ..rules.profile_registry import default_engine_settings

_ENGINE_SETTINGS = default_engine_settings()
_TEMPORAL_SETTINGS = _ENGINE_SETTINGS.get("temporal", {})
_LABEL_SETTINGS = _ENGINE_SETTINGS.get("labels", {})
_DATE_PARSEABLE_RATIO = float(_TEMPORAL_SETTINGS.get("parseable_ratio", 0.6))
_DATE_NAME_PATTERN = re.compile(str(_TEMPORAL_SETTINGS.get("date_name_pattern", "")), re.IGNORECASE)
_BIRTH_PATTERN = re.compile(str(_TEMPORAL_SETTINGS.get("birth_pattern", "")), re.IGNORECASE)
_DATE_VALUE_PATTERN = re.compile(str(_TEMPORAL_SETTINGS.get("date_value_pattern", "")))
_START_PATTERNS = {
    group: re.compile(str(pattern), re.IGNORECASE)
    for group, pattern in (_TEMPORAL_SETTINGS.get("start_patterns", {}) or {}).items()
}
_END_PATTERNS = {
    group: re.compile(str(pattern), re.IGNORECASE)
    for group, pattern in (_TEMPORAL_SETTINGS.get("end_patterns", {}) or {}).items()
}


# date 텍스트 데이터를 정제 및 정리함
def _clean_date_text(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("년", "-").replace("월", "-").replace("일", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# date series 데이터를 분석하여 파싱함
def _parse_date_series(series: pd.Series) -> pd.Series:
    """Parse common Korean, ISO and compact date values without raising."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    values = series.copy()
    if pd.api.types.is_numeric_dtype(values):
        as_text = values.dropna().astype("Int64", errors="ignore").astype(str)
        compact_ratio = float(as_text.str.fullmatch(r"\d{8}").mean()) if len(as_text) else 0.0
        if compact_ratio >= _DATE_PARSEABLE_RATIO:
            return pd.to_datetime(values.astype("Int64", errors="ignore").astype(str), format="%Y%m%d", errors="coerce")
        return pd.to_datetime(values, errors="coerce")

    text = values.astype("string").map(lambda value: pd.NA if pd.isna(value) else _clean_date_text(value))
    compact = text.str.replace(r"\D", "", regex=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(text, errors="coerce")
    compact_mask = parsed.isna() & compact.str.fullmatch(r"\d{8}", na=False)
    if compact_mask.any():
        parsed.loc[compact_mask] = pd.to_datetime(compact.loc[compact_mask], format="%Y%m%d", errors="coerce")
    return parsed


# parseable date ratio 작업을 수행함
def _parseable_date_ratio(series: pd.Series) -> float:
    non_empty = series.dropna()
    if non_empty.empty:
        return 0.0
    text = non_empty.astype(str).str.strip()
    non_empty = non_empty.loc[text != ""]
    if non_empty.empty:
        return 0.0
    if not pd.api.types.is_datetime64_any_dtype(non_empty) and not text.map(lambda value: bool(_DATE_VALUE_PATTERN.search(value))).any():
        return 0.0
    return float(_parse_date_series(non_empty).notna().mean())


# format date like 작업을 수행함
def _format_date_like(original: Any, value: pd.Timestamp) -> Any:
    if pd.isna(original):
        return value.date().isoformat()
    if isinstance(original, pd.Timestamp):
        return value
    text = str(original)
    if re.fullmatch(r"\d{8}", text.strip()):
        return value.strftime("%Y%m%d")
    if "년" in text and "월" in text:
        if re.search(r"\d{4}년\s*\d{2}월\s*\d{2}일", text):
            return value.strftime("%Y년 %m월 %d일")
        return f"{value.year}년 {value.month}월 {value.day}일"
    if "/" in text:
        return value.strftime("%Y/%m/%d")
    if "." in text:
        return value.strftime("%Y.%m.%d")
    if re.search(r"\d{1,2}:\d{2}", text):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value.date().isoformat()


# 컬럼 date role 작업을 수행함
def _column_date_role(column: str, series: pd.Series | None = None) -> tuple[str | None, str | None]:
    name = str(column)
    if series is not None and not _DATE_NAME_PATTERN.search(name) and _parseable_date_ratio(series) < _DATE_PARSEABLE_RATIO:
        return None, None
    if _BIRTH_PATTERN.search(name):
        return "birth", "person"
    for group, pattern in _START_PATTERNS.items():
        if pattern.search(name):
            return "start", group
    for group, pattern in _END_PATTERNS.items():
        if pattern.search(name):
            return "end", group
    if _DATE_NAME_PATTERN.search(name) or (series is not None and _parseable_date_ratio(series) >= _DATE_PARSEABLE_RATIO):
        return "event", "generic"
    return None, None


# constraint key 작업을 수행함
def _constraint_key(constraint: dict[str, Any]) -> tuple[Any, ...]:
    return (
        constraint.get("type"),
        constraint.get("column"),
        constraint.get("before_column"),
        constraint.get("after_column"),
        constraint.get("birth_column"),
        constraint.get("reference_column"),
    )


# infer temporal constraints 작업을 수행함
def infer_temporal_constraints(
    df: pd.DataFrame,
    columns: list[str] | set[str] | None = None,
    existing: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Infer conservative temporal rules from column names and parseable values."""
    selected = [column for column in df.columns if columns is None or column in set(columns)]
    roles: dict[str, tuple[str, str]] = {}
    for column in selected:
        role, group = _column_date_role(str(column), df[column])
        if role and group:
            roles[column] = (role, group)

    inferred: list[dict[str, Any]] = []
    birth_columns = [column for column, (role, _) in roles.items() if role == "birth"]
    start_columns = [column for column, (role, _) in roles.items() if role == "start"]
    end_columns = [column for column, (role, _) in roles.items() if role == "end"]

    for start in start_columns:
        start_group = roles[start][1]
        partners = [end for end in end_columns if roles[end][1] == start_group]
        if not partners and len(start_columns) == 1 and len(end_columns) == 1:
            partners = end_columns
        for end in partners:
            inferred.append({
                "type": "date_order",
                "before_column": start,
                "after_column": end,
                "allow_equal": True,
                "min_days": 0,
                "source": "auto_temporal_inference",
            })

    reference_columns = start_columns + end_columns
    for birth in birth_columns:
        for reference in reference_columns:
            min_years = int(
                _TEMPORAL_SETTINGS.get("employment_min_years", 15)
                if roles[reference][1] == "employment"
                else _TEMPORAL_SETTINGS.get("default_min_years", 0)
            )
            inferred.append({
                "type": "age_at_least",
                "birth_column": birth,
                "reference_column": reference,
                "min_years": min_years,
                "max_years": int(_TEMPORAL_SETTINGS.get("max_years", 120)),
                "source": "auto_temporal_inference",
            })

    seen = {_constraint_key(constraint) for constraint in existing or []}
    unique: list[dict[str, Any]] = []
    for constraint in inferred:
        key = _constraint_key(constraint)
        if key in seen:
            continue
        seen.add(key)
        unique.append(constraint)
    return unique


# apply date order 작업을 수행함
def _apply_date_order(output: pd.DataFrame, constraint: dict[str, Any]) -> pd.DataFrame:
    before_col = (
        constraint.get("before_column")
        or constraint.get("start_column")
        or constraint.get("low_column")
        or constraint.get("less_column")
    )
    after_col = (
        constraint.get("after_column")
        or constraint.get("end_column")
        or constraint.get("high_column")
        or constraint.get("greater_column")
    )
    if before_col not in output.columns or after_col not in output.columns:
        return output

    before = _parse_date_series(output[before_col])
    after = _parse_date_series(output[after_col])
    min_days = int(constraint.get("min_days", 0 if constraint.get("allow_equal", True) else 1))
    max_days = constraint.get("max_days")
    min_after = before + pd.to_timedelta(min_days, unit="D")
    valid = before.notna() & after.notna()
    too_early = valid & (after < min_after)
    too_late = pd.Series(False, index=output.index)
    if max_days is not None:
        max_after = before + pd.to_timedelta(int(max_days), unit="D")
        too_late = valid & (after > max_after)

    if constraint.get("on_violation") == "drop":
        return output.loc[~(too_early | too_late)].copy()

    if too_early.any():
        for index in output.index[too_early]:
            output.at[index, after_col] = _format_date_like(output.at[index, after_col], min_after.at[index])
    if max_days is not None and too_late.any():
        for index in output.index[too_late]:
            output.at[index, after_col] = _format_date_like(output.at[index, after_col], max_after.at[index])
    return output


# shift years 작업을 수행함
def _shift_years(value: pd.Timestamp, years: int) -> pd.Timestamp:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


# apply age 변환 규칙 작업을 수행함
def _apply_age_rule(output: pd.DataFrame, constraint: dict[str, Any]) -> pd.DataFrame:
    birth_col = constraint.get("birth_column") or constraint.get("column")
    reference_col = constraint.get("reference_column") or constraint.get("as_of_column")
    if birth_col not in output.columns or reference_col not in output.columns:
        return output

    birth = _parse_date_series(output[birth_col])
    reference = _parse_date_series(output[reference_col])
    valid = birth.notna() & reference.notna()
    min_years = int(constraint.get("min_years", 0))
    max_years = constraint.get("max_years")
    min_birth = reference.map(lambda value: pd.NaT if pd.isna(value) else _shift_years(value, -min_years))
    too_young = valid & (birth > min_birth)
    too_old = pd.Series(False, index=output.index)
    if max_years is not None:
        max_birth = reference.map(lambda value: pd.NaT if pd.isna(value) else _shift_years(value, -int(max_years)))
        too_old = valid & (birth < max_birth)

    if constraint.get("on_violation") == "drop":
        return output.loc[~(too_young | too_old)].copy()

    if too_young.any():
        for index in output.index[too_young]:
            repaired = _shift_years(reference.at[index], -min_years)
            output.at[index, birth_col] = _format_date_like(output.at[index, birth_col], repaired)
    if max_years is not None and too_old.any():
        for index in output.index[too_old]:
            repaired = _shift_years(reference.at[index], -int(max_years))
            output.at[index, birth_col] = _format_date_like(output.at[index, birth_col], repaired)
    return output


# apply date range 작업을 수행함
def _apply_date_range(output: pd.DataFrame, constraint: dict[str, Any]) -> pd.DataFrame:
    column = constraint.get("column")
    if column not in output.columns:
        return output
    values = _parse_date_series(output[column])
    minimum = pd.to_datetime(constraint.get("min") or constraint.get("start"), errors="coerce")
    maximum = pd.to_datetime(constraint.get("max") or constraint.get("end"), errors="coerce")
    valid = values.notna()
    too_low = valid & pd.Series(False, index=output.index)
    too_high = valid & pd.Series(False, index=output.index)
    if pd.notna(minimum):
        too_low = valid & (values < minimum)
    if pd.notna(maximum):
        too_high = valid & (values > maximum)
    if constraint.get("on_violation") == "drop":
        return output.loc[~(too_low | too_high)].copy()
    for index in output.index[too_low]:
        output.at[index, column] = _format_date_like(output.at[index, column], minimum)
    for index in output.index[too_high]:
        output.at[index, column] = _format_date_like(output.at[index, column], maximum)
    return output

# constraint null 컬럼 목록 작업을 수행함
def constraint_null_columns(constraints: list[dict[str, Any]]) -> set[str]:
    """결측값 표시 제약조건이 적용된 컬럼을 추출함"""
    return {
        constraint["column"]
        for constraint in constraints
        if constraint.get("type") == "null_indicator" and "column" in constraint
    }

# prepare training frame 작업을 수행함
def prepare_training_frame(df: pd.DataFrame, plan: ColumnPlan, constraints: list[dict[str, Any]], reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """합성 모델 학습에 사용할 데이터프레임을 준비함"""
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

# apply constraints before training 작업을 수행함
def apply_constraints_before_training(df: pd.DataFrame, constraints: list[dict[str, Any]], plan: ColumnPlan) -> tuple[pd.DataFrame, ColumnPlan]:
    """모델 학습 전에 입력 데이터와 처리 계획에 제약조건을 적용함"""
    output = df.copy()
    categorical = list(plan.categorical)

    for constraint in constraints:
        if constraint.get("type") != "null_indicator":
            continue

        column = constraint["column"]
        indicator = constraint["indicator_column"]
        null_label = constraint.get("null_label", _LABEL_SETTINGS.get("null_indicator", "비적용"))
        not_null_label = constraint.get("not_null_label", _LABEL_SETTINGS.get("not_null_indicator", "적용"))

        if column not in output.columns or column not in plan.categorical + plan.numerical:
            raise ValueError(f"결측 의미 보존 대상이 학습 컬럼에 없습니다: {column}")
        if column in output.columns:
            if column in plan.numerical:
                output[column] = pd.to_numeric(output[column], errors="coerce")
            output[indicator] = np.where(output[column].isna(), null_label, not_null_label)
            if indicator not in categorical:
                categorical.append(indicator)

    return output, ColumnPlan(categorical, plan.numerical, plan.ignored, plan.pii, plan.rules)

# apply constraints after generation 작업을 수행함
def apply_constraints_after_generation(df: pd.DataFrame, constraints: list[dict[str, Any]]) -> pd.DataFrame:
    """생성된 데이터에 후처리 제약조건을 적용함"""
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
                numeric_mask = val_high.notna() & val_low.notna()
                if numeric_mask.any():
                    mask = numeric_mask & (val_high < val_low)
                    if mask.any():
                        output.loc[mask, [high_col, low_col]] = output.loc[mask, [low_col, high_col]].values
                else:
                    output = _apply_date_order(output, {
                        **constraint,
                        "type": "date_order",
                        "before_column": low_col,
                        "after_column": high_col,
                    })

        elif c_type == "date_order":
            output = _apply_date_order(output, constraint)

        elif c_type == "age_at_least":
            output = _apply_age_rule(output, constraint)

        elif c_type == "date_range":
            output = _apply_date_range(output, constraint)

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

    # Other repairs can change a null-constrained column; enforce its meaning
    # on the final candidate before it is accepted.
    for constraint in constraints:
        if constraint.get("type") == "null_indicator":
            column, indicator = constraint["column"], constraint["indicator_column"]
            if column not in output or indicator not in output:
                raise ValueError(f"결측 제약조건 컬럼이 생성 결과에 없습니다: {column}, {indicator}")
            null_label = constraint.get("null_label", _LABEL_SETTINGS.get("null_indicator", "비적용"))
            not_null_label = constraint.get("not_null_label", _LABEL_SETTINGS.get("not_null_indicator", "적용"))
            output.loc[output[indicator] == null_label, column] = np.nan
            valid = output[indicator].isin([null_label, not_null_label])
            invalid = (output[indicator] == not_null_label) & output[column].isna()
            output = output.loc[valid & ~invalid].copy()
    return output
