# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: analyzer.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/analyzer.py
# 목적: 데이터 구조·개인정보·정보 유형을 분석하고 처리 계획을 생성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan
from ..rules.profile_registry import default_engine_settings


_ENGINE_SETTINGS = default_engine_settings()
_SEMANTIC_SETTINGS = _ENGINE_SETTINGS.get("semantic", {})
_PROFILING_SETTINGS = _ENGINE_SETTINGS.get("profiling", {})


def _configured_patterns(key: str, *, flags: int = 0) -> dict[str, re.Pattern[str]]:
    return {
        name: re.compile(str(pattern), flags)
        for name, pattern in (_SEMANTIC_SETTINGS.get(key, {}) or {}).items()
    }


PII_COLUMN_PATTERNS = _configured_patterns("pii_column_patterns", flags=re.IGNORECASE)
PII_VALUE_PATTERNS = _configured_patterns("pii_value_patterns")
QUASI_IDENTIFIER_COLUMN_PATTERN = re.compile(
    str(_SEMANTIC_SETTINGS.get("quasi_identifier_column_pattern", "")), re.IGNORECASE
)
JOB_IDENTIFIER_COLUMN_PATTERN = re.compile(
    str(_SEMANTIC_SETTINGS.get("job_identifier_column_pattern", "")), re.IGNORECASE
)
GENERAL_INFORMATION_COLUMN_PATTERN = re.compile(
    str(_SEMANTIC_SETTINGS.get("general_information_column_pattern", "")), re.IGNORECASE
)
INFORMATION_TYPES = set(_SEMANTIC_SETTINGS.get("information_types", []))
REGION_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("region_value_pattern", "")))
GENDER_VALUES = set(_SEMANTIC_SETTINGS.get("gender_values", []))
AGE_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("age_value_pattern", "")))
SCHOOL_TYPE_VALUES = set(_SEMANTIC_SETTINGS.get("school_type_values", []))
EDUCATION_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("education_value_pattern", "")))
INCOME_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("income_value_pattern", "")))
HOUSEHOLD_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("household_value_pattern", "")))
JOB_VALUE_PATTERN = re.compile(str(_SEMANTIC_SETTINGS.get("job_value_pattern", "")))


# information type 데이터를 표준 형식으로 정규화함
def normalize_information_type(value: Any) -> str | None:
    """정보 유형 입력값을 준식별자 또는 일반정보로 정규화함"""
    text = str(value or "").strip()
    if not text:
        return None
    if text in INFORMATION_TYPES:
        return text
    if any(keyword in text for keyword in _SEMANTIC_SETTINGS.get("normalize_quasi_keywords", [])):
        return "준식별자"
    if any(keyword in text for keyword in _SEMANTIC_SETTINGS.get("normalize_general_keywords", [])):
        return "일반정보"
    return None


# value match ratio 작업을 수행함
def value_match_ratio(series: pd.Series, pattern: re.Pattern[str] | set[str], sample_size: int = 200) -> float:
    """컬럼 값이 지정 패턴과 일치하는 비율을 계산함"""
    values = series.dropna().astype(str).map(lambda v: re.sub(r"\s+", "", v.strip())).head(sample_size)
    values = values[values != ""]
    if values.empty:
        return 0.0
    if isinstance(pattern, set):
        lowered = {str(value).lower() for value in pattern}
        return float(values.map(lambda value: value.lower() in lowered).mean())
    return float(values.map(lambda value: bool(pattern.search(value))).mean())


# quasi identifier values 보유 여부를 확인함
def has_quasi_identifier_values(series: pd.Series) -> bool:
    """컬럼 값에 준식별자 특성이 있는지 확인함"""
    non_null = int(series.notna().sum())
    if non_null == 0:
        return False

    thresholds = _SEMANTIC_SETTINGS.get("quasi_value_thresholds", {}) or {}
    checks = [
        (REGION_VALUE_PATTERN, float(thresholds.get("region", 0.6))),
        (GENDER_VALUES, float(thresholds.get("gender", 0.8))),
        (AGE_VALUE_PATTERN, float(thresholds.get("age", 0.6))),
        (SCHOOL_TYPE_VALUES, float(thresholds.get("school_type", 0.6))),
        (EDUCATION_VALUE_PATTERN, float(thresholds.get("education", 0.5))),
        (INCOME_VALUE_PATTERN, float(thresholds.get("income", 0.5))),
        (HOUSEHOLD_VALUE_PATTERN, float(thresholds.get("household", 0.5))),
        (JOB_VALUE_PATTERN, float(thresholds.get("job", 0.5))),
    ]
    sample_size = int(_PROFILING_SETTINGS.get("quasi_sample_size", 200))
    return any(value_match_ratio(series, pattern, sample_size=sample_size) >= threshold for pattern, threshold in checks)


