# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: faker.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/faker.py
# 목적: 컬럼 유형과 문맥을 반영한 일관 가명값을 생성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
import hashlib
import random
from typing import Any
import pandas as pd
from faker import Faker
from ..common.types import ColumnPlan
from ..rules.profile_registry import default_engine_settings
from .token_vault import project_token
from .masker import SmartMasker


_ENGINE_SETTINGS = default_engine_settings()
_PRIVACY_SETTINGS = _ENGINE_SETTINGS["privacy"]
_CONTEXT_COLUMNS = _PRIVACY_SETTINGS["context_columns"]
_GENDER_SETTINGS = _PRIVACY_SETTINGS["gender"]
_IDENTITY_SETTINGS = _PRIVACY_SETTINGS["identity"]
_PHONE_SETTINGS = _PRIVACY_SETTINGS["phone"]
_REGION_PREFIXES = {
    str(region): str(prefix)
    for region, prefix in _PHONE_SETTINGS["region_prefixes"].items()
}


def _setting_list(value: Any) -> list[str]:
    """설정 파일의 문자열 목록을 가명 생성용 목록으로 정규화함."""
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [str(value).strip()]


def _contains_any(value: Any, tokens: list[str]) -> bool:
    normalized = "" if value is None else str(value).strip().lower()
    return any(token.lower() in normalized for token in tokens if token)


def _gender_matches(value: Any, token_key: str, exact_key: str) -> bool:
    normalized = "" if value is None else str(value).strip().lower()
    contains = _setting_list(_GENDER_SETTINGS[token_key])
    exact = {token.lower() for token in _setting_list(_GENDER_SETTINGS[exact_key])}
    return _contains_any(normalized, contains) or normalized in exact


_AGE_CONTEXT_COLUMNS = _setting_list(_CONTEXT_COLUMNS["age"])
_GENDER_CONTEXT_COLUMNS = _setting_list(_CONTEXT_COLUMNS["gender"])
_REGION_CONTEXT_COLUMNS = _setting_list(_CONTEXT_COLUMNS["region"])
_MIN_AGE = int(_IDENTITY_SETTINGS["min_age"])
_MAX_AGE = int(_IDENTITY_SETTINGS["max_age"])
_FALLBACK_BIRTH_YEAR = int(_IDENTITY_SETTINGS["fallback_birth_year"])
_LANDLINE_COLUMN_TOKENS = _setting_list(_PHONE_SETTINGS["landline_column_tokens"])
_DEFAULT_LANDLINE_PREFIX = str(_PHONE_SETTINGS["default_landline_prefix"])
_MOBILE_PREFIX = str(_PHONE_SETTINGS["mobile_prefix"])
_PASSPORT_PREFIXES = _setting_list(_PRIVACY_SETTINGS["passport_prefixes"])
_DRIVER_LICENSE_REGION_CODES = _setting_list(_PRIVACY_SETTINGS["driver_license_region_codes"])
_CAR_PLATE_HANGUL = _setting_list(_PRIVACY_SETTINGS["car_plate_hangul"])


# repeat source series 작업을 수행함
def _repeat_source_series(raw: pd.DataFrame, column: str, length: int) -> pd.Series:
    """Return source values repeated to the synthetic row count."""
    if column not in raw.columns or length <= 0:
        return pd.Series([None] * max(length, 0))
    source = raw[column].reset_index(drop=True)
    if source.empty:
        return pd.Series([None] * length)
    return pd.Series([source.iloc[idx % len(source)] for idx in range(length)])

