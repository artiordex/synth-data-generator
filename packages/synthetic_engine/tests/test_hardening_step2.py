# -*- coding: utf-8 -*-
import pandas as pd

from synthetic_engine.privacy.guardrails import escape_unique_clones


def test_minority_group_retention_after_clone_escape():
    raw = pd.DataFrame({
        "group": ["minority"] * 2 + ["majority"] * 8,
        "amount": [10.0, 11.0] + [100.0 + i for i in range(8)],
    })
    synthetic = raw.iloc[[0, 1, 2, 3, 4]].copy().reset_index(drop=True)

    escaped, report = escape_unique_clones(
        raw,
        synthetic,
        qi_columns=["group"],
        non_qi_columns=["amount"],
        random_state=42,
        return_report=True,
    )

    assert len(escaped) == len(synthetic)
    assert escaped["group"].value_counts(normalize=True)["minority"] == 2 / 5
    assert report["dropped_rows"] == 0
    assert report["escaped_full_clones"] >= 5


def test_unique_qi_combination_is_not_safe_with_non_qi_jitter_only():
    raw = pd.DataFrame({
        "region": ["A", "B", "C"],
        "amount": [10.0, 20.0, 30.0],
    })
    synthetic = pd.DataFrame({
        "region": ["A"],
        "amount": [10.25],
    })

    escaped, report = escape_unique_clones(
        raw,
        synthetic,
        qi_columns=["region"],
        non_qi_columns=["amount"],
        random_state=42,
        return_report=True,
    )

    assert report["unique_qi_candidates"] == 1
    assert report["unsafe_unique_qi_rows"] == 1
    assert not ((escaped["region"] == "A") & (escaped["amount"] == 10.25)).any()
    assert escaped.loc[0, "region"] != "A" or escaped.loc[0, "amount"] != 10.25


def test_escape_jitter_preserves_domain_constraints():
    raw = pd.DataFrame({"id": [1], "amount": [50.0]})
    synthetic = raw.copy()

    escaped = escape_unique_clones(
        raw,
        synthetic,
        non_qi_columns=["amount"],
        bounds={"amount": (0, 100)},
        random_state=1,
    )

    assert 0 <= escaped.loc[0, "amount"] <= 100
    assert escaped.loc[0, "amount"] != 50.0


def test_exact_full_row_clone_rate_remains_zero():
    raw = pd.DataFrame({"category": ["a", "b"], "value": [1.0, 2.0]})
    synthetic = raw.copy()

    escaped = escape_unique_clones(raw, synthetic, non_qi_columns=["value"], random_state=8)
    assert not set(map(tuple, escaped.astype(object).values)).intersection(
        set(map(tuple, raw.astype(object).values))
    )


def test_escape_jitter_is_reproducible_with_seed():
    raw = pd.DataFrame({"category": ["a", "b"], "value": [1.0, 2.0]})
    synthetic = raw.copy()

    first = escape_unique_clones(raw, synthetic, non_qi_columns=["value"], random_state=11)
    second = escape_unique_clones(raw, synthetic, non_qi_columns=["value"], random_state=11)
    pd.testing.assert_frame_equal(first, second)