# classify information type 작업을 수행함
def classify_information_type(column: Any, series: pd.Series | None = None, pii_detected: bool = False) -> str:
    """컬럼명과 값의 특성으로 정보 유형을 분류함"""
    name = str(column or "").strip()
    if pii_detected:
        return "준식별자"

    if JOB_IDENTIFIER_COLUMN_PATTERN.search(name):
        return "준식별자"

    if QUASI_IDENTIFIER_COLUMN_PATTERN.search(name):
        return "준식별자"

    if series is not None and has_quasi_identifier_values(series):
        return "준식별자"

    if GENERAL_INFORMATION_COLUMN_PATTERN.search(name):
        return "일반정보"

    if series is not None:
        non_null = int(series.notna().sum())
        unique = int(series.nunique(dropna=True))
        unique_ratio = unique / max(non_null, 1)
        if non_null >= int(_PROFILING_SETTINGS.get("unique_identifier_min_rows", 20)) and unique_ratio >= float(
            _PROFILING_SETTINGS.get("unique_identifier_ratio", 0.8)
        ):
            return "준식별자"

    return "일반정보"


# read 표(테이블) 작업을 수행함
def _legacy_read_table(path: Path | str, sheet_name: str | int = 0) -> pd.DataFrame:
    """지원 파일 형식을 판별해 데이터프레임으로 읽음"""
    path = Path(path)
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
                return pd.read_csv(path, sep="	", encoding=encoding)
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

    # Document files (PDF, HWP, HWPX, HWPT, DOCX, DOC, MD)
    if suffix in {".pdf", ".hwp", ".hwpx", ".hwpt", ".docx", ".doc", ".md"}:
        return _read_document_as_dataframe(path)

    raise ValueError(f"Unsupported input file type: {suffix} (지원 형식: CSV, XLSX, XLS, TSV, JSON, PARQUET, PDF, HWP, HWPX, HWPT, DOCX, MD)")


# 한글(HWP) 텍스트 pure 요소를 추출하여 반환함
def _extract_hwp_text_pure(path: Path) -> list[str]:
    """Pure-python fallback to extract text from HWP binary stream using olefile & zlib."""
    lines = []
    try:
        import olefile
        import zlib
        import struct
        ole = olefile.OleFileIO(str(path))
        sec_names = sorted([p for p in ole.listdir() if len(p) >= 2 and p[0] == "BodyText" and p[1].startswith("Section")])
        for sec_p in sec_names:
            sec_bytes = ole.openstream(sec_p).read()
            try:
                decomp = zlib.decompress(sec_bytes, -15)
            except Exception:
                try:
                    decomp = zlib.decompress(sec_bytes)
                except Exception:
                    continue
            pos = 0
            while pos + 4 <= len(decomp):
                header = struct.unpack("<I", decomp[pos:pos + 4])[0]
                pos += 4
                tag_id = header & 0x3FF
                size = (header >> 20) & 0xFFF
                if size == 0xFFF:
                    if pos + 4 > len(decomp):
                        break
                    size = struct.unpack("<I", decomp[pos:pos + 4])[0]
                    pos += 4
                if pos + size > len(decomp):
                    break
                payload = decomp[pos:pos + size]
                pos += size
                if tag_id == 67:  # HWPTAG_STRING / HWPTAG_TEXT
                    txt = payload.decode("utf-16le", errors="ignore").strip()
                    if txt:
                        for l in txt.splitlines():
                            l_clean = l.strip()
                            if l_clean:
                                lines.append(l_clean)
        ole.close()
    except Exception:
        pass
    return lines


