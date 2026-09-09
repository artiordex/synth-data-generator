# -*- coding: utf-8 -*-
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

QUASI_IDENTIFIER_COLUMN_PATTERN = re.compile(
    r"(이름|성명|name|전화|휴대|핸드폰|연락처|phone|mobile|tel|이메일|메일|email|e-mail|"
    r"주소|거주|거주지|소재지|지역|시도|시군구|읍면동|우편|주민|주민등록|rrn|ssn|"
    r"외국인|여권|운전면허|면허|계좌|사업자|법인|카드|차량|ip|아이피|"
    r"성별|성별코드|연령|연령대|나이|생년|출생|학교|고등학교|대학교|학년|반|"
    r"직위|직급|부서|소속|기관|회사|사업장|업종|직장|"
    r"학력|최종학력|전공|졸업|소득|가구|가구원|세대|가족|혼인|결혼|국적|장애|"
    r"질병|병력|건강|진단|회원|고객|학생|교사|담당자|작성자|대표자)",
    re.IGNORECASE,
)

JOB_IDENTIFIER_COLUMN_PATTERN = re.compile(r"^(현재)?(직업|직무|직종|직업명|직무명)$|^(직업|직무|직종)[_ -]?(분류|코드|유형|명)$")

GENERAL_INFORMATION_COLUMN_PATTERN = re.compile(
    r"(조사연도|연도|년도|월|일자|날짜|시점|기간|"
    r"경험|참여|만족|만족도|희망|수요|인식|여부|수준|점수|평가|정도|빈도|"
    r"의향|계획|선호|이용|사용|활용|응답|의견|관심|효과|필요|문항|"
    r"사고|침해|피해|심각도|상담|수업|교육|학습|진로|창업|대화|소통)",
    re.IGNORECASE,
)

INFORMATION_TYPES = {"준식별자", "일반정보"}

REGION_VALUE_PATTERN = re.compile(
    r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|"
    r"서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|"
    r"세종특별자치시|경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도|"
    r"제주특별자치도|전남광주)$"
)
GENDER_VALUES = {"남", "여", "남성", "여성", "m", "f", "male", "female"}
AGE_VALUE_PATTERN = re.compile(r"^(\d{1,3}\s*세|\d{1,2}\s*대|\d{1,3}\s*-\s*\d{1,3}|만\s*\d{1,3}\s*세)$")
SCHOOL_TYPE_VALUES = {"일반고", "특성화고", "자율고", "특목고", "마이스터고", "중학교", "고등학교", "대학교", "대학원"}
EDUCATION_VALUE_PATTERN = re.compile(r"(무학|초졸|중졸|고졸|전문대|대졸|석사|박사|재학|졸업|중퇴)")
INCOME_VALUE_PATTERN = re.compile(r"(\d+\s*분위|소득|만원|원|상위|하위|중위|저소득|고소득)")
HOUSEHOLD_VALUE_PATTERN = re.compile(r"^(\d+\s*인|\d+\s*명|1인가구|2인가구|3인가구|4인가구|5인이상)")
JOB_VALUE_PATTERN = re.compile(r"(관리자|전문가|사무|서비스|판매|농림|어업|기능원|장치|기계|조립|단순노무|군인|학생|주부|무직|자영업|회사원|공무원|교사)")


def normalize_information_type(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text in INFORMATION_TYPES:
        return text
    if any(keyword in text for keyword in ("식별자", "개인정보", "민감", "고유식별", "위치", "인구통계")):
        return "준식별자"
    if any(keyword in text for keyword in ("일반", "응답", "설문", "이용", "경험", "만족", "수요")):
        return "일반정보"
    return None


def value_match_ratio(series: pd.Series, pattern: re.Pattern[str] | set[str], sample_size: int = 200) -> float:
    values = series.dropna().astype(str).map(lambda v: re.sub(r"\s+", "", v.strip())).head(sample_size)
    values = values[values != ""]
    if values.empty:
        return 0.0
    if isinstance(pattern, set):
        lowered = {str(value).lower() for value in pattern}
        return float(values.map(lambda value: value.lower() in lowered).mean())
    return float(values.map(lambda value: bool(pattern.search(value))).mean())


def has_quasi_identifier_values(series: pd.Series) -> bool:
    non_null = int(series.notna().sum())
    if non_null == 0:
        return False

    checks = [
        (REGION_VALUE_PATTERN, 0.6),
        (GENDER_VALUES, 0.8),
        (AGE_VALUE_PATTERN, 0.6),
        (SCHOOL_TYPE_VALUES, 0.6),
        (EDUCATION_VALUE_PATTERN, 0.5),
        (INCOME_VALUE_PATTERN, 0.5),
        (HOUSEHOLD_VALUE_PATTERN, 0.5),
        (JOB_VALUE_PATTERN, 0.5),
    ]
    return any(value_match_ratio(series, pattern) >= threshold for pattern, threshold in checks)


def classify_information_type(column: Any, series: pd.Series | None = None, pii_detected: bool = False) -> str:
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
        if non_null >= 20 and unique_ratio >= 0.8:
            return "준식별자"

    return "일반정보"


def read_table(path: Path | str, sheet_name: str | int = 0) -> pd.DataFrame:
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
    from synthetic_engine.privacy.masker import SmartMasker
    detected: dict[str, dict[str, Any]] = {}

    for column in df.columns:
        for pii_type, pattern in PII_COLUMN_PATTERNS.items():
            if pattern.search(str(column)):
                detected[column] = {"action": "smart_mask", "faker": pii_type, "consistent_mapping": True, "detected_by": "column_name"}
                break

        if column in detected:
            continue

        sample = df[column].dropna().astype(str).head(200)
        found_pure = False
        for pii_type, pattern in PII_VALUE_PATTERNS.items():
            hits = sample.map(lambda value: bool(pattern.search(value))).mean() if len(sample) else 0
            if hits >= 0.3:
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