class ContextAwareFaker:
    """행과 컬럼 문맥을 사용해 개인정보 가명값을 생성함"""

    @staticmethod
    def _reference_year(reference_date: Any = None) -> int:
        """기준일이 없으면 실행일을 사용하되 특정 연도를 고정하지 않는다."""
        try:
            return int(pd.Timestamp(reference_date).year) if reference_date is not None else int(pd.Timestamp.now().year)
        except (TypeError, ValueError):
            return int(pd.Timestamp.now().year)

    # context value 요소를 추출하여 반환함
    @staticmethod
    def extract_context_value(row: Any, target_columns: list[str]) -> Any:
        """행에서 대상 컬럼과 일치하는 문맥 값을 추출함"""
        if isinstance(row, dict):
            for col in target_columns:
                for k, v in row.items():
                    if col.lower() in str(k).lower() and pd.notna(v):
                        return v
        elif hasattr(row, "index"):
            for col in target_columns:
                for k in row.index:
                    if col.lower() in str(k).lower() and pd.notna(row[k]):
                        return row[k]
        return None

    # coherent ssn 데이터를 생성하여 반환함
    @classmethod
    def generate_coherent_ssn(cls, age_val: Any, gender_val: Any, reference_date: Any = None) -> str:
        """연령·성별 문맥을 반영한 주민등록번호 형식 값을 생성함"""
        current_year = cls._reference_year(reference_date)
        birth_year = _FALLBACK_BIRTH_YEAR
        if age_val is not None:
            try:
                age_int = int(float(age_val))
                if _MIN_AGE <= age_int <= _MAX_AGE:
                    birth_year = current_year - age_int
            except Exception:
                pass

        yy = f"{birth_year % 100:02d}"
        mm = f"{random.randint(1, 12):02d}"
        dd = f"{random.randint(1, 28):02d}"
        front = f"{yy}{mm}{dd}"

        is_female = False
        if gender_val is not None:
            is_female = _gender_matches(gender_val, "female_tokens", "female_exact_values")

        gender_digit = ("2" if is_female else "1") if birth_year < 2000 else ("4" if is_female else "3")
        back_tail = f"{random.randint(100000, 999999):06d}"
        return f"{front}-{gender_digit}{back_tail}"

    # coherent phone 데이터를 생성하여 반환함
    @classmethod
    def generate_coherent_phone(cls, col_name: str, region_val: Any) -> str:
        """컬럼명과 지역 문맥을 반영한 전화번호 형식 값을 생성함"""
        region = str(region_val or "").strip()
        if _contains_any(col_name, _LANDLINE_COLUMN_TOKENS):
            code = next(
                (prefix for region_token, prefix in _REGION_PREFIXES.items() if region_token in region),
                _DEFAULT_LANDLINE_PREFIX,
            )
        else:
            code = _MOBILE_PREFIX

        mid = random.randint(2000, 9999)
        last = random.randint(1000, 9999)
        return f"{code}-{mid}-{last:04d}"

    # coherent foreigner id 데이터를 생성하여 반환함
    @classmethod
    def generate_coherent_foreigner_id(cls, age_val: Any, gender_val: Any, reference_date: Any = None) -> str:
        """연령·성별 문맥을 반영한 외국인등록번호 형식 값을 생성함"""
        current_year = cls._reference_year(reference_date)
        birth_year = _FALLBACK_BIRTH_YEAR
        if age_val is not None:
            try:
                age_int = int(float(age_val))
                if _MIN_AGE <= age_int <= _MAX_AGE:
                    birth_year = current_year - age_int
            except Exception:
                pass

        yy = f"{birth_year % 100:02d}"
        mm = f"{random.randint(1, 12):02d}"
        dd = f"{random.randint(1, 28):02d}"
        front = f"{yy}{mm}{dd}"

        is_female = False
        if gender_val is not None:
            is_female = _gender_matches(gender_val, "female_tokens", "female_exact_values")

        gender_digit = ("6" if is_female else "5") if birth_year < 2000 else ("8" if is_female else "7")
        back_tail = f"{random.randint(100000, 999999):06d}"
        return f"{front}-{gender_digit}{back_tail}"

    # passport 데이터를 생성하여 반환함
    @classmethod
    def generate_passport(cls) -> str:
        """여권번호 형식의 가명값을 생성함"""
        letter = random.choice(_PASSPORT_PREFIXES)
        digits = f"{random.randint(10000000, 99999999):08d}"
        return f"{letter}{digits}"

    # driver license 데이터를 생성하여 반환함
    @classmethod
    def generate_driver_license(cls) -> str:
        """운전면허번호 형식의 가명값을 생성함"""
        region_code = random.choice(_DRIVER_LICENSE_REGION_CODES)
        yy = f"{random.randint(0, 26):02d}"
        serial = f"{random.randint(100000, 999999):06d}"
        chk = f"{random.randint(10, 99):02d}"
        return f"{region_code}-{yy}-{serial}-{chk}"

    # business number 데이터를 생성하여 반환함
    @classmethod
    def generate_business_number(cls) -> str:
        """사업자등록번호 형식의 가명값을 생성함"""
        part1 = f"{random.randint(100, 999):03d}"
        part2 = f"{random.randint(10, 99):02d}"
        part3 = f"{random.randint(10000, 99999):05d}"
        return f"{part1}-{part2}-{part3}"

    # corporate number 데이터를 생성하여 반환함
    @classmethod
    def generate_corporate_number(cls) -> str:
        """법인등록번호 형식의 가명값을 생성함"""
        part1 = f"{random.randint(100000, 999999):06d}"
        part2 = f"{random.randint(1000000, 9999999):07d}"
        return f"{part1}-{part2}"

    # credit card 데이터를 생성하여 반환함
    @classmethod
    def generate_credit_card(cls) -> str:
        """카드번호 형식의 가명값을 생성함"""
        p1 = f"{random.randint(1000, 9999):04d}"
        p2 = f"{random.randint(1000, 9999):04d}"
        p3 = f"{random.randint(1000, 9999):04d}"
        p4 = f"{random.randint(1000, 9999):04d}"
        return f"{p1}-{p2}-{p3}-{p4}"

    # car plate 데이터를 생성하여 반환함
    @classmethod
    def generate_car_plate(cls) -> str:
        """차량번호 형식의 가명값을 생성함"""
        num = random.choice([f"{random.randint(10, 99):02d}", f"{random.randint(100, 999):03d}"])
        hangeul = random.choice(_CAR_PLATE_HANGUL)
        tail = f"{random.randint(1000, 9999):04d}"
        return f"{num}{hangeul} {tail}"

    # ip address 데이터를 생성하여 반환함
    @classmethod
    def generate_ip_address(cls, fake: Faker) -> str:
        """IP 주소 형식의 가명값을 생성함"""
        return fake.ipv4() if hasattr(fake, "ipv4") else f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    # faker value coherent 작업을 수행함
    @classmethod
    def faker_value_coherent(
        cls,
        fake: Faker,
        provider: str,
        col_name: str,
        row: Any,
        reference_date: Any = None,
    ) -> Any:
        """개인정보 제공자 유형에 맞는 문맥 기반 가명값을 생성함"""
        if provider == "ssn":
            age = cls.extract_context_value(row, _AGE_CONTEXT_COLUMNS)
            gender = cls.extract_context_value(row, _GENDER_CONTEXT_COLUMNS)
            return cls.generate_coherent_ssn(age, gender, reference_date=reference_date)

        if provider == "foreigner_id":
            age = cls.extract_context_value(row, _AGE_CONTEXT_COLUMNS)
            gender = cls.extract_context_value(row, _GENDER_CONTEXT_COLUMNS)
            return cls.generate_coherent_foreigner_id(age, gender, reference_date=reference_date)

        if provider == "passport":
            return cls.generate_passport()

        if provider == "driver_license":
            return cls.generate_driver_license()

        if provider == "business_number":
            return cls.generate_business_number()

        if provider == "corporate_number":
            return cls.generate_corporate_number()

        if provider == "credit_card":
            return cls.generate_credit_card()

        if provider == "car_plate":
            return cls.generate_car_plate()

        if provider == "ip_address":
            return cls.generate_ip_address(fake)

        if provider == "phone_number":
            region = cls.extract_context_value(row, _REGION_CONTEXT_COLUMNS)
            return cls.generate_coherent_phone(col_name, region)

        if provider == "name":
            gender = cls.extract_context_value(row, _GENDER_CONTEXT_COLUMNS)
            if gender:
                if _gender_matches(gender, "female_tokens", "female_exact_values"):
                    return fake.name_female() if hasattr(fake, "name_female") else fake.name()
                if _gender_matches(gender, "male_tokens", "male_exact_values"):
                    return fake.name_male() if hasattr(fake, "name_male") else fake.name()
            return fake.name()

        if provider == "email": return fake.email()
        if provider == "address": return fake.address().replace("\n", " ")
        if provider == "account": return fake.bban()
        return fake.word()

