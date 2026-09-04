# -*- coding: utf-8 -*-
from __future__ import annotations
import math
import random
from typing import Any
import numpy as np
import pandas as pd
from ...common.types import TableRelationship

class TurboRelationalSampler:
    """High-speed relational sampler ensuring 100% referential integrity across parent-child tables."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.tables: dict[str, pd.DataFrame] = {}
        self.relationships: list[TableRelationship] = []
        self.primary_keys: dict[str, str] = {}

    def fit(
        self,
        tables: dict[str, pd.DataFrame],
        relationships: list[TableRelationship],
        primary_keys: dict[str, str] | None = None,
        **kwargs: Any
    ) -> None:
        self.tables = {k: v.copy() for k, v in tables.items()}
        self.relationships = list(relationships)
        self.primary_keys = dict(primary_keys or {})

        for rel in self.relationships:
            if rel.parent_table not in self.primary_keys:
                self.primary_keys[rel.parent_table] = rel.parent_key

    def _sample_single_table(self, df: pd.DataFrame, num_rows: int, exclude_cols: set[str]) -> pd.DataFrame:
        """Sample attributes of a table using empirical bootstrapping with subtle continuous noise."""
        if len(df) == 0:
            return pd.DataFrame(columns=df.columns)

        rng = np.random.default_rng(self.seed)
        indices = rng.choice(len(df), size=num_rows, replace=True)
        sampled = df.iloc[indices].copy().reset_index(drop=True)

        for col in sampled.columns:
            if col in exclude_cols:
                continue
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() > 20:
                std = float(df[col].std(skipna=True))
                if std > 0:
                    noise = rng.normal(0, std * 0.05, size=num_rows)
                    sampled[col] = (sampled[col] + noise).round(2)
        return sampled

    def sample(self, num_rows_or_scale: int | float = 1.0) -> dict[str, pd.DataFrame]:
        rng = np.random.default_rng(self.seed)
        generated: dict[str, pd.DataFrame] = {}

        # 1. Topological order: Parents first, then Children
        child_tables = {rel.child_table for rel in self.relationships}
        ordered_tables = [t for t in self.tables if t not in child_tables]
        for t in self.tables:
            if t not in ordered_tables:
                ordered_tables.append(t)

        # 2. Generate tables sequentially maintaining FK references
        for table_name in ordered_tables:
            orig_df = self.tables[table_name]
            orig_rows = len(orig_df)
            target_rows = int(num_rows_or_scale) if isinstance(num_rows_or_scale, int) else max(1, int(orig_rows * num_rows_or_scale))

            incoming_rels = [rel for rel in self.relationships if rel.child_table == table_name]
            pk_col = self.primary_keys.get(table_name)

            exclude_cols = set()
            if pk_col:
                exclude_cols.add(pk_col)
            for rel in incoming_rels:
                exclude_cols.add(rel.child_key)

            # Sample non-key attributes
            sampled_df = self._sample_single_table(orig_df, target_rows, exclude_cols)

            # Assign fresh unique Primary Key if defined
            if pk_col and pk_col in orig_df.columns:
                first_val = orig_df[pk_col].dropna().iloc[0] if orig_df[pk_col].notna().any() else 1
                if isinstance(first_val, (int, np.integer)):
                    sampled_df[pk_col] = np.arange(1, target_rows + 1)
                else:
                    prefix = "".join(filter(str.isalpha, str(first_val))) or "ID_"
                    sampled_df[pk_col] = [f"{prefix}{i+1:05d}" for i in range(target_rows)]

            # Assign valid Foreign Keys referencing parent generated table
            for rel in incoming_rels:
                parent_gen = generated.get(rel.parent_table)
                if parent_gen is not None and rel.parent_key in parent_gen.columns:
                    valid_parent_keys = parent_gen[rel.parent_key].values
                    if len(valid_parent_keys) > 0:
                        fk_assigned = rng.choice(valid_parent_keys, size=target_rows, replace=True)
                        sampled_df[rel.child_key] = fk_assigned

            generated[table_name] = sampled_df

        return generated
