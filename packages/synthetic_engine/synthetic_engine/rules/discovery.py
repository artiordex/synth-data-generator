# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: discovery.py
# 경로: packages/synthetic_engine/synthetic_engine/rules/discovery.py
# 목적: 원본 데이터에서 변수 간 선후관계, 조건부 종속성, 산식 및 상호의존 관계를 자동 발견함
# =============================================================================
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from .base import DatasetRule, RuleType, ActionType
from ..preprocessing.transformer import _parse_date_series, _parseable_date_ratio
from .profile_registry import default_engine_settings


_DISCOVERY_SETTINGS = default_engine_settings().get("discovery", {})
_DATE_PARSEABLE_RATIO = float(_DISCOVERY_SETTINGS.get("date_parseable_ratio", 0.6))
_TEMPORAL_CONFIDENCE = float(_DISCOVERY_SETTINGS.get("temporal_confidence", 0.995))
_CONDITIONAL_NULL_CONFIDENCE = float(_DISCOVERY_SETTINGS.get("conditional_null_confidence", 0.995))
_ZERO_IMPLICATION_CONFIDENCE = float(_DISCOVERY_SETTINGS.get("zero_implication_confidence", 0.99))
_INEQUALITY_CONFIDENCE = float(_DISCOVERY_SETTINGS.get("inequality_confidence", 0.995))
_NEGATIVE_CATEGORY_VALUES = {str(value) for value in _DISCOVERY_SETTINGS.get("negative_category_values", [])}


