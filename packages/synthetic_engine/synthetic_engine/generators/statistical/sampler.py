# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from ...common.types import ColumnPlan
from ..base import BaseSynthesizer

class StatisticalSampler(BaseSynthesizer):
    def __init__(self):
        self.training = None
        self.plan = None

    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        self.training = training.copy()
        self.plan = plan

    def sample(self, num_rows: int, conditions: dict[str, Any] | None = None) -> pd.DataFrame:
        output = pd.DataFrame(index=range(num_rows))
        sub_training = self.training.copy()

        if conditions:
            for col, val in conditions.items():
                if col in sub_training.columns and val is not None and str(val).strip() != "":
                    filtered = sub_training[sub_training[col].astype(str) == str(val)]
                    if not filtered.empty:
                        sub_training = filtered

        for column in self.plan.categorical:
            if column not in sub_training.columns:
                continue
            distribution = sub_training[column].astype("string").value_counts(normalize=True, dropna=False)
            output[column] = np.random.choice(distribution.index.astype(str), size=num_rows, p=distribution.values)

        for column in self.plan.numerical:
            if column not in sub_training.columns:
                continue
            series = pd.to_numeric(sub_training[column], errors="coerce").dropna()
            if series.empty:
                output[column] = np.nan
                continue
            output[column] = np.random.choice(series.values, size=num_rows, replace=True)

        if conditions:
            for col, val in conditions.items():
                if col in output.columns and val is not None and str(val).strip() != "":
                    output[col] = val

        return output
