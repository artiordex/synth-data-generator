# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
import random
from typing import Any
import pandas as pd
from faker import Faker
from ..common.types import ColumnPlan

class ContextAwareFaker:
    @staticmethod
    def extract_context_value(row: Any, target_columns: list[str]) -> Any:
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
    def faker_value_coherent(cls, fake: Faker, provider: str, col_name: str, row: Any) -> Any:
        if provider == "ssn":
            age = cls.extract_context_value(row, ["연령", "나이", "age"])
            gender = cls.extract_context_value(row, ["성별", "gender", "sex"])
            return cls.generate_coherent_ssn(age, gender)

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

def apply_pii(df: pd.DataFrame, plan: ColumnPlan, seed: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    fake = Faker("ko_KR")
    Faker.seed(seed)
    output = df.copy()
    summary = {}

    for column, spec in plan.pii.items():
        if column not in output.columns: continue
        action = spec.get("action", "faker")
        if action == "drop":
            output = output.drop(columns=[column])
            summary[column] = {"action": "drop"}
            continue
        if action == "mask":
            output[column] = output[column].map(lambda value: None if pd.isna(value) else "***")
            summary[column] = {"action": "mask"}
            continue
        if action == "hash":
            output[column] = output[column].map(lambda value: None if pd.isna(value) else hashlib.sha256(str(value).encode("utf-8")).hexdigest())
            summary[column] = {"action": "hash"}
            continue
        summary[column] = {"action": "faker", "provider": spec.get("faker", "word")}

    return output, summary

def build_pii_output(raw: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan, seed: int) -> tuple[pd.DataFrame, dict[str, Any]]:
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
        if action == "mask":
            output[column] = "***"
            summary[column] = {"action": "mask"}
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

    return output, {"summary": summary}
