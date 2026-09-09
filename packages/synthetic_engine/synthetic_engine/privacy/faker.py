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
from .token_vault import project_token
from .masker import SmartMasker


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

    @classmethod
    def generate_coherent_ssn(cls, age_val: Any, gender_val: Any) -> str:
        """연령·성별 문맥을 반영한 주민등록번호 형식 값을 생성함"""
        current_year = 2026
        birth_year = 1990
        if age_val is not None:
            try:
                age_int = int(float(age_val))
                if 0 <= age_int <= 120:
                    birth_year = current_year - age_int
            except Exception:
                pass

        yy = f"{birth_year % 100:02d}"
        mm = f"{random.randint(1, 12):02d}"
        dd = f"{random.randint(1, 28):02d}"
        front = f"{yy}{mm}{dd}"

        is_female = False
        if gender_val is not None:
            g_str = str(gender_val).strip().lower()
            if "여" in g_str or "female" in g_str or g_str == "f" or g_str == "2":
                is_female = True

        gender_digit = ("2" if is_female else "1") if birth_year < 2000 else ("4" if is_female else "3")
        back_tail = f"{random.randint(100000, 999999):06d}"
        return f"{front}-{gender_digit}{back_tail}"

    @classmethod
    def generate_coherent_phone(cls, col_name: str, region_val: Any) -> str:
        """컬럼명과 지역 문맥을 반영한 전화번호 형식 값을 생성함"""
        region = str(region_val or "").strip()
        if "유선" in col_name or "tel" in col_name.lower():
            if "서울" in region: code = "02"
            elif "경기" in region or "인천" in region: code = "031"
            elif "부산" in region: code = "051"
            elif "대구" in region: code = "053"
            elif "광주" in region: code = "062"
            elif "대전" in region: code = "042"
            else: code = "031"
        else:
            code = "010"

        mid = random.randint(2000, 9999)
        last = random.randint(1000, 9999)
        return f"{code}-{mid}-{last:04d}"

    @classmethod
    def generate_coherent_foreigner_id(cls, age_val: Any, gender_val: Any) -> str:
        """연령·성별 문맥을 반영한 외국인등록번호 형식 값을 생성함"""
        current_year = 2026
        birth_year = 1990
        if age_val is not None:
            try:
                age_int = int(float(age_val))
                if 0 <= age_int <= 120:
                    birth_year = current_year - age_int
            except Exception:
                pass

        yy = f"{birth_year % 100:02d}"
        mm = f"{random.randint(1, 12):02d}"
        dd = f"{random.randint(1, 28):02d}"
        front = f"{yy}{mm}{dd}"

        is_female = False
        if gender_val is not None:
            g_str = str(gender_val).strip().lower()
            if "여" in g_str or "female" in g_str or g_str == "f" or g_str == "2":
                is_female = True

        gender_digit = ("6" if is_female else "5") if birth_year < 2000 else ("8" if is_female else "7")
        back_tail = f"{random.randint(100000, 999999):06d}"
        return f"{front}-{gender_digit}{back_tail}"

    @classmethod
    def generate_passport(cls) -> str:
        """여권번호 형식의 가명값을 생성함"""
        letter = random.choice(["M", "S", "G", "D", "R"])
        digits = f"{random.randint(10000000, 99999999):08d}"
        return f"{letter}{digits}"

    @classmethod
    def generate_driver_license(cls) -> str:
        """운전면허번호 형식의 가명값을 생성함"""
        region_code = random.choice(["11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "28"])
        yy = f"{random.randint(0, 26):02d}"
        serial = f"{random.randint(100000, 999999):06d}"
        chk = f"{random.randint(10, 99):02d}"
        return f"{region_code}-{yy}-{serial}-{chk}"

    @classmethod
    def generate_business_number(cls) -> str:
        """사업자등록번호 형식의 가명값을 생성함"""
        part1 = f"{random.randint(100, 999):03d}"
        part2 = f"{random.randint(10, 99):02d}"
        part3 = f"{random.randint(10000, 99999):05d}"
        return f"{part1}-{part2}-{part3}"

    @classmethod
    def generate_corporate_number(cls) -> str:
        """법인등록번호 형식의 가명값을 생성함"""
        part1 = f"{random.randint(100000, 999999):06d}"
        part2 = f"{random.randint(1000000, 9999999):07d}"
        return f"{part1}-{part2}"

    @classmethod
    def generate_credit_card(cls) -> str:
        """카드번호 형식의 가명값을 생성함"""
        p1 = f"{random.randint(1000, 9999):04d}"
        p2 = f"{random.randint(1000, 9999):04d}"
        p3 = f"{random.randint(1000, 9999):04d}"
        p4 = f"{random.randint(1000, 9999):04d}"
        return f"{p1}-{p2}-{p3}-{p4}"

    @classmethod
    def generate_car_plate(cls) -> str:
        """차량번호 형식의 가명값을 생성함"""
        num = random.choice([f"{random.randint(10, 99):02d}", f"{random.randint(100, 999):03d}"])
        hangeul = random.choice(["가", "나", "다", "라", "마", "거", "너", "더", "러", "머", "고", "노", "도", "로", "모", "구", "누", "두", "루", "무", "하", "허", "호"])
        tail = f"{random.randint(1000, 9999):04d}"
        return f"{num}{hangeul} {tail}"

    @classmethod
    def generate_ip_address(cls, fake: Faker) -> str:
        """IP 주소 형식의 가명값을 생성함"""
        return fake.ipv4() if hasattr(fake, "ipv4") else f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    @classmethod
    def faker_value_coherent(cls, fake: Faker, provider: str, col_name: str, row: Any) -> Any:
        """개인정보 제공자 유형에 맞는 문맥 기반 가명값을 생성함"""
        if provider == "ssn":
            age = cls.extract_context_value(row, ["연령", "나이", "age"])
            gender = cls.extract_context_value(row, ["성별", "gender", "sex"])
            return cls.generate_coherent_ssn(age, gender)

        if provider == "foreigner_id":
            age = cls.extract_context_value(row, ["연령", "나이", "age"])
            gender = cls.extract_context_value(row, ["성별", "gender", "sex"])
            return cls.generate_coherent_foreigner_id(age, gender)

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
            region = cls.extract_context_value(row, ["거주", "지역", "주소", "소재지", "시도", "region", "address"])
            return cls.generate_coherent_phone(col_name, region)

        if provider == "name":
            gender = cls.extract_context_value(row, ["성별", "gender", "sex"])
            if gender:
                if "여" in str(gender) or "f" in str(gender).lower():
                    return fake.name_female() if hasattr(fake, "name_female") else fake.name()
                if "남" in str(gender) or "m" in str(gender).lower():
                    return fake.name_male() if hasattr(fake, "name_male") else fake.name()
            return fake.name()

        if provider == "email": return fake.email()
        if provider == "address": return fake.address().replace("\n", " ")
        if provider == "account": return fake.bban()
        return fake.word()

def apply_pii(df: pd.DataFrame, plan: ColumnPlan, seed: int = 42,
              project_id: str = "default", key_version: str = "v1") -> tuple[pd.DataFrame, dict[str, Any]]:
    """컬럼별 처리 계획에 따라 입력 데이터의 개인정보를 가명화함"""
    fake = Faker("ko_KR")
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
        fake = Faker("ko_KR")
        values = []
        for idx in range(len(output)):
            row_data = output.iloc[idx]
            val = ContextAwareFaker.faker_value_coherent(fake, provider, column, row_data)
            values.append(val)
        output[column] = values
        summary[column] = {"action": "faker", "provider": provider}

    return output, summary

def build_pii_output(raw: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan, seed: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    """합성 결과의 개인정보 컬럼을 원본 문맥과 계획에 따라 처리함"""
    fake = Faker("ko_KR")
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
            val = ContextAwareFaker.faker_value_coherent(fake, provider, column, row_data)
            values.append(val)
        output[column] = values
        summary[column] = {"action": "faker", "provider": provider, "consistent_mapping": False, "coherent_context": True}

    ordered = [column for column in raw.columns if column in output.columns]
    extras = [column for column in output.columns if column not in ordered]
    output = output[ordered + extras]
    return output, {"summary": summary}
