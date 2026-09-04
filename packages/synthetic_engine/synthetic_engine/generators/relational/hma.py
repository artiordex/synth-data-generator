# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import pandas as pd
from ...common.types import TableRelationship

class HMARelationalSynthesizer:
    """Multi-table hierarchical relational synthesizer using SDV HMASynthesizer."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.synthesizer = None
        self.metadata = None
        self.table_names: list[str] = []

    def fit(
        self,
        tables: dict[str, pd.DataFrame],
        relationships: list[TableRelationship],
        primary_keys: dict[str, str] | None = None,
        **kwargs: Any
    ) -> None:
        from sdv.metadata import MultiTableMetadata
        from sdv.multi_table import HMASynthesizer

        self.metadata = MultiTableMetadata()
        self.table_names = list(tables.keys())
        pkeys = primary_keys or {}

        # 1. Detect metadata for each table
        for table_name, df in tables.items():
            self.metadata.detect_table_from_dataframe(
                table_name=table_name,
                data=df
            )
            # Set primary key if specified or inferred
            if table_name in pkeys:
                self.metadata.set_primary_key(table_name=table_name, column_name=pkeys[table_name])

        # 2. Add relationships
        for rel in relationships:
            if rel.parent_table in tables and rel.child_table in tables:
                parent_pk = rel.parent_key
                try:
                    self.metadata.set_primary_key(table_name=rel.parent_table, column_name=parent_pk)
                except Exception:
                    pass

                self.metadata.add_relationship(
                    parent_table_name=rel.parent_table,
                    child_table_name=rel.child_table,
                    parent_primary_key=rel.parent_key,
                    child_foreign_key=rel.child_key
                )

        self.synthesizer = HMASynthesizer(
            self.metadata,
            verbose=self.verbose
        )
        self.synthesizer.fit(tables)

    def sample(self, scale: float = 1.0) -> dict[str, pd.DataFrame]:
        if self.synthesizer is None:
            raise RuntimeError("HMARelationalSynthesizer is not fitted.")
        return self.synthesizer.sample(scale=scale)
