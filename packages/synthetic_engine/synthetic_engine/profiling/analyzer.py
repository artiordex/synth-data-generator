# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan

PII_COLUMN_PATTERNS = {
    "name": re.compile(r"(이름|성명|name|대표자|담당자|작성자|고객명|환자명|회원명)", re.IGNORECASE),
    "phone_number": re.compile(r"(전화|휴대|핸드폰|연락처|phone|mobile|tel|hp)", re.IGNORECASE),
    "email": re.compile(r"(이메일|메일|email|e-mail)", re.IGNORECASE),
    "address": re.compile(r"(주소|address|거주지|도로명|소재지|배송지)", re.IGNORECASE),
    "ssn": re.compile(r"(주민|주민등록|rrn|ssn|resident)", re.IGNORECASE),
    "account": re.compile(r"(계좌|account|계좌번호|환불계좌)", re.IGNORECASE),
    "foreigner_id": re.compile(r"(외국인|외국인등록|alien|arc)", re.IGNORECASE),
    "passport": re.compile(r"(여권|여권번호|passport)", re.IGNORECASE),
    "driver_license": re.compile(r"(운전면허|면허번호|driver.*licen)", re.IGNORECASE),
    "business_number": re.compile(r"(사업자|사업자등록|사업자번호|biz_no|business_number)", re.IGNORECASE),
    "corporate_number": re.compile(r"(법인|법인등록|법인번호|corporate_number)", re.IGNORECASE),
    "credit_card": re.compile(r"(카드|카드번호|신용카드|credit_card|card_number)", re.IGNORECASE),
    "car_plate": re.compile(r"(차량|차량번호|자동차번호|plate|vehicle)", re.IGNORECASE),
    "ip_address": re.compile(r"(ip|ip_address|아이피|접속ip|방문ip)", re.IGNORECASE),
}

PII_VALUE_PATTERNS = {
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "phone_number": re.compile(r"^(01[016789]|02|0[3-6][1-5])[-\s]?\d{3,4}[-\s]?\d{4}$"),
    "ssn": re.compile(r"^\d{6}[-\s]?[1-4]\d{6}$"),
    "foreigner_id": re.compile(r"^\d{6}[-\s]?[5-8]\d{6}$"),
    "passport": re.compile(r"^[a-zA-Z]\d{8}$"),
    "driver_license": re.compile(r"^\d{2}[-\s]?\d{2}[-\s]?\d{6}[-\s]?\d{2}$"),
    "business_number": re.compile(r"^\d{3}[-\s]?\d{2}[-\s]?\d{5}$"),
    "corporate_number": re.compile(r"^\d{6}[-\s]?\d{7}$"),
    "credit_card": re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"),
    "car_plate": re.compile(r"^(\d{2,3}[가-힣]\s?\d{4}|[가-힣]{2}\d{2}[가-힣]\s?\d{4})$"),
    "ip_address": re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"),
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
    if suffix in {".json", ".jsonl"}:
        try:
            return pd.read_json(path)
        except Exception:
            try:
                return pd.read_json(path, lines=True)
            except Exception:
                import json
                with open(path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                if isinstance(data, list):
                    return pd.json_normalize(data)
                elif isinstance(data, dict):
                    for k in ["data", "records", "items", "rows", "values"]:
                        if k in data and isinstance(data[k], list):
                            return pd.json_normalize(data[k])
                    return pd.DataFrame(data)
                raise ValueError(f"Unable to parse JSON file as tabular dataset: {path}")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)

    raise ValueError(f"Unsupported input file type: {suffix} (지원 형식: CSV, XLSX, XLS, TSV, JSON, PARQUET)")

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
