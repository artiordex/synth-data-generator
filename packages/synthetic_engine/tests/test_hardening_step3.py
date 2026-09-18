# -*- coding: utf-8 -*-
import pandas as pd

from synthetic_engine.rules.base import ActionType, DatasetRule, RuleType
from synthetic_engine.rules.discovery import resolve_rule_dependencies_dag
from synthetic_engine.rules.engine import DatasetRuleEngine


def _rule(name, source, target, rule_type, confidence=1.0, support=0.5, violation_rate=0.0):
    return DatasetRule(
        name=name,
        rule_type=rule_type,
        columns=[source, target],
        action=ActionType.REPAIR_CONDITIONAL,
        params={
            "confidence": confidence,
            "support": support,
            "violation_rate": violation_rate,
        },
    )


def test_rule_dependency_cycle_resolution():
    rules = [
        _rule("a_le_b", "a", "b", RuleType.LESS_THAN_OR_EQUAL),
        _rule("b_le_c", "b", "c", RuleType.LESS_THAN_OR_EQUAL),
        _rule("c_le_a", "c", "a", RuleType.LESS_THAN_OR_EQUAL),
    ]
    report = resolve_rule_dependencies_dag(rules, return_report=True)
    assert report["status"] == "PASS"
    assert report["topological_order"]
    assert report["cycles_resolved"] == 1


def test_non_strict_cycle_collapses_to_equivalence():
    report = resolve_rule_dependencies_dag([
        _rule("a_le_b", "a", "b", RuleType.LESS_THAN_OR_EQUAL),
        _rule("b_le_a", "b", "a", RuleType.LESS_THAN_OR_EQUAL),
    ], return_report=True)
    assert any(set(item) == {"a", "b"} for item in report["equivalence_classes"])
    assert any(rule.rule_type == RuleType.EQUALITY for rule in report["resolved_rules"])


def test_strict_cycle_prunes_lowest_confidence_edge():
    rules = [
        _rule("a_lt_b", "a", "b", RuleType.LESS_THAN, confidence=.999),
        _rule("b_lt_c", "b", "c", RuleType.LESS_THAN, confidence=.998),
        _rule("c_lt_a", "c", "a", RuleType.LESS_THAN, confidence=.996),
    ]
    report = resolve_rule_dependencies_dag(rules, return_report=True)
    assert [item["rule"] for item in report["pruned_rules"]] == ["c_lt_a"]
    assert len(report["resolved_rules"]) == 2


def test_discovered_rules_are_applied_in_topological_order():
    frame = pd.DataFrame({"a": [5.0], "b": [3.0], "c": [1.0]})
    rules = [
        _rule("a_le_b", "a", "b", RuleType.LESS_THAN_OR_EQUAL),
        _rule("b_le_c", "b", "c", RuleType.LESS_THAN_OR_EQUAL),
    ]
    processed, report = DatasetRuleEngine.apply_discovered_rules(frame, rules, return_report=True)
    assert processed.loc[0, "a"] <= processed.loc[0, "b"] <= processed.loc[0, "c"]
    assert report["applied_rules"] == ["a_le_b", "b_le_c"]


def test_low_confidence_discovered_rule_is_not_auto_applied():
    report = resolve_rule_dependencies_dag([
        _rule("low", "a", "b", RuleType.LESS_THAN_OR_EQUAL, confidence=.90, support=.5),
    ], return_report=True)
    assert report["auto_applied_rules"] == []
    assert report["discovered_rules"] == ["low"]


def test_rule_resolution_is_deterministic():
    rules = [
        _rule("b_le_c", "b", "c", RuleType.LESS_THAN_OR_EQUAL),
        _rule("a_le_b", "a", "b", RuleType.LESS_THAN_OR_EQUAL),
    ]
    first = resolve_rule_dependencies_dag(rules, return_report=True)
    second = resolve_rule_dependencies_dag(list(reversed(rules)), return_report=True)
    assert first["topological_order"] == second["topological_order"]
    assert [r.name for r in first["resolved_rules"]] == [r.name for r in second["resolved_rules"]]
