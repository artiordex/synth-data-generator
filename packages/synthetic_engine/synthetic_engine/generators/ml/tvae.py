# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing import Any
import pandas as pd
from ...common.types import ColumnPlan
from ..base import BaseSynthesizer
from ..registry import register_synthesizer

@register_synthesizer("tvae")
class TVAEGenerator(BaseSynthesizer):
    def __init__(self, epochs: int = 30, batch_size: int = 64, enable_gpu: bool = False):
        self.epochs = max(1, epochs)
        self.batch_size = batch_size
        self.enable_gpu = enable_gpu
        self.synthesizer = None
        self.plan = None

        try:
            import torch
            torch.set_num_threads(min(os.cpu_count() or 4, 8))
        except Exception:
            pass

    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import TVAESynthesizer

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

        self.batch_size = min(len(training), self.batch_size)
        self.synthesizer = TVAESynthesizer(
            metadata,
            epochs=self.epochs,
            batch_size=self.batch_size,
            enable_gpu=self.enable_gpu,
        )
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