# read document as dataframe 작업을 수행함
def _read_document_as_dataframe(path: Path) -> pd.DataFrame:
    """Extract structured tabular data or sequential text paragraphs from document files into a DataFrame."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            import pdfplumber
            tables = []
            with pdfplumber.open(str(path.resolve())) as pdf:
                for page in pdf.pages:
                    for raw_t in page.extract_tables():
                        if raw_t and len(raw_t) > 1:
                            tables.append(raw_t)
            if tables:
                largest = max(tables, key=lambda t: len(t) * max(len(r) for r in t))
                header = [str(c).strip() if c else f"컬럼_{i+1}" for i, c in enumerate(largest[0])]
                rows = []
                for r in largest[1:]:
                    padded_r = [(str(c).strip() if c is not None else "") for c in r]
                    if any(padded_r):
                        if len(padded_r) < len(header):
                            padded_r += [""] * (len(header) - len(padded_r))
                        rows.append(padded_r[:len(header)])
                if rows:
                    return pd.DataFrame(rows, columns=header)

            with pdfplumber.open(str(path.resolve())) as pdf:
                all_text = []
                for p in pdf.pages:
                    txt = p.extract_text() or ""
                    all_text.extend([line.strip() for line in txt.splitlines() if line.strip()])
                if all_text:
                    return pd.DataFrame({"문단번호": list(range(1, len(all_text) + 1)), "문서_내용": all_text})
        except Exception:
            pass

    elif suffix in {".docx", ".doc"}:
        try:
            import docx
            doc = docx.Document(path)
            if doc.tables:
                largest_tbl = max(doc.tables, key=lambda t: len(t.rows) * len(t.columns))
                rows = []
                for r in largest_tbl.rows:
                    cells = [c.text.strip().replace("\n", " ") for c in r.cells]
                    if any(cells):
                        rows.append(cells)
                if len(rows) > 1:
                    max_cols = max(len(r) for r in rows)
                    padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                    header = [h if h else f"컬럼_{i+1}" for i, h in enumerate(padded_rows[0])]
                    return pd.DataFrame(padded_rows[1:], columns=header)

            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if paragraphs:
                return pd.DataFrame({"문단번호": list(range(1, len(paragraphs) + 1)), "문서_내용": paragraphs})
        except Exception:
            pass

    elif suffix == ".hwpx":
        try:
            hp_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
            with zipfile.ZipFile(path, "r") as zf:
                section_names = sorted([n for n in zf.namelist() if "section" in n.lower() and n.endswith(".xml")])
                tbl_rows = []
                for s_name in section_names:
                    root = ET.fromstring(zf.read(s_name))
                    for tbl in root.findall(".//hp:tbl", hp_ns):
                        for tr in tbl.findall(".//hp:tr", hp_ns):
                            row_cells = []
                            for tc in tr.findall(".//hp:tc", hp_ns):
                                text = "".join([t.text for t in tc.findall(".//hp:t", hp_ns) if t.text]).strip()
                                row_cells.append(text)
                            if any(row_cells):
                                tbl_rows.append(row_cells)
                if len(tbl_rows) >= 2:
                    header = [h if h else f"컬럼_{i+1}" for i, h in enumerate(tbl_rows[0])]
                    ncols = len(header)
                    data = [r[:ncols] + [""] * max(0, ncols - len(r)) for r in tbl_rows[1:]]
                    return pd.DataFrame(data, columns=header)

                paragraphs = []
                for s_name in section_names:
                    root = ET.fromstring(zf.read(s_name))
                    for p in root.findall(".//hp:p", hp_ns):
                        runs = [t.text for t in p.findall(".//hp:t", hp_ns) if t.text]
                        p_txt = "".join(runs).strip()
                        if p_txt:
                            paragraphs.append(p_txt)
                if paragraphs:
                    return pd.DataFrame({"문단번호": list(range(1, len(paragraphs) + 1)), "문서_내용": paragraphs})
        except Exception:
            pass

    elif suffix in {".hwp", ".hwpt"}:
        try:
            res = subprocess.run(["hwp5txt", str(path)], capture_output=True)
            txt = res.stdout.decode("utf-8", errors="ignore").strip()
            if txt:
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                return pd.DataFrame({"문단번호": list(range(1, len(lines) + 1)), "문서_내용": lines})
        except Exception:
            pass

        # Pure Python OLE fallback for HWP
        pure_lines = _extract_hwp_text_pure(path)
        if pure_lines:
            return pd.DataFrame({"문단번호": list(range(1, len(pure_lines) + 1)), "문서_내용": pure_lines})

    elif suffix == ".md":
        try:
            lines = [l.strip() for l in path.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
            table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
            if len(table_lines) >= 2:
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip("|").split("|")]
                    if all(re.match(r"^:?-+:?$", c) for c in cells):
                        continue
                    rows.append(cells)
                if len(rows) >= 2:
                    header = [h if h else f"컬럼_{i+1}" for i, h in enumerate(rows[0])]
                    ncols = len(header)
                    data = [r[:ncols] + [""] * max(0, ncols - len(r)) for r in rows[1:]]
                    return pd.DataFrame(data, columns=header)
            if lines:
                return pd.DataFrame({"문단번호": list(range(1, len(lines) + 1)), "문서_내용": lines})
        except Exception:
            pass

    return pd.DataFrame({"문서_내용": ["문서 내용을 파싱할 수 없습니다."]})


# infer 컬럼 목록 작업을 수행함
def read_table(path: Path | str, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read an input table through the shared profiling reader boundary.

    The public import path remains ``analyzer.read_table`` while
    format-specific loading is implemented in ``table_reader``.
    """
    from .table_reader import read_table as _read_table

    return _read_table(path, sheet_name=sheet_name)


