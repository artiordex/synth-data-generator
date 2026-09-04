# -*- coding: utf-8 -*-
from __future__ import annotations
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan

class BaseSynthesizer(ABC):
    """Abstract base class for all synthetic data generators."""

    @abstractmethod
    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        """Fit generator on training data according to column plan."""
        pass

    @abstractmethod
    def sample(self, num_rows: int, conditions: dict[str, Any] | None = None) -> pd.DataFrame:
        """Sample synthetic rows from the fitted model."""
        pass

    def save(self, file_path: str | Path) -> None:
        """Serialize synthesizer state and weights to file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, file_path: str | Path) -> BaseSynthesizer:
        """Deserialize synthesizer instance from file."""
        target = Path(file_path)
        if not target.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {target}")
        with target.open("rb") as f:
            instance = pickle.load(f)
        if not isinstance(instance, BaseSynthesizer):
            raise TypeError(f"Loaded object is not a BaseSynthesizer: {type(instance)}")
        return instance

