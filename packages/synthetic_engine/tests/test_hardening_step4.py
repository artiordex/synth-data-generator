# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.rules.base import DatasetSchemaConfig
from synthetic_engine.privacy.projection import project_domain_constraints


def test_dp_projection_restores_integer_domain():
    frame = pd.DataFrame({"count": [1.2, 2.8, np.nan]})
    plan = ColumnPlan([], ["count"], [], {}, {"count": {"integer": True, "min": 0, "max": 10}})

    projected = project_domain_constraints(frame, plan)
    assert str(projected["count"].dtype) == "Int64"
    assert projected["count"].tolist() == [1, 3, pd.NA]


def test_dp_projection_enforces_non_negative_bounds():
    frame = pd.DataFrame({"amount": [-10.0, 2.0]})
    plan = ColumnPlan([], ["amount"], [], {}, {"amount": {"non_negative": True}})

    projected = project_domain_constraints(frame, plan)
    assert (projected["amount"] >= 0).all()


def test_dp_projection_respects_public_schema_bounds():
    frame = pd.DataFrame({"score": [-100.0, 100.0]})
    schema = DatasetSchemaConfig(
        "public",
        numerical_columns=["score"],
        public_bounds={"score": {"min": 0, "max": 10, "integer": True}},
    )

    projected = project_domain_constraints(frame, ColumnPlan([], ["score"], [], {}, {}), schema=schema)
    assert projected["score"].tolist() == [0, 10]


def test_dp_projection_does_not_use_raw_exact_minmax_without_permission():
    frame = pd.DataFrame({"value": [-100.0, 100.0]})
    plan = ColumnPlan([], ["value"], [], {}, {})

    projected = project_domain_constraints(frame, plan)
    assert projected["value"].tolist() == [-100.0, 100.0]


def test_dp_projection_preserves_nullable_values():
    frame = pd.DataFrame({"count": [1.4, np.nan, 3.6]})
    plan = ColumnPlan([], ["count"], [], {}, {"count": {"integer": True, "min": 0, "max": 10}})

    projected = project_domain_constraints(frame, plan)
    assert pd.isna(projected.loc[1, "count"])
    assert projected["count"].dtype == "Int64"


def test_dp_projection_is_deterministic_after_seeded_noise():
    frame = pd.DataFrame({"amount": [-1.0, 2.3, 11.2]})
    plan = ColumnPlan([], ["amount"], [], {}, {"amount": {"min": 0, "max": 10}})

    first = project_domain_constraints(frame, plan)
    second = project_domain_constraints(frame, plan)
    pd.testing.assert_frame_equal(first, second)