def infer_columns(df: pd.DataFrame, ignored: list[str]) -> tuple[list[str], list[str]]:
    """데이터프레임 컬럼을 범주형과 수치형으로 추론함"""
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

        if numeric_ratio >= float(_PROFILING_SETTINGS.get("numeric_ratio", 0.9)) and unique_ratio > float(
            _PROFILING_SETTINGS.get("numeric_unique_ratio", 0.05)
        ):
            numerical.append(column)
        else:
            categorical.append(column)

    return categorical, numerical


# scan 개인식별정보(PII) 컬럼 목록 작업을 수행함
def scan_pii_columns(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """컬럼명·값·본문 패턴으로 개인정보 후보 컬럼을 탐지함"""
    from synthetic_engine.privacy.masker import SmartMasker
    detected: dict[str, dict[str, Any]] = {}

    for column in df.columns:
        for pii_type, pattern in PII_COLUMN_PATTERNS.items():
            if pattern.search(str(column)):
                detected[column] = {"action": "smart_mask", "faker": pii_type, "consistent_mapping": True, "detected_by": "column_name"}
                break

        if column in detected:
            continue

        sample = df[column].dropna().astype(str).head(int(_PROFILING_SETTINGS.get("pii_sample_size", 200)))
        found_pure = False
        for pii_type, pattern in PII_VALUE_PATTERNS.items():
            hits = sample.map(lambda value: bool(pattern.search(value))).mean() if len(sample) else 0
            if hits >= float(_PROFILING_SETTINGS.get("pii_value_hit_ratio", 0.3)):
                detected[column] = {"action": "smart_mask", "faker": pii_type, "consistent_mapping": True, "detected_by": "value_pattern"}
                found_pure = True
                break

        if found_pure or column in detected:
            continue

        # Check for inline PII in narrative/mixed text cells (e.g. PDF/HWP/Word documents)
        inline_hits = sample.map(lambda v: bool(SmartMasker.mask_full_text(str(v)) != str(v))).sum() if len(sample) else 0
        if inline_hits > 0:
            detected[column] = {
                "action": "smart_mask",
                "faker": "unstructured_text",
                "consistent_mapping": True,
                "detected_by": "inline_content",
                "inline_hits": int(inline_hits)
            }

    return detected


# 컬럼 plan 구조를 생성 및 조립함
def build_column_plan(config: dict[str, Any], df: pd.DataFrame) -> ColumnPlan:
    """설정과 분석 결과를 합쳐 컬럼별 처리 계획을 생성함"""
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
    configured_categorical = columns_config.get("categorical")
    configured_numerical = columns_config.get("numerical")
    categorical = list(inferred_categorical if configured_categorical is None else configured_categorical)
    numerical = list(inferred_numerical if configured_numerical is None else configured_numerical)

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