# apply 개인식별정보(PII) 작업을 수행함
def apply_pii(
    df: pd.DataFrame,
    plan: ColumnPlan,
    seed: int = 42,
    project_id: str = "default",
    key_version: str = "v1",
    locale: str = "ko_KR",
    reference_date: Any = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """컬럼별 처리 계획에 따라 입력 데이터의 개인정보를 가명화함"""
    fake = Faker(locale)
    Faker.seed(seed)
    random.seed(seed)
    output = df.copy()
    summary = {}

    for column, spec in plan.pii.items():
        if column not in output.columns: continue
        action = spec.get("action", "faker")
        if action == "drop":
            output = output.drop(columns=[column])
            summary[column] = {"action": "drop"}
            continue
        if action in ("mask", "smart_mask"):
            pii_type = spec.get("faker") or spec.get("pii_type")
            output[column] = SmartMasker.mask_series(output[column], pii_type=pii_type)
            summary[column] = {"action": "mask", "mode": "smart_format_preserving", "pii_type": pii_type}
            continue
        if action == "hash":
            output[column] = output[column].map(lambda value: None if pd.isna(value) else hashlib.sha256(str(value).encode("utf-8")).hexdigest())
            summary[column] = {"action": "hash"}
            continue
        if action == "token":
            output[column] = output[column].map(
                lambda value: project_token(value, project_id=project_id, namespace=column, key_version=key_version))
            summary[column] = {"action": "token", "project_id": project_id,
                               "key_version": key_version, "consistent_mapping": True}
            continue
        provider = spec.get("faker", "word")
        fake = Faker(locale)
        values = []
        for idx in range(len(output)):
            row_data = output.iloc[idx]
            val = ContextAwareFaker.faker_value_coherent(
                fake, provider, column, row_data, reference_date=reference_date
            )
            values.append(val)
        output[column] = values
        summary[column] = {"action": "faker", "provider": provider}

    return output, summary

# 개인식별정보(PII) output 구조를 생성 및 조립함
def build_pii_output(
    raw: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan,
    seed: int,
    locale: str = "ko_KR",
    reference_date: Any = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """합성 결과의 개인정보 컬럼을 원본 문맥과 계획에 따라 처리함"""
    fake = Faker(locale)
    Faker.seed(seed)
    random.seed(seed)
    output = synthetic.copy()
    summary = {}

    for column, spec in plan.pii.items():
        action = spec.get("action", "faker")
        if action == "drop":
            if column in output.columns: output = output.drop(columns=[column])
            summary[column] = {"action": "drop"}
            continue
        if action in ("mask", "smart_mask"):
            pii_type = spec.get("faker") or spec.get("pii_type")
            source = output[column] if column in output.columns else _repeat_source_series(raw, column, len(output))
            output[column] = SmartMasker.mask_series(source, pii_type=pii_type)
            summary[column] = {"action": "mask", "mode": "smart_format_preserving", "pii_type": pii_type}
            continue
        if action == "hash":
            source_values = raw[column].dropna().astype(str).tolist() if column in raw.columns else []
            output[column] = [hashlib.sha256(source_values[i % len(source_values)].encode("utf-8")).hexdigest() for i in range(len(output))] if source_values else None
            summary[column] = {"action": "hash"}
            continue

        provider = spec.get("faker", "word")
        values = []
        for idx in range(len(output)):
            row_data = output.iloc[idx]
            val = ContextAwareFaker.faker_value_coherent(
                fake, provider, column, row_data, reference_date=reference_date
            )
            values.append(val)
        output[column] = values
        summary[column] = {"action": "faker", "provider": provider, "consistent_mapping": False, "coherent_context": True}

    ordered = [column for column in raw.columns if column in output.columns]
    extras = [column for column in output.columns if column not in ordered]
    output = output[ordered + extras]
    return output, {"summary": summary}
