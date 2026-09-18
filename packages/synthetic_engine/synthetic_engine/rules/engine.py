# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: engine.py
# 경로: packages/synthetic_engine/synthetic_engine/rules/engine.py
# 목적: 선언형 데이터 규칙을 실행하는 범용 합성데이터 규칙 엔진
# =============================================================================
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from .base import DatasetRule, DatasetSchemaConfig, RuleType, ActionType, RuleViolation
from .catalog import match_dataset_schema
from .profile_registry import default_engine_settings
from .lag_sampling import sample_empirical_lags  # backwards-compatible public import
from .discovery import DependencyDiscoveryEngine, resolve_rule_dependencies_dag
from .operators import RuleExecutionContext, execute_rule


_ENGINE_DEFAULTS = default_engine_settings()


class DatasetRuleEngine:
    """프로파일 규칙과 데이터 기반 발견 규칙을 실행하는 범용 엔진.

    이 클래스는 데이터셋 이름이나 컬럼명에 대한 업무 지식을 보유하지 않는다.
    업무 의미는 ``DatasetSchemaConfig.rules``에 선언하고, 실행기는 규칙 타입별
    연산자만 제공한다. 따라서 미등록 데이터셋에는 카탈로그 업무규칙이
    자동으로 적용되지 않는다.
    """

    @classmethod
    def apply_discovered_rules(
        cls,
        df: pd.DataFrame,
        rules: list[DatasetRule],
        reference: pd.DataFrame | None = None,
        random_state: int | np.random.Generator | None = 42,
        return_report: bool = False,
        as_of: pd.Timestamp | str | None = None,
    ) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
        """규칙 의존성을 해결한 뒤 결정론적인 순서로 규칙을 실행한다."""
        resolution = resolve_rule_dependencies_dag(rules, return_report=True)
        output = df.copy()
        rng = random_state if isinstance(random_state, np.random.Generator) else np.random.default_rng(random_state)
        context = RuleExecutionContext(
            reference=reference,
            rng=rng,
            as_of=pd.Timestamp(as_of) if as_of is not None else None,
        )
        applied: list[str] = []
        changed_rows_by_rule: dict[str, int] = {}
        changed_columns_by_rule: dict[str, list[str]] = {}

        # A later dependency can tighten a value touched by an earlier edge.
        # The bounded fixed-point pass keeps chained constraints stable.
        for _ in range(max(1, len(resolution["resolved_rules"]) + 1)):
            before = output.copy(deep=True)
            for rule in resolution["resolved_rules"]:
                output, changed_rows, changed_columns = execute_rule(output, rule, context)
                if rule.name not in applied:
                    applied.append(rule.name)
                if changed_rows:
                    changed_rows_by_rule[rule.name] = max(changed_rows_by_rule.get(rule.name, 0), changed_rows)
                    changed_columns_by_rule[rule.name] = sorted(
                        set(changed_columns_by_rule.get(rule.name, [])) | set(changed_columns)
                    )
            if output.equals(before):
                break

        resolution["applied_rules"] = applied
        resolution["changed_rows_by_rule"] = changed_rows_by_rule
        resolution["changed_columns_by_rule"] = changed_columns_by_rule
        if return_report:
            return output, resolution
        return output

    @classmethod
    def preprocess(
        cls,
        df: pd.DataFrame,
        schema: DatasetSchemaConfig | None = None,
        dataset_name: str = "",
        return_report: bool = False,
    ) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
        """생성 전 공통 전처리와 프로파일 선언 변환을 적용한다.

        알 수 없는 데이터셋에는 컬럼명만 보고 연령·금액·업무 영역을 추정하는
        변환을 적용하지 않는다. 희소범주 통합처럼 타입만으로 안전하게 판단할
        수 있는 처리는 공통 정책으로 수행하고, 구간화/극단값 처리는 프로파일
        규칙으로만 수행한다.
        """
        output = df.copy()
        if schema is None:
            schema = match_dataset_schema(output, dataset_name)

        report: dict[str, Any] = {
            "rare_category_mappings": {},
            "clipped_extremes": {},
            "binned_columns": {},
            "applied_rules": [],
        }

        preprocessing_rules = [
            rule
            for rule in (schema.rules if schema is not None else [])
            if rule.rule_type in {RuleType.RARE_CATEGORY, RuleType.EXTREME_VALUE}
        ]
        if preprocessing_rules:
            output, rule_report = cls.apply_discovered_rules(
                output,
                preprocessing_rules,
                reference=output,
                random_state=0,
                return_report=True,
            )
            report["applied_rules"] = rule_report.get("applied_rules", [])
            changed_columns = rule_report.get("changed_columns_by_rule", {})
            rare_rule_columns = {
                column
                for rule in preprocessing_rules
                if rule.rule_type == RuleType.RARE_CATEGORY
                for column in rule.columns
            }
            for columns in changed_columns.values():
                for column in columns:
                    if column in rare_rule_columns:
                        report["binned_columns"][column] = "profile rule"
                    else:
                        report["clipped_extremes"][column] = {"source": "profile rule"}

        # This is a type-level transformation, not a dataset-specific rule.
        cat_cols = output.select_dtypes(include=["object", "string", "category"]).columns
        rare_threshold = getattr(
            schema,
            "rare_category_threshold",
            float((_ENGINE_DEFAULTS.get("labels", {}) or {}).get("rare_category_threshold", 0.01)),
        ) if schema else float((_ENGINE_DEFAULTS.get("labels", {}) or {}).get("rare_category_threshold", 0.01))
        # Unknown profiles do not receive a language-specific replacement label.
        # A profile can explicitly provide one (the built-in Korean profiles do).
        rare_label = getattr(schema, "rare_category_label", None) if schema else None
        for column in cat_cols:
            frequencies = output[column].value_counts(normalize=True, dropna=True)
            rare_values = frequencies[frequencies < rare_threshold].index.tolist()
            if rare_label is not None and rare_values and len(rare_values) < len(frequencies):
                output[column] = output[column].replace({value: rare_label for value in rare_values}).astype("string")
                report["rare_category_mappings"][column] = {
                    "rare_values_grouped": rare_values,
                    "grouped_count": len(rare_values),
                    "label": rare_label,
                }

        return (output, report) if return_report else output

    @classmethod
    def postprocess(
        cls,
        synthetic: pd.DataFrame,
        original: pd.DataFrame | None = None,
        schema: DatasetSchemaConfig | None = None,
        dataset_name: str = "",
        raw_df: pd.DataFrame | None = None,
        return_violations: bool = False,
        filter_clones: bool = True,
        random_state: int | np.random.Generator | None = None,
        as_of: pd.Timestamp | str | None = None,
    ) -> pd.DataFrame | tuple[pd.DataFrame, list[RuleViolation]]:
        """프로파일/자동발견 규칙과 원본 복제 방지 정책을 적용한다."""
        output = synthetic.copy()
        violations: list[RuleViolation] = []
        reference = original if original is not None else raw_df
        if schema is None:
            schema = match_dataset_schema(reference if reference is not None else output, dataset_name)

        executable_rules: list[DatasetRule] = list(schema.rules) if schema is not None else []
        if isinstance(reference, pd.DataFrame) and not reference.empty:
            executable_rules.extend(DependencyDiscoveryEngine.discover_all_dependencies(reference))

        if executable_rules:
            output, rule_report = cls.apply_discovered_rules(
                output,
                executable_rules,
                reference=reference,
                random_state=42 if random_state is None else random_state,
                return_report=True,
                as_of=as_of,
            )
            rules_by_name = {rule.name: rule for rule in executable_rules}
            for name, affected_rows in rule_report.get("changed_rows_by_rule", {}).items():
                rule = rules_by_name.get(name)
                if rule is None:
                    continue
                violations.append(
                    RuleViolation(
                        rule_name=name,
                        rule_type=rule.rule_type,
                        action_taken=rule.action,
                        affected_rows=int(affected_rows),
                        affected_columns=rule_report.get("changed_columns_by_rule", {}).get(name, list(rule.columns)),
                        description=rule.description,
                    )
                )

        if filter_clones and isinstance(reference, pd.DataFrame) and not reference.empty:
            output, clone_violations = cls.filter_exact_and_unique_clones(output, reference)
            violations.extend(clone_violations)

        return (output, violations) if return_violations else output

    @classmethod
    def filter_exact_and_unique_clones(
        cls,
        synthetic: pd.DataFrame,
        original: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[RuleViolation]]:
        """원본 전체 일치와 원본 유일 레코드 일치를 분리하여 차단한다."""
        violations: list[RuleViolation] = []
        common_columns = [column for column in original.columns if column in synthetic.columns]
        if not common_columns or original.empty or synthetic.empty:
            return synthetic, violations

        def make_keys(frame: pd.DataFrame) -> list[tuple[Any, ...]]:
            clean = frame[common_columns].astype(object).where(frame[common_columns].notna(), None)
            return [tuple(row) for row in clean.to_numpy()]

        original_counts = Counter(make_keys(original))
        unique_keys = {key for key, count in original_counts.items() if count == 1}
        all_keys = set(original_counts)
        synthetic_keys = make_keys(synthetic)
        unique_mask = np.array([key in unique_keys for key in synthetic_keys])
        exact_mask = np.array([key in all_keys for key in synthetic_keys])
        unique_count = int(unique_mask.sum())
        exact_count = int(exact_mask.sum())

        if unique_count:
            violations.append(
                RuleViolation(
                    rule_name="raw_unique_record_match_block",
                    rule_type=RuleType.UNIQUE_RECORD_MATCH_BLOCK,
                    action_taken=ActionType.DROP,
                    affected_rows=unique_count,
                    affected_columns=common_columns,
                    description="원본에서 유일한 전체 행과 일치하는 합성 레코드를 제거",
                )
            )
        if exact_count > unique_count:
            violations.append(
                RuleViolation(
                    rule_name="raw_exact_record_match_block",
                    rule_type=RuleType.EXACT_MATCH_BLOCK,
                    action_taken=ActionType.DROP,
                    affected_rows=exact_count - unique_count,
                    affected_columns=common_columns,
                    description="원본 행과 완전히 일치하는 합성 레코드를 제거",
                )
            )

        if exact_count:
            return synthetic.loc[~exact_mask].reset_index(drop=True), violations
        return synthetic, violations

    @classmethod
    def audit_rules(
        cls,
        df: pd.DataFrame,
        schema: DatasetSchemaConfig | None = None,
        dataset_name: str = "",
    ) -> dict[str, int]:
        """선언된 규칙이 현재 프레임을 변경해야 하는 행 수를 집계한다."""
        if schema is None:
            schema = match_dataset_schema(df=df, dataset_name=dataset_name)

        rules: list[DatasetRule] = list(schema.rules) if schema is not None else []
        rules.extend(DependencyDiscoveryEngine.discover_all_dependencies(df))
        resolution = resolve_rule_dependencies_dag(rules, return_report=True)
        result: dict[str, int] = {}
        for rule in resolution["resolved_rules"]:
            before = df.copy(deep=True)
            checked = cls.apply_discovered_rules(
                df,
                [rule],
                reference=df,
                random_state=0,
            )
            changed = pd.Series(False, index=df.index)
            for column in before.columns.intersection(checked.columns):
                left = before[column]
                right = checked[column]
                changed |= ~(left.eq(right) | (left.isna() & right.isna()))
            result[rule.name] = int(changed.sum())
        return result


__all__ = ["DatasetRuleEngine", "sample_empirical_lags"]
