# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: engine.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/rule_based/engine.py
# 목적: 규칙 기반 합성 데이터 생성 엔진 메인 루프를 실행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import Any
import pandas as pd
from ...common.types import ColumnPlan

class RuleEngine:
    # weighted choice 작업을 수행함
    @staticmethod
    def weighted_choice(values: list[Any], weights: list[float] | None = None) -> Any:
        if not values:
            return None
        if not weights:
            return random.choice(values)
        total = sum(weights)
        pick = random.random() * total
        cumulative = 0.0
        for value, weight in zip(values, weights):
            cumulative += weight
            if pick <= cumulative:
                return value
        return values[-1]

    # apply 변환 규칙 컬럼 작업을 수행함
    @classmethod
    def apply_rule_column(cls, row_count: int, spec: dict[str, Any]) -> list[Any]:
        rule_type = spec.get("type")
        if rule_type == "choice":
            values = list(spec.get("values", []))
            weights = spec.get("weights")
            return [cls.weighted_choice(values, weights) for _ in range(row_count)]

        if rule_type == "sequence":
            start = int(spec.get("start", 1))
            step = int(spec.get("step", 1))
            prefix = str(spec.get("prefix", ""))
            return [f"{prefix}{start + i * step}" for i in range(row_count)]

        if rule_type == "number_range":
            min_value = float(spec.get("min", 0))
            max_value = float(spec.get("max", 1))
            integer = bool(spec.get("integer", False))
            values = [random.uniform(min_value, max_value) for _ in range(row_count)]
            return [round(value) if integer else value for value in values]

        if rule_type == "date_between":
            start = datetime.fromisoformat(spec["start"])
            end = datetime.fromisoformat(spec["end"])
            days = max((end - start).days, 0)
            return [(start + timedelta(days=random.randint(0, days))).date().isoformat() for _ in range(row_count)]

        if rule_type == "pattern":
            fmt = str(spec.get("format", "########"))
            res = []
            for _ in range(row_count):
                chars = []
                for ch in fmt:
                    if ch == '#':
                        chars.append(str(random.randint(0, 9)))
                    elif ch == '?':
                        chars.append(chr(random.randint(65, 90)))
                    else:
                        chars.append(ch)
                res.append("".join(chars))
            return res

        if rule_type == "constant":
            return [spec.get("value") for _ in range(row_count)]

        raise ValueError(f"Unsupported rule type: {rule_type}")

    # apply 규칙 목록 작업을 수행함
    @classmethod
    def apply_rules(cls, df: pd.DataFrame, plan: ColumnPlan) -> pd.DataFrame:
        output = df.copy()
        for column, spec in plan.rules.items():
            output[column] = cls.apply_rule_column(len(output), spec)
        return output
