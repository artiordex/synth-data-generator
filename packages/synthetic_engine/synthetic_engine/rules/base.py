# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: base.py
# 경로: packages/synthetic_engine/synthetic_engine/rules/base.py
# 목적: 합성데이터 업무규칙·제약조건·위반 처리를 위한 데이터 모델 및 타입을 정의함
# =============================================================================
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RuleType(str, Enum):
    """업무규칙 유형 열거형"""
    REQUIRED = "required"
    NULLABLE_IF = "nullable_if"
    REQUIRED_IF = "required_if"
    MIN_MAX = "min_max"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    EQUALITY = "equality"
    DATE_ORDER = "date_order"
    DATE_RANGE = "date_range"
    ALLOWED_VALUES = "allowed_values"
    CONDITIONAL_ALLOWED_VALUES = "conditional_allowed_values"
    CALCULATED_FIELD = "calculated_field"
    RARE_CATEGORY = "rare_category"
    EXTREME_VALUE = "extreme_value"
    EXACT_MATCH_BLOCK = "exact_match_block"
    UNIQUE_RECORD_MATCH_BLOCK = "unique_record_match_block"
    CUSTOM = "custom"


class ActionType(str, Enum):
    """위반 시 오류 처리 우선순위 원칙 열거형"""
    RECALCULATE = "recalculate"               # 1순위: 다른 컬럼으로 정확히 재계산
    REPAIR_CONDITIONAL = "repair_conditional" # 2순위: 논리적 종속관계 조건부 보정
    REGENERATE = "regenerate"                 # 3순위: 해당 행/필드 재생성
    DROP = "drop"                             # 4순위: 안전하게 보정할 수 없는 행 삭제


@dataclass
class RuleViolation:
    """규칙 위반 상세 정보"""
    rule_name: str
    rule_type: RuleType
    action_taken: ActionType
    affected_rows: int
    affected_columns: list[str]
    sample_indices: list[int] = field(default_factory=list)
    description: str = ""


@dataclass
class DatasetRule:
    """개별 업무규칙 명세"""
    name: str
    rule_type: RuleType
    columns: list[str]
    action: ActionType = ActionType.REPAIR_CONDITIONAL
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    validator: Callable[[Any], Any] | None = None
    repairer: Callable[[Any], Any] | None = None

    @property
    def preceding_column(self) -> str | None:
        return (
            self.params.get("start_column")
            or self.params.get("before_column")
            or self.params.get("less_column")
            or (self.columns[0] if len(self.columns) >= 2 else None)
        )

    @property
    def succeeding_column(self) -> str | None:
        return (
            self.params.get("end_column")
            or self.params.get("after_column")
            or self.params.get("greater_column")
            or (self.columns[1] if len(self.columns) >= 2 else None)
        )

    @property
    def primary_column(self) -> str | None:
        return (
            self.params.get("zero_column")
            or self.params.get("condition_column")
            or (self.columns[0] if self.columns else None)
        )

    @property
    def implied_zero_column(self) -> str | None:
        return (
            self.params.get("dependent_column")
            or self.params.get("target_column")
            or (self.columns[1] if len(self.columns) >= 2 else None)
        )

    @property
    def condition_column(self) -> str | None:
        return self.params.get("condition_column") or (self.columns[0] if self.columns else None)

    @property
    def target_null_column(self) -> str | None:
        return self.params.get("null_column") or (self.columns[1] if len(self.columns) >= 2 else None)


@dataclass
class DatasetSchemaConfig:
    """데이터셋별 스키마 및 생성 전략 구성"""
    dataset_name: str
    dataset_id: str = ""
    aliases: list[str] = field(default_factory=list)
    quasi_identifiers: list[str] = field(default_factory=list)
    sensitive_columns: list[str] = field(default_factory=list)
    numerical_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    rules: list[DatasetRule] = field(default_factory=list)
    # Optional catalog metadata is kept after the public schema fields so
    # positional construction remains compatible with the task contract.
    identifiers: list[str] = field(default_factory=list)
    derived_columns: list[str] = field(default_factory=list)
    rare_category_threshold: float = 0.01
    rare_category_label: Any = "기타"
    extreme_value_quantile: float = 0.999
    notes: str = ""
    # Public, non-sensitive domain metadata used by post-DP projection.
    public_bounds: dict[str, Any] = field(default_factory=dict)
    domain_constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
