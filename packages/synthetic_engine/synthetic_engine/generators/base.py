# -*- coding: utf-8 -*-
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan

class BaseSynthesizer(ABC):
    @abstractmethod
    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def sample(self, num_rows: int, conditions: dict[str, Any] | None = None) -> pd.DataFrame:
        pass
