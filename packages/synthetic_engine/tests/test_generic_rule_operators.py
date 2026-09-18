# -*- coding: utf-8 -*-
"""범용 규칙 연산자가 데이터셋별 분기 없이 동작하는지 검증한다."""
import numpy as np
import pandas as pd

from synthetic_engine.rules.base import ActionType, DatasetRule, DatasetSchemaConfig, RuleType
from synthetic_engine.rules.engine import DatasetRuleEngine


def test_generic_formula_rule_works_with_arbitrary_column_names():
    frame = pd.DataFrame({"base_value": [100.0, 200.0], "factor": [0.1, 0.25], "derived": [0.0, 0.0]})
    rule = DatasetRule(
        name="derived_value_formula",
        rule_type=RuleType.CALCULATED_FIELD,
        columns=["derived", "base_value", "factor"],
        action=ActionType.RECALCULATE,
        params={
            "target_column": "derived",
            "calculation": "multiply",
            "source_columns": ["base_value", "factor"],
            "round_digits": 2,
        },
    )

    result = DatasetRuleEngine.apply_discovered_rules(frame, [rule])

    assert result["derived"].tolist() == [10.0, 50.0]


def test_generic_conditional_rule_can_update_multiple_targets():
    frame = pd.DataFrame({"count": [0, 2], "flag": ["Y", "Y"], "amount": [100, 20]})
    rule = DatasetRule(
        name="zero_count_implies_empty",
        rule_type=RuleType.CUSTOM,
        columns=["count", "flag", "amount"],
        action=ActionType.REPAIR_CONDITIONAL,
        params={
            "condition_column": "count",
            "condition": "equals",
            "condition_value": 0,
            "numeric_compare": True,
            "target_columns": ["flag", "amount"],
            "target_values": ["N", 0],
        },
    )

    result = DatasetRuleEngine.apply_discovered_rules(frame, [rule])

    assert result.loc[0, "flag"] == "N"
    assert result.loc[0, "amount"] == 0
    assert result.loc[1, "flag"] == "Y"
    assert result.loc[1, "amount"] == 20


def test_generic_date_order_uses_reference_lag_distribution():
    reference = pd.DataFrame(
        {
            "opened": pd.date_range("2024-01-01", periods=40, freq="D"),
            "closed": pd.date_range("2024-01-01", periods=40, freq="D")
            + pd.to_timedelta(np.tile(np.arange(1, 11), 4), unit="D"),
        }
    )
    frame = pd.DataFrame(
        {
            "opened": pd.date_range("2025-01-01", periods=20, freq="D"),
            "closed": pd.date_range("2024-12-01", periods=20, freq="D"),
        }
    )
    rule = DatasetRule(
        name="opened_before_closed",
        rule_type=RuleType.DATE_ORDER,
        columns=["opened", "closed"],
        params={"before_column": "opened", "after_column": "closed", "allow_equal": True},
    )

    result = DatasetRuleEngine.apply_discovered_rules(frame, [rule], reference=reference, random_state=7)
    lags = (result["closed"] - result["opened"]).dt.days

    assert (lags > 0).all()
    assert lags.nunique() > 1


def test_unknown_dataset_does_not_apply_domain_specific_age_binning():
    frame = pd.DataFrame({"age": [43, 57], "value": [1, 2]})

    result = DatasetRuleEngine.postprocess(frame, dataset_name="unregistered_dataset", filter_clones=False)

    assert result["age"].tolist() == [43, 57]


def test_profile_controls_numeric_binning_without_engine_column_names():
    schema = DatasetSchemaConfig(
        dataset_name="generic_profile",
        rules=[
            DatasetRule(
                name="bucket_measure",
                rule_type=RuleType.RARE_CATEGORY,
                columns=["measure"],
                params={"column": "measure", "bin_size": 5},
            )
        ],
    )
    frame = pd.DataFrame({"measure": [1, 7, 14]})

    result = DatasetRuleEngine.preprocess(frame, schema=schema)

    assert result["measure"].tolist() == [0.0, 5.0, 10.0]