class DependencyDiscoveryEngine:
    """
    원본 데이터셋의 프로파일링 과정에서 변수 간 관계(선후관계, 계층관계, 조건부 0값/결측값, 부등식)를
    자동으로 탐색하고 정량적 규칙으로 추출하는 엔진
    """

    @classmethod
    def discover_all_dependencies(cls, df: pd.DataFrame) -> list[DatasetRule]:
        """데이터셋 내의 모든 통계적/결정적 업무 규칙을 자동 탐색함"""
        discovered_rules: list[DatasetRule] = []
        discovered_rules.extend(cls.discover_temporal_orders(df))
        discovered_rules.extend(cls.discover_conditional_nulls(df))
        discovered_rules.extend(cls.discover_zero_implications(df))
        discovered_rules.extend(cls.discover_numerical_inequalities(df))
        return discovered_rules

    @classmethod
    def discover_temporal_orders(cls, df: pd.DataFrame) -> list[DatasetRule]:
        """
        1. 날짜·시간 선후관계 탐색
        두 날짜 컬럼(T1, T2)에 대해 원본에서 T1 <= T2가 99.5% 이상 성립하는 경우 선후관계 규칙으로 도출
        """
        date_cols = [col for col in df.columns if _parseable_date_ratio(df[col]) >= _DATE_PARSEABLE_RATIO]
        rules = []
        if len(date_cols) < 2:
            return rules

        parsed_dates = {col: _parse_date_series(df[col]) for col in date_cols}

        for i, col1 in enumerate(date_cols):
            for col2 in date_cols[i + 1:]:
                s1 = parsed_dates[col1]
                s2 = parsed_dates[col2]
                valid = s1.notna() & s2.notna()
                if not valid.any():
                    continue

                # col1 <= col2 검증
                forward_valid = (s1[valid] <= s2[valid]).mean()
                if forward_valid >= _TEMPORAL_CONFIDENCE:
                    rules.append(DatasetRule(
                        name=f"auto_date_order_{col1}_le_{col2}",
                        rule_type=RuleType.DATE_ORDER,
                        columns=[col1, col2],
                        action=ActionType.REPAIR_CONDITIONAL,
                        params={
                            "before_column": col1,
                            "after_column": col2,
                            "allow_equal": True,
                            "confidence": float(forward_valid),
                            "support": float(valid.mean()),
                            "violation_rate": float(1.0 - forward_valid),
                        },
                        description=f"자동 감지된 날짜 선후관계: {col1} <= {col2} (원본 신뢰도: {forward_valid:.1%})"
                    ))
                else:
                    # 반대 방향 col2 <= col1 검증
                    backward_valid = (s2[valid] <= s1[valid]).mean()
                    if backward_valid >= _TEMPORAL_CONFIDENCE:
                        rules.append(DatasetRule(
                            name=f"auto_date_order_{col2}_le_{col1}",
                            rule_type=RuleType.DATE_ORDER,
                            columns=[col2, col1],
                            action=ActionType.REPAIR_CONDITIONAL,
                            params={
                                "before_column": col2,
                                "after_column": col1,
                                "allow_equal": True,
                                "confidence": float(backward_valid),
                                "support": float(valid.mean()),
                                "violation_rate": float(1.0 - backward_valid),
                            },
                            description=f"자동 감지된 날짜 선후관계: {col2} <= {col1} (원본 신뢰도: {backward_valid:.1%})"
                        ))
        return rules

    @classmethod
    def discover_conditional_nulls(cls, df: pd.DataFrame) -> list[DatasetRule]:
        """
        2. 조건부 결측 종속성 탐색
        A가 NULL일 때 B도 반드시 NULL인 관계 (Support >= 5%, Confidence >= 99%)
        예: 해지사유 == NULL -> 퇴거일자 == NULL
        """
        rules = []
        cols_with_null = [col for col in df.columns if df[col].isna().any()]

        for col_a in cols_with_null:
            null_a = df[col_a].isna()
            for col_b in cols_with_null:
                if col_a == col_b:
                    continue
                null_b = df[col_b].isna()
                # A가 null일 때 B도 null인 비율
                if not null_a.any():
                    continue
                conf = float(null_b[null_a].mean())
                support = float(null_a.mean())
                if conf >= _CONDITIONAL_NULL_CONFIDENCE:
                    rules.append(DatasetRule(
                        name=f"auto_nullable_if_{col_a}_null_then_{col_b}_null",
                        rule_type=RuleType.NULLABLE_IF,
                        columns=[col_a, col_b],
                        action=ActionType.REPAIR_CONDITIONAL,
                        params={
                            "condition_column": col_a,
                            "condition": "is_null",
                            "null_column": col_b,
                            "target_null_column": col_b,
                            "confidence": conf,
                            "support": support,
                            "violation_rate": 1.0 - conf,
                        },
                        description=f"자동 감지된 조건부 결측 종속성: {col_a}=NULL이면 {col_b}=NULL (신뢰도 {conf:.1%})"
                    ))

        # 2. 범주값 조건부 결측 탐색 (예: 퇴거여부=='N' -> 퇴거일자==NULL)
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns
        for col_a in cat_cols:
            series_a = df[col_a].dropna()
            if len(series_a) == 0:
                continue
            for val in series_a.unique():
                mask_val = (df[col_a].astype(str).str.strip() == str(val).strip())
                if not mask_val.any():
                    continue
                for col_b in cols_with_null:
                    if col_a == col_b:
                        continue
                    conf = float(df.loc[mask_val, col_b].isna().mean())
                    support = float(mask_val.mean())
                    if conf >= _CONDITIONAL_NULL_CONFIDENCE:
                        rules.append(DatasetRule(
                            name=f"auto_nullable_if_{col_a}_{val}_then_{col_b}_null",
                            rule_type=RuleType.NULLABLE_IF,
                            columns=[col_a, col_b],
                            action=ActionType.REPAIR_CONDITIONAL,
                            params={
                                "condition_column": col_a,
                                "condition_val": val,
                                "null_column": col_b,
                                "target_null_column": col_b,
                                "confidence": conf,
                                "support": support,
                                "violation_rate": 1.0 - conf,
                            },
                            description=f"자동 감지된 조건부 결측: {col_a}='{val}'이면 {col_b}=NULL (신뢰도 {conf:.1%})"
                        ))
        return rules

    @classmethod
    def discover_zero_implications(cls, df: pd.DataFrame) -> list[DatasetRule]:
        """
        3. 0값 및 상호 배타성/종속성 탐색
        수치형 A=0 일 때 수치형 B=0 이거나 범주형 C='N'/'0'/'무'인 관계
        예: 자녀수 == 0 -> 출산자녀수 == 0, 출산여부 == 'N'
        """
        rules = []
        num_cols = df.select_dtypes(include=[np.number]).columns

        for col_a in num_cols:
            is_zero_a = (df[col_a] == 0)
            if not is_zero_a.any():
                continue

            # 다른 수치형 컬럼 비교
            for col_b in num_cols:
                if col_a == col_b:
                    continue
                is_zero_b = (df[col_b] == 0)
                conf = float(is_zero_b[is_zero_a].mean())
                if conf >= _ZERO_IMPLICATION_CONFIDENCE:
                    rules.append(DatasetRule(
                        name=f"auto_zero_implication_{col_a}_0_then_{col_b}_0",
                        rule_type=RuleType.CUSTOM,
                        columns=[col_a, col_b],
                        action=ActionType.REPAIR_CONDITIONAL,
                        params={
                            "condition_column": col_a,
                            "condition_val": 0,
                            "target_column": col_b,
                            "target_val": 0,
                            "confidence": conf,
                            "support": float(is_zero_a.mean()),
                            "violation_rate": 1.0 - conf,
                        },
                        description=f"자동 감지된 0값 종속성: {col_a}=0 -> {col_b}=0 (신뢰도 {conf:.1%})"
                    ))

            # 범주형 컬럼 비교 (출산여부 등)
            for col_c in df.select_dtypes(exclude=[np.number]).columns:
                vals_at_zero = df.loc[is_zero_a, col_c].dropna().astype(str)
                if len(vals_at_zero) == 0:
                    continue
                value_counts = vals_at_zero.value_counts()
                top_val, top_count = value_counts.index[0], int(value_counts.iloc[0])
                conf = top_count / len(vals_at_zero)
                if conf >= _ZERO_IMPLICATION_CONFIDENCE and top_val in _NEGATIVE_CATEGORY_VALUES:
                    rules.append(DatasetRule(
                        name=f"auto_category_implication_{col_a}_0_then_{col_c}_{top_val}",
                        rule_type=RuleType.CUSTOM,
                        columns=[col_a, col_c],
                        action=ActionType.REPAIR_CONDITIONAL,
                        params={
                            "condition_column": col_a,
                            "condition_val": 0,
                            "target_column": col_c,
                            "target_val": top_val,
                            "confidence": conf,
                            "support": float(is_zero_a.mean()),
                            "violation_rate": 1.0 - conf,
                        },
                        description=f"자동 감지된 범주 종속성: {col_a}=0 -> {col_c}='{top_val}' (신뢰도 {conf:.1%})"
                    ))
        return rules

    @classmethod
    def discover_numerical_inequalities(cls, df: pd.DataFrame) -> list[DatasetRule]:
        """
        4. 수치형 상하한 부등식 관계 탐색
        A <= B 가 원본 데이터에서 99.5% 이상 성립하는 경우 (예: 부동산자산 <= 총자산, 단축시간 <= 근무시간)
        """
        rules = []
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) < 2:
            return rules

        for i, col_a in enumerate(num_cols):
            for col_b in num_cols[i + 1:]:
                valid = df[col_a].notna() & df[col_b].notna()
                if not valid.any():
                    continue

                s_a = df.loc[valid, col_a]
                s_b = df.loc[valid, col_b]

                # col_a <= col_b 검사
                ratio_le = (s_a <= s_b).mean()
                if ratio_le >= _INEQUALITY_CONFIDENCE and not (s_a == s_b).all():
                    rules.append(DatasetRule(
                        name=f"auto_inequality_{col_a}_le_{col_b}",
                        rule_type=RuleType.LESS_THAN_OR_EQUAL,
                        columns=[col_a, col_b],
                        action=ActionType.REPAIR_CONDITIONAL,
                        params={
                            "less_column": col_a,
                            "greater_column": col_b,
                            "confidence": float(ratio_le),
                            "support": float(valid.mean()),
                            "violation_rate": float(1.0 - ratio_le),
                        },
                        description=f"자동 감지된 부등식 제약: {col_a} <= {col_b} (원본 신뢰도 {ratio_le:.1%})"
                    ))
                else:
                    # 반대 방향 col_b <= col_a 검사
                    ratio_ge = (s_b <= s_a).mean()
                    if ratio_ge >= _INEQUALITY_CONFIDENCE and not (s_a == s_b).all():
                        rules.append(DatasetRule(
                            name=f"auto_inequality_{col_b}_le_{col_a}",
                            rule_type=RuleType.LESS_THAN_OR_EQUAL,
                            columns=[col_b, col_a],
                            action=ActionType.REPAIR_CONDITIONAL,
                            params={
                                "less_column": col_b,
                                "greater_column": col_a,
                                "confidence": float(ratio_ge),
                                "support": float(valid.mean()),
                                "violation_rate": float(1.0 - ratio_ge),
                            },
                            description=f"자동 감지된 부등식 제약: {col_b} <= {col_a} (원본 신뢰도 {ratio_ge:.1%})"
                        ))
        return rules


