# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import pandas as pd
from ...common.types import ColumnPlan
from ..base import BaseSynthesizer

class GaussianCopulaGenerator(BaseSynthesizer):
    def __init__(self):
        self.synthesizer = None
        self.plan = None

    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import GaussianCopulaSynthesizer

        self.plan = plan
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(training)

        if getattr(metadata, "primary_key", None):
            metadata.set_primary_key(column_name=None)

        for column in plan.categorical:
            if column in training.columns:
                metadata.update_column(column_name=column, sdtype="categorical")
        for column in plan.numerical:
            if column in training.columns:
                metadata.update_column(column_name=column, sdtype="numerical")

        self.synthesizer = GaussianCopulaSynthesizer(metadata)
        self.synthesizer.fit(training)

    def sample(self, num_rows: int, conditions: dict[str, Any] | None = None) -> pd.DataFrame:
        if self.synthesizer is None:
            raise RuntimeError("Model is not fitted.")
        from sdv.sampling import Condition

        if conditions:
            valid_conditions = {k: v for k, v in conditions.items() if v is not None and str(v).strip() != ""}
            if valid_conditions:
                try:
                    cond = Condition(num_rows=num_rows, column_values=valid_conditions)
                    return self.synthesizer.sample_from_conditions(conditions=[cond])
                except Exception as e:
                    print(f"[WARN] sample_from_conditions fallback: {e}")

        return self.synthesizer.sample(num_rows=num_rows)
