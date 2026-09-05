# -*- coding: utf-8 -*-
from __future__ import annotations
import random
from typing import Any
import numpy as np
import pandas as pd
from faker import Faker
from ...common.catalog import DomainCatalog
from ...privacy.faker import ContextAwareFaker
from .engine import RuleEngine

class DummyDataGenerator:
    """High-speed dummy data generator from schema definitions without requiring raw data."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.fake = Faker("ko_KR")
        Faker.seed(seed)
        random.seed(seed)
        np.random.seed(seed)

    def generate(self, columns: list[dict[str, Any]], num_rows: int = 1000,
                 scenario: str = "normal") -> pd.DataFrame:
        """Generate a DataFrame based on column definitions and standard domain rules."""
        num_rows = max(1, min(num_rows, 500000))
        data: dict[str, list[Any]] = {}

        # 1. Resolve rules for each column
        resolved_columns: list[dict[str, Any]] = []
        for col_def in columns:
            col_name = col_def.get("name", "col")
            domain_id = col_def.get("domain_id")
            rule = col_def.get("rule")

            domain = DomainCatalog.get_domain(domain_id) if domain_id else None
            if not domain:
                domain = DomainCatalog.infer_domain_by_name(col_name)

            effective_rule = rule or domain.get("rule", { "type": "choice", "values": ["Sample_A", "Sample_B"] })
            resolved_columns.append({
                "name": col_name,
                "domain": domain,
                "rule": effective_rule,
                "primary_key": bool(col_def.get("primary_key")),
                "unique": bool(col_def.get("unique")),
                "nullable": bool(col_def.get("nullable", True)),
            })

        # 2. Fast column-by-column generation
        col_data: dict[str, list[Any] | np.ndarray] = {}
        for item in resolved_columns:
            col_name = item["name"]
            rule = item["rule"]
            rule_type = rule.get("type")

            if rule_type == "faker":
                provider = rule.get("provider", "word")
                values = []
                # Check if generator exists in ContextAwareFaker
                for _ in range(num_rows):
                    val = ContextAwareFaker.faker_value_coherent(self.fake, provider, col_name, {})
                    values.append(val)
                col_data[col_name] = values

            elif rule_type in ("sequence", "number_range", "choice", "date_between", "constant", "pattern"):
                col_data[col_name] = RuleEngine.apply_rule_column(num_rows, rule)

            else:
                # Default fallback
                values = rule.get("values", ["A", "B", "C"])
                col_data[col_name] = np.random.choice(values, size=num_rows)

        frame = pd.DataFrame(col_data)
        for item in resolved_columns:
            if not (item["primary_key"] or item["unique"]):
                continue
            name = item["name"]
            seen: dict[str, int] = {}
            unique_values = []
            for value in frame[name]:
                key = str(value)
                occurrence = seen.get(key, 0)
                seen[key] = occurrence + 1
                unique_values.append(value if occurrence == 0 else f"{value}-{occurrence + 1}")
            frame[name] = unique_values
        return self._apply_scenario(frame, resolved_columns, scenario)

    @staticmethod
    def _apply_scenario(frame: pd.DataFrame, columns: list[dict[str, Any]], scenario: str) -> pd.DataFrame:
        """Add deterministic boundary or intentionally invalid rows for test fixtures."""
        if frame.empty or scenario == "normal":
            return frame
        output = frame.copy()
        if scenario in {"boundary", "mixed"}:
            for item in columns:
                name, rule = item["name"], item["rule"]
                if name not in output:
                    continue
                if rule.get("type") == "number_range":
                    output.at[0, name] = rule.get("min", 0)
                    if len(output) > 1:
                        output.at[1, name] = rule.get("max", 1)
                elif rule.get("type") in {"choice", "pattern", "faker"}:
                    output.at[0, name] = ""
        if scenario in {"invalid", "mixed"}:
            count = max(1, min(len(output), round(len(output) * (1.0 if scenario == "invalid" else 0.05))))
            for item in columns:
                name, rule = item["name"], item["rule"]
                if name not in output:
                    continue
                if rule.get("type") == "number_range":
                    maximum = float(rule.get("max", 1))
                    output.loc[:count - 1, name] = maximum + max(abs(maximum), 1) + 1
                else:
                    output.loc[:count - 1, name] = None
        return output

    @staticmethod
    def to_sql_insert(df: pd.DataFrame, table_name: str = "dummy_table", limit: int = 10000) -> str:
        """Generate SQL INSERT statements for seeding databases."""
        export_df = df.head(limit)
        cols = [f"`{c}`" for c in export_df.columns]
        col_str = ", ".join(cols)

        lines = [f"-- Generated by SynthDataGenerator Quick Dummy Engine", f"-- Table: {table_name}, Rows: {len(export_df)}", ""]

        batch_size = 500
        for i in range(0, len(export_df), batch_size):
            chunk = export_df.iloc[i : i + batch_size]
            val_rows = []
            for _, row in chunk.iterrows():
                row_vals = []
                for val in row:
                    if pd.isna(val):
                        row_vals.append("NULL")
                    elif isinstance(val, (int, float, np.number)):
                        row_vals.append(str(val))
                    else:
                        clean_str = str(val).replace("'", "''")
                        row_vals.append(f"'{clean_str}'")
                val_rows.append(f"  ({', '.join(row_vals)})")
            
            insert_stmt = f"INSERT INTO `{table_name}` ({col_str}) VALUES\n" + ",\n".join(val_rows) + ";"
            lines.append(insert_stmt)
            lines.append("")

        return "\n".join(lines)