def _rule_edge(rule: DatasetRule) -> tuple[str, str, bool] | None:
    """Return dependency direction and whether the relation is strict."""
    if rule.rule_type not in {
        RuleType.DATE_ORDER,
        RuleType.LESS_THAN,
        RuleType.LESS_THAN_OR_EQUAL,
        RuleType.GREATER_THAN,
        RuleType.GREATER_THAN_OR_EQUAL,
        RuleType.EQUALITY,
    }:
        return None
    columns = list(rule.columns)
    if len(columns) < 2:
        return None
    strict_types = {RuleType.LESS_THAN, RuleType.GREATER_THAN}
    strict = rule.rule_type in strict_types or bool(rule.params.get("strict", False))
    if rule.rule_type == RuleType.DATE_ORDER:
        strict = not bool(rule.params.get("allow_equal", True))
    if rule.rule_type == RuleType.EQUALITY:
        strict = False
    return columns[0], columns[1], strict


def _strongly_connected_components(nodes: list[str], edges: list[dict[str, Any]]) -> list[list[str]]:
    graph = {node: [] for node in nodes}
    for edge in edges:
        graph.setdefault(edge["source"], []).append(edge["target"])
    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, [])):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] == indices[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(sorted(component))

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return components


def _topological_order(nodes: list[str], edges: list[dict[str, Any]]) -> list[str]:
    indegree = {node: 0 for node in nodes}
    outgoing = {node: [] for node in nodes}
    for edge in edges:
        source, target = edge["source"], edge["target"]
        outgoing.setdefault(source, []).append(target)
        indegree[target] = indegree.get(target, 0) + 1
    ready = sorted(node for node, degree in indegree.items() if degree == 0)
    result: list[str] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        for target in sorted(outgoing.get(node, [])):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    return result


def resolve_rule_dependencies_dag(
    rules: list[DatasetRule],
    min_confidence: float | None = None,
    min_support: float | None = None,
    return_report: bool = False,
) -> list[DatasetRule] | dict[str, Any]:
    """Resolve discovered rule dependencies with SCC-aware cycle semantics.

    Rules below the automatic-application thresholds remain in the discovery
    report but are excluded from the returned executable rule list.  Non-strict
    cycles become equality classes; strict cycles prune the least-supported
    edge until a deterministic DAG remains.
    """
    ordered_rules = sorted(list(rules or []), key=lambda rule: rule.name)
    if min_confidence is None:
        min_confidence = float(_DISCOVERY_SETTINGS.get("temporal_confidence", 0.995))
    if min_support is None:
        min_support = float(_DISCOVERY_SETTINGS.get("min_support", 0.05))
    discovered_names = [rule.name for rule in ordered_rules]
    eligible: list[DatasetRule] = []
    for rule in ordered_rules:
        confidence = float(rule.params.get("confidence", 1.0))
        support = float(rule.params.get("support", 1.0))
        if confidence >= min_confidence and support >= min_support:
            eligible.append(rule)

    nodes = sorted({column for rule in eligible for column in rule.columns[:2]})
    edges: list[dict[str, Any]] = []
    standalone_rules: list[DatasetRule] = []
    for rule in eligible:
        edge = _rule_edge(rule)
        if edge is None:
            standalone_rules.append(rule)
            continue
        source, target, strict = edge
        edges.append({
            "source": source,
            "target": target,
            "strict": strict,
            "rule": rule,
            "confidence": float(rule.params.get("confidence", 1.0)),
            "support": float(rule.params.get("support", 1.0)),
            "violation_rate": float(rule.params.get("violation_rate", 0.0)),
        })

    equivalence_classes: list[list[str]] = []
    pruned_rules: list[dict[str, Any]] = []
    cycles_resolved = 0
    equivalence_rules: list[DatasetRule] = []

    while True:
        components = _strongly_connected_components(nodes, edges)
        cyclic = [component for component in components if len(component) > 1]
        if not cyclic:
            break
        component = sorted(cyclic, key=lambda value: tuple(value))[0]
        member_set = set(component)
        internal = [edge for edge in edges if edge["source"] in member_set and edge["target"] in member_set]
        if internal and not any(edge["strict"] for edge in internal):
            cycles_resolved += 1
            equivalence_classes.append(component)
            edges = [edge for edge in edges if edge not in internal]
            equivalence_rules.append(DatasetRule(
                name="equivalence_" + "_".join(component),
                rule_type=RuleType.EQUALITY,
                columns=component,
                action=ActionType.REPAIR_CONDITIONAL,
                params={"equivalence_class": component, "confidence": min(edge["confidence"] for edge in internal)},
                description="비엄격 부등식 순환을 동치관계로 축약",
            ))
        else:
            edge = min(
                internal,
                key=lambda item: (
                    item["confidence"],
                    item["support"],
                    -item["violation_rate"],
                    item["rule"].name,
                ),
            )
            edges.remove(edge)
            cycles_resolved += 1
            pruned_rules.append({
                "rule": edge["rule"].name,
                "reason": "strict_cycle_lowest_evidence",
                "confidence": edge["confidence"],
                "support": edge["support"],
                "violation_rate": edge["violation_rate"],
            })

    topological = _topological_order(nodes, edges)
    rank = {node: position for position, node in enumerate(topological)}
    resolved_edges = [edge["rule"] for edge in edges]
    resolved_rules = sorted(
        resolved_edges + equivalence_rules + standalone_rules,
        key=lambda rule: (min((rank.get(column, len(rank)) for column in rule.columns), default=len(rank)), rule.name),
    )
    report = {
        "status": "PASS" if not pruned_rules or topological else "FAIL_SAFE",
        "discovered_rules": discovered_names,
        "auto_applied_rules": [rule.name for rule in resolved_rules],
        "resolved_rules": resolved_rules,
        "topological_order": topological,
        "equivalence_classes": equivalence_classes,
        "pruned_rules": pruned_rules,
        "cycles_resolved": cycles_resolved,
        "thresholds": {"confidence": min_confidence, "support": min_support},
    }
    return report if return_report else resolved_rules


# 모듈 레벨 편의 함수 노출
discover_all_dependencies = DependencyDiscoveryEngine.discover_all_dependencies
discover_temporal_orders = DependencyDiscoveryEngine.discover_temporal_orders
discover_conditional_nulls = DependencyDiscoveryEngine.discover_conditional_nulls
discover_zero_implications = DependencyDiscoveryEngine.discover_zero_implications
discover_numerical_inequalities = DependencyDiscoveryEngine.discover_numerical_inequalities
