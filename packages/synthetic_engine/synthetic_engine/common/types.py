# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ColumnPlan:
    categorical: list[str]
    numerical: list[str]
    ignored: list[str]
    pii: dict[str, dict[str, Any]]
    rules: dict[str, dict[str, Any]]

@dataclass
class SynthesisConfig:
    model_type: str = "ctgan"
    sample_rows: int = 1000
    epochs: int = 30
    batch_size: int = 64
    pac: int = 1
    dp_enabled: bool = False
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5
    seed: int = 42
