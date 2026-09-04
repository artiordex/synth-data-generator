# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan

PII_COLUMN_PATTERNS = {
    "name": re.compile(r"(이름|성명|name)", re.IGNORECASE),
    "phone_number": re.compile(r"(전화|휴대|핸드폰|연락처|phone|mobile|tel)", re.IGNORECASE),
    "email": re.compile(r"(이메일|메일|email)", re.IGNORECASE),
    "address": re.compile(r"(주소|address)", re.IGNORECASE),
    "ssn": re.compile(r"(주민|주민등록|rrn|ssn|resident)", re.IGNORECASE),
    "account": re.compile(r"(계좌|account)", re.IGNORECASE),
}

PII_VALUE_PATTERNS = {
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "phone_number": re.compile(r"^(01[016789]|02|0[3-6][1-5])[-\s]?\d{3,4}[-\s]?\d{4}$"),
    "ssn": re.compile(r"^\d{6}[-\s]?[1-4]\d{6}$"),
}

def read_table(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    if suffix == ".csv":
        last_error = None
        for encoding in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise last_error or ValueError(f"Unable to read CSV file: {path}")
    if suffix in {".tsv", ".txt"}:
        last_error = None
        for encoding in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(path, sep="\t", encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise last_error or ValueError(f"Unable to read delimited text file: {path}")

    raise ValueError(f"Unsupported input file type: {suffix}")

def infer_columns(df: pd.DataFrame, ignored: list[str]) -> tuple[list[str], list[str]]:
    categorical: list[str] = []
    numerical: list[str] = []

    for column in df.columns:
        if column in ignored:
            continue

        series = df[column]
        numeric = pd.to_numeric(series, errors="coerce")
        non_null = series.notna().sum()
        numeric_ratio = 0.0 if non_null == 0 else float(numeric.notna().sum() / non_null)
        unique_ratio = float(series.nunique(dropna=True) / max(non_null, 1))

        if numeric_ratio >= 0.9 and unique_ratio > 0.05:
            numerical.append(column)
        else:
            categorical.append(column)

    return categorical, numerical

def scan_pii_columns(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    detected: dict[str, dict[str, Any]] = {}

    for column in df.columns:
        for pii_type, pattern in PII_COLUMN_PATTERNS.items():
            if pattern.search(str(column)):
                detected[column] = {"action": "faker", "faker": pii_type, "consistent_mapping": True, "detected_by": "column_name"}
                break

        if column in detected:
            continue

        sample = df[column].dropna().astype(str).head(200)
        for pii_type, pattern in PII_VALUE_PATTERNS.items():
            hits = sample.map(lambda value: bool(pattern.search(value))).mean() if len(sample) else 0
            if hits >= 0.3:
                detected[column] = {"action": "faker", "faker": pii_type, "consistent_mapping": True, "detected_by": "value_pattern"}
                break

    return detected

def build_column_plan(config: dict[str, Any], df: pd.DataFrame) -> ColumnPlan:
    columns_config = config.get("columns", {})
    selected = columns_config.get("selected")
    ignored = list(columns_config.get("ignore", []))

    if selected is not None:
        selected_set = set(selected)
        for col in df.columns:
            if col not in selected_set and col not in ignored:
                ignored.append(col)

    detected_pii = scan_pii_columns(df)
    configured_pii = columns_config.get("pii", {})
    pii = {**detected_pii, **configured_pii}

    if selected is not None:
        pii = {k: v for k, v in pii.items() if k in selected_set}

    ignored = sorted(set(ignored + list(pii.keys())))
    inferred_categorical, inferred_numerical = infer_columns(df, ignored)
    categorical = list(columns_config.get("categorical", inferred_categorical))
    numerical = list(columns_config.get("numerical", inferred_numerical))

    for column in ignored:
        if column in categorical:
            categorical.remove(column)
        if column in numerical:
            numerical.remove(column)

    rules = dict(columns_config.get("rules", {}))
    for column in rules:
        if column not in categorical and column not in numerical:
            categorical.append(column)

    return ColumnPlan(categorical=categorical, numerical=numerical, ignored=ignored, pii=pii, rules=rules)
