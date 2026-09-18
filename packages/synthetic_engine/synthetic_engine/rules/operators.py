# -*- coding: utf-8 -*-
"""범용 업무규칙 연산자.

이 모듈은 데이터셋 이름이나 특정 컬럼명을 알지 않고 ``DatasetRule``의
선언을 DataFrame 변환으로 실행한다. 업무 규칙은 카탈로그/프로파일에 두고,
여기에는 재사용 가능한 연산 의미만 둔다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .base import DatasetRule, RuleType
from .catalog import resolve_column_name
from .lag_sampling import sample_empirical_lags
from ..preprocessing.transformer import _format_date_like, _parse_date_series


@dataclass
class RuleExecutionContext:
    """규칙 실행에 필요한 외부 참조와 재현성 상태."""

    reference: pd.DataFrame | None = None
    rng: np.random.Generator = field(default_factory=np.random.default_rng)
    as_of: pd.Timestamp | None = None


def _resolve_column(frame: pd.DataFrame, name: Any) -> str | None:
    if name is None:
        return None
    if name in frame.columns:
        return str(name)
    return resolve_column_name(frame, [str(name)])


def _resolve_columns(frame: pd.DataFrame, names: list[Any]) -> list[str]:
    resolved: list[str] = []
    for name in names:
        column = _resolve_column(frame, name)
        if column and column not in resolved:
            resolved.append(column)
    return resolved


def _changed_rows(before: pd.Series, after: pd.Series) -> int:
    before_values = before.astype(object).where(before.notna(), None)
    after_values = after.astype(object).where(after.notna(), None)
    return int((before_values != after_values).fillna(False).sum())


def _condition_mask(frame: pd.DataFrame, rule: DatasetRule) -> tuple[pd.Series | None, str | None]:
    params = rule.params or {}
    condition_name = (
        params.get("condition_column")
        or params.get("when_column")
        or (rule.columns[0] if rule.columns else None)
    )
    condition_column = _resolve_column(frame, condition_name)
    if not condition_column:
        return None, None

    series = frame[condition_column]
    condition = str(params.get("condition") or params.get("operator") or "equals").lower()
    if condition in {"is_null", "null", "isna"}:
        return series.isna(), condition_column
    if condition in {"not_null", "notnull", "notna"}:
        return series.notna(), condition_column
    if condition in {"is_zero", "zero"}:
        return pd.to_numeric(series, errors="coerce").eq(0), condition_column
    if condition in {"not_zero", "nonzero"}:
        return pd.to_numeric(series, errors="coerce").ne(0), condition_column

    value = params.get("condition_value", params.get("condition_val"))
    if condition in {"in", "isin"}:
        values = params.get("condition_values", value)
        if not isinstance(values, (list, tuple, set, np.ndarray, pd.Series)):
            values = [values]
        return series.isin(list(values)), condition_column
    if condition in {"not_in", "notin"}:
        values = params.get("condition_values", value)
        if not isinstance(values, (list, tuple, set, np.ndarray, pd.Series)):
            values = [values]
        return ~series.isin(list(values)), condition_column

    if condition in {"gt", "greater_than", "gte", "greater_than_or_equal", "lt", "less_than", "lte", "less_than_or_equal"}:
        left = pd.to_numeric(series, errors="coerce")
        right = pd.to_numeric(pd.Series(value, index=frame.index), errors="coerce")
        if condition in {"gt", "greater_than"}:
            return left > right, condition_column
        if condition in {"gte", "greater_than_or_equal"}:
            return left >= right, condition_column
        if condition in {"lt", "less_than"}:
            return left < right, condition_column
        return left <= right, condition_column

    if value is None:
        return None, condition_column
    if params.get("numeric_compare"):
        left = pd.to_numeric(series, errors="coerce")
        right = pd.to_numeric(pd.Series(value, index=frame.index), errors="coerce")
        return left.eq(right), condition_column
    return series.astype("string").str.strip().eq(str(value).strip()), condition_column


def _value_for_column(frame: pd.DataFrame, column: str, value: Any) -> Any:
    """선언된 값 또는 dtype별 값을 현재 컬럼에 맞게 선택한다."""
    if not isinstance(value, dict):
        return value
    if "by_dtype" in value and isinstance(value["by_dtype"], dict):
        value = value["by_dtype"]
    if pd.api.types.is_numeric_dtype(frame[column]):
        return value.get("numeric", value.get("number", value.get("default")))
    return value.get("string", value.get("categorical", value.get("default")))


def _target_values(frame: pd.DataFrame, columns: list[str], params: dict[str, Any]) -> dict[str, Any]:
    configured = params.get("target_values")
    fallback = params.get("target_value", params.get("default_value"))
    result: dict[str, Any] = {}
    if isinstance(configured, dict):
        for column in columns:
            result[column] = configured.get(column, fallback)
    elif isinstance(configured, (list, tuple)):
        for index, column in enumerate(columns):
            result[column] = configured[index] if index < len(configured) else fallback
    else:
        result = {column: fallback for column in columns}
    return {column: _value_for_column(frame, column, value) for column, value in result.items()}


def _assign(frame: pd.DataFrame, mask: pd.Series, column: str, value: Any) -> int:
    if not mask.any() or column not in frame.columns:
        return 0
    before = frame[column].copy()
    if value is None:
        frame.loc[mask, column] = np.nan
    else:
        frame.loc[mask, column] = value
    return _changed_rows(before, frame[column])


def _expression(frame: pd.DataFrame, expression: Any) -> Any:
    """허용된 산술 연산만 지원하는 작은 선언형 표현식 평가기."""
    if isinstance(expression, str):
        column = _resolve_column(frame, expression)
        return frame[column] if column else expression
    if not isinstance(expression, dict):
        return expression

    if "column" in expression:
        column = _resolve_column(frame, expression["column"])
        return frame[column] if column else pd.Series(np.nan, index=frame.index)
    if "literal" in expression:
        return expression["literal"]

    op = str(expression.get("op", "")).lower()
    args = expression.get("args", [])
    values = [_expression(frame, item) for item in args]
    if op in {"sum", "add"}:
        if not values:
            return pd.Series(0, index=frame.index, dtype=float)
        result = values[0]
        for value in values[1:]:
            result = result + value
        return result
    if op in {"subtract", "sub"} and len(values) >= 2:
        return values[0] - values[1]
    if op in {"multiply", "mul"}:
        if not values:
            return pd.Series(1, index=frame.index, dtype=float)
        result = values[0]
        for value in values[1:]:
            result = result * value
        return result
    if op in {"divide", "div"} and len(values) >= 2:
        denominator = values[1].replace(0, np.nan) if isinstance(values[1], pd.Series) else values[1]
        return values[0] / denominator
    if op == "clip" and values:
        return pd.to_numeric(values[0], errors="coerce").clip(
            lower=expression.get("min"), upper=expression.get("max")
        )
    if op == "round" and values:
        return pd.to_numeric(values[0], errors="coerce").round(int(expression.get("digits", 0)))
    raise ValueError(f"지원하지 않는 규칙 표현식 연산자: {op}")


def _calculated_value(frame: pd.DataFrame, rule: DatasetRule, context: RuleExecutionContext) -> tuple[pd.Series | None, str | None]:
    params = rule.params or {}
    target = _resolve_column(frame, params.get("target_column") or (rule.columns[0] if rule.columns else None))
    if not target:
        return None, None

    if "expression" in params:
        value = _expression(frame, params["expression"])
        expected = pd.Series(value, index=frame.index) if not isinstance(value, pd.Series) else value
        return expected, target

    calculation = str(params.get("calculation", "")).lower()
    source_names = params.get("source_columns") or params.get("sources") or list(rule.columns[1:])
    source_columns = _resolve_columns(frame, list(source_names)) if isinstance(source_names, (list, tuple)) else []
    if calculation in {"sum", "sum_columns", "sum_arrears"}:
        if not source_columns:
            return None, target
        expected = frame[source_columns].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
    elif calculation in {"multiply", "product"}:
        if len(source_columns) < 2:
            return None, target
        expected = pd.to_numeric(frame[source_columns[0]], errors="coerce")
        for source in source_columns[1:]:
            expected = expected * pd.to_numeric(frame[source], errors="coerce")
    elif calculation in {"elapsed_months", "months_elapsed"}:
        source = _resolve_column(frame, params.get("source_column") or (source_names[0] if source_names else None))
        if not source:
            return None, target
        parsed = _parse_date_series(frame[source])
        as_of = params.get("as_of") or context.as_of or pd.Timestamp.now()
        as_of = pd.Timestamp(as_of)
        expected = (as_of.year - parsed.dt.year) * 12 + (as_of.month - parsed.dt.month)
    elif calculation in {"subtract", "difference"} and len(source_columns) >= 2:
        expected = pd.to_numeric(frame[source_columns[0]], errors="coerce") - pd.to_numeric(
            frame[source_columns[1]], errors="coerce"
        )
    elif calculation in {"work_hours", "base_minus_reduction"}:
        reduction = _resolve_column(frame, params.get("reduction_column") or (source_names[0] if source_names else None))
        if not reduction or params.get("base_hours") is None:
            return None, target
        expected = params["base_hours"] - pd.to_numeric(frame[reduction], errors="coerce")
        expected = expected.clip(lower=params.get("min_hours"), upper=params.get("max_hours"))
    else:
        return None, target

    if params.get("round_digits") is not None:
        expected = pd.to_numeric(expected, errors="coerce").round(int(params["round_digits"]))
    return pd.Series(expected, index=frame.index), target


def _apply_date_order(frame: pd.DataFrame, rule: DatasetRule, context: RuleExecutionContext) -> tuple[int, list[str]]:
    params = rule.params or {}
    before = _resolve_column(frame, params.get("before_column") or (rule.columns[0] if rule.columns else None))
    after = _resolve_column(frame, params.get("after_column") or (rule.columns[1] if len(rule.columns) > 1 else None))
    if not before or not after:
        return 0, []
    parsed_before = _parse_date_series(frame[before])
    parsed_after = _parse_date_series(frame[after])
    valid = parsed_before.notna() & parsed_after.notna()
    invalid = valid & (parsed_after < parsed_before)
    if not invalid.any():
        return 0, []
    lags = sample_empirical_lags(
        context.reference,
        before,
        after,
        int(invalid.sum()),
        random_state=context.rng,
        min_days=float(params.get("min_days", 1)),
        max_days=params.get("max_days"),
    )
    for position, index in enumerate(frame.index[invalid]):
        repaired = parsed_before.at[index] + pd.Timedelta(days=max(1, int(round(float(lags[position])))))
        frame.at[index, after] = _format_date_like(frame.at[index, after], repaired)
    return int(invalid.sum()), [after]


def _apply_min_max(frame: pd.DataFrame, rule: DatasetRule, context: RuleExecutionContext) -> tuple[int, list[str]]:
    params = rule.params or {}
    column = _resolve_column(frame, params.get("column") or (rule.columns[0] if rule.columns else None))
    if not column:
        return 0, []
    values = pd.to_numeric(frame[column], errors="coerce")
    before = frame[column].copy()
    minimum, maximum = params.get("min"), params.get("max")
    strategy = str(params.get("repair_strategy", "clip")).lower()
    repaired = values.copy()
    if strategy in {"smooth_upper_bound", "smooth_boundary"} and maximum is not None:
        over = values > float(maximum)
        if over.any():
            if pd.api.types.is_integer_dtype(frame[column]) or params.get("integer_values"):
                candidates = params.get("integer_values") or [int(maximum)]
                repaired.loc[over] = context.rng.choice(np.asarray(candidates), size=int(over.sum()), replace=True)
            else:
                width = params.get("smoothing_width", [0.01, 0.5])
                if isinstance(width, (int, float)):
                    width = [0.0, float(width)]
                repaired.loc[over] = float(maximum) - context.rng.uniform(float(width[0]), float(width[1]), size=int(over.sum()))
    else:
        repaired = repaired.clip(lower=minimum, upper=maximum)
    frame[column] = repaired
    return _changed_rows(before, frame[column]), [column]


def _apply_calculated(frame: pd.DataFrame, rule: DatasetRule, context: RuleExecutionContext) -> tuple[int, list[str]]:
    expected, target = _calculated_value(frame, rule, context)
    if expected is None or not target:
        return 0, []
    current = pd.to_numeric(frame[target], errors="coerce")
    expected_numeric = pd.to_numeric(expected, errors="coerce")
    valid = expected_numeric.notna()
    if pd.api.types.is_numeric_dtype(frame[target]) or current.notna().any():
        different = valid & ~np.isclose(current, expected_numeric, equal_nan=True)
    else:
        different = valid & frame[target].astype("string").ne(expected.astype("string"))
    before = frame[target].copy()
    frame.loc[valid, target] = expected.loc[valid]
    changed = max(_changed_rows(before, frame[target]), int(different.sum()))
    return changed, [target]


def _apply_custom(frame: pd.DataFrame, rule: DatasetRule) -> tuple[int, list[str]]:
    params = rule.params or {}
    mask, _ = _condition_mask(frame, rule)
    if mask is None:
        return 0, []
    target_names = params.get("target_columns")
    if target_names is None:
        target_names = [params.get("target_column") or params.get("required_column") or (rule.columns[1] if len(rule.columns) > 1 else None)]
    targets = _resolve_columns(frame, [name for name in target_names if name is not None])
    if not targets:
        return 0, []
    values = _target_values(frame, targets, params)
    total = 0
    for target in targets:
        target_mask = mask
        if rule.rule_type == RuleType.REQUIRED_IF:
            target_mask = mask & frame[target].isna()
        total += _assign(frame, target_mask, target, values.get(target))
    return total, targets


def _apply_rare_category(frame: pd.DataFrame, rule: DatasetRule) -> tuple[int, list[str]]:
    params = rule.params or {}
    column = _resolve_column(frame, params.get("column") or (rule.columns[0] if rule.columns else None))
    if not column or params.get("bin_size") is None:
        return 0, []
    before = frame[column].copy()
    numeric = pd.to_numeric(frame[column], errors="coerce")
    bin_size = float(params["bin_size"])
    binned = (numeric // bin_size) * bin_size
    frame[column] = binned.where(numeric.notna(), frame[column])
    return _changed_rows(before, frame[column]), [column]


def _apply_extreme_value(frame: pd.DataFrame, rule: DatasetRule, context: RuleExecutionContext) -> tuple[int, list[str]]:
    params = rule.params or {}
    columns = _resolve_columns(frame, list(params.get("columns") or rule.columns))
    if not columns:
        return 0, []
    total = 0
    changed_columns: list[str] = []
    if params.get("prevent_min_spike"):
        spike_value = params.get("spike_value")
        threshold = float(params.get("spike_threshold", 0.30))
        scale = float(params.get("scale", 500.0))
        offset = float(params.get("offset", 10.0))
        round_digits = params.get("round_digits", -1)
        for column in columns:
            numeric = pd.to_numeric(frame[column], errors="coerce")
            if spike_value is None or float(numeric.eq(float(spike_value)).mean()) <= threshold:
                continue
            mask = numeric.eq(float(spike_value))
            before = frame[column].copy()
            values = context.rng.exponential(scale=scale, size=int(mask.sum())) + offset
            if round_digits is not None:
                values = np.round(values, int(round_digits))
            frame.loc[mask, column] = values
            total += _changed_rows(before, frame[column])
            changed_columns.append(column)
        return total, changed_columns

    quantile = params.get("quantile")
    if quantile is None:
        return 0, []
    source = context.reference if isinstance(context.reference, pd.DataFrame) and not context.reference.empty else frame
    for column in columns:
        if column not in source.columns:
            continue
        source_values = pd.to_numeric(source[column], errors="coerce").dropna()
        if source_values.empty:
            continue
        upper = float(source_values.quantile(float(quantile)))
        before = frame[column].copy()
        numeric = pd.to_numeric(frame[column], errors="coerce")
        frame[column] = numeric.clip(upper=upper)
        changed = _changed_rows(before, frame[column])
        if changed:
            total += changed
            changed_columns.append(column)
    return total, changed_columns


def execute_rule(
    frame: pd.DataFrame,
    rule: DatasetRule,
    context: RuleExecutionContext,
) -> tuple[pd.DataFrame, int, list[str]]:
    """규칙 하나를 실행하고 변경 행 수와 대상 컬럼을 반환한다."""
    rule_type = rule.rule_type
    if rule_type in {
        RuleType.LESS_THAN_OR_EQUAL,
        RuleType.LESS_THAN,
        RuleType.GREATER_THAN_OR_EQUAL,
        RuleType.GREATER_THAN,
    }:
        params = rule.params or {}
        source_name = params.get("less_column") or params.get("greater_column") or (rule.columns[0] if rule.columns else None)
        target_name = params.get("greater_column") or params.get("less_column") or (rule.columns[1] if len(rule.columns) > 1 else None)
        source = _resolve_column(frame, source_name)
        target = _resolve_column(frame, target_name)
        if not source or not target:
            return frame, 0, []
        left = pd.to_numeric(frame[source], errors="coerce")
        right = pd.to_numeric(frame[target], errors="coerce")
        valid = left.notna() & right.notna()
        if rule_type in {RuleType.GREATER_THAN_OR_EQUAL, RuleType.GREATER_THAN}:
            invalid = valid & (left < right if rule_type == RuleType.GREATER_THAN_OR_EQUAL else left <= right)
            replacement = right.copy()
            if rule_type == RuleType.GREATER_THAN:
                replacement = np.nextafter(replacement.astype(float), np.inf)
        else:
            invalid = valid & (left > right if rule_type == RuleType.LESS_THAN_OR_EQUAL else left >= right)
            replacement = right.copy()
            if rule_type == RuleType.LESS_THAN:
                replacement = np.nextafter(replacement.astype(float), -np.inf)
        changed = int(invalid.sum())
        if changed:
            frame.loc[invalid, source] = replacement.loc[invalid]
        return frame, changed, [source] if changed else []

    if rule_type == RuleType.DATE_ORDER:
        changed, columns = _apply_date_order(frame, rule, context)
        return frame, changed, columns
    if rule_type in {RuleType.NULLABLE_IF, RuleType.REQUIRED_IF, RuleType.CUSTOM}:
        changed, columns = _apply_custom(frame, rule)
        return frame, changed, columns
    if rule_type == RuleType.MIN_MAX:
        changed, columns = _apply_min_max(frame, rule, context)
        return frame, changed, columns
    if rule_type == RuleType.CALCULATED_FIELD:
        changed, columns = _apply_calculated(frame, rule, context)
        return frame, changed, columns
    if rule_type == RuleType.RARE_CATEGORY:
        changed, columns = _apply_rare_category(frame, rule)
        return frame, changed, columns
    if rule_type == RuleType.EXTREME_VALUE:
        changed, columns = _apply_extreme_value(frame, rule, context)
        return frame, changed, columns
    if rule_type == RuleType.EQUALITY and len(rule.columns) >= 2:
        source = _resolve_column(frame, rule.columns[0])
        if not source:
            return frame, 0, []
        changed = 0
        columns: list[str] = []
        for name in rule.columns[1:]:
            target = _resolve_column(frame, name)
            if not target:
                continue
            changed += _changed_rows(frame[target], frame[source])
            frame[target] = frame[source]
            columns.append(target)
        return frame, changed, columns
    return frame, 0, []


__all__ = ["RuleExecutionContext", "execute_rule"]
