# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: duckdb_profiler.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/duckdb_profiler.py
# 목적: DuckDB 인메모리 OLAP SQL 엔진 기반 대용량 데이터 초고속 통계 분석기
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import pandas as pd


def profile_dataset_with_duckdb(
    data: Union[pd.DataFrame, str, Path],
    max_categories: int = 10,
) -> Dict[str, Any]:
    """
    DuckDB 인메모리 C++ OLAP 엔진을 활용하여 대용량(수십만~수백만 행) 데이터셋을
    단 수 밀리초(ms) 만에 초고속으로 프로파일링하고 기초 통계를 산출합니다.
    """
    con = duckdb.connect(database=":memory:")
    start_time = time.time()

    # Register table based on input type
    if isinstance(data, pd.DataFrame):
        con.register("df_table", data)
        table_name = "df_table"
    elif isinstance(data, (str, Path)):
        p = Path(data)
        if p.suffix.lower() == ".parquet":
            con.execute(f"CREATE VIEW df_table AS SELECT * FROM read_parquet('{str(p).replace('\\', '/')}')")
        else:
            con.execute(f"CREATE VIEW df_table AS SELECT * FROM read_csv_auto('{str(p).replace('\\', '/')}')")
        table_name = "df_table"
    else:
        raise ValueError("Unsupported data input type for DuckDB profiler.")

    # 1. Total rows & schema
    total_rows = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
    schema_info = con.execute(f"DESCRIBE {table_name}").fetchall()

    columns_summary: Dict[str, Any] = {}

    for col_name, col_type, null_ok, key, default, extra in schema_info:
        # SQL-escaped column name
        c_esc = f'"{col_name}"'

        # Null count and distinct count
        null_count, distinct_count = con.execute(
            f"SELECT count(*) FILTER (WHERE {c_esc} IS NULL), count(DISTINCT {c_esc}) FROM {table_name}"
        ).fetchone()

        col_stat: Dict[str, Any] = {
            "type": col_type,
            "null_count": int(null_count),
            "null_ratio": round(null_count / max(1, total_rows), 4),
            "distinct_count": int(distinct_count),
        }

        # Numeric statistics
        is_numeric = any(t in col_type.upper() for t in ("INT", "BIGINT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "HUGEINT"))
        if is_numeric:
            min_val, max_val, avg_val, std_val = con.execute(
                f"SELECT min({c_esc}), max({c_esc}), avg({c_esc}), stddev({c_esc}) FROM {table_name} WHERE {c_esc} IS NOT NULL"
            ).fetchone()
            col_stat.update({
                "is_numeric": True,
                "min": float(min_val) if min_val is not None else None,
                "max": float(max_val) if max_val is not None else None,
                "mean": round(float(avg_val), 4) if avg_val is not None else None,
                "std": round(float(std_val), 4) if std_val is not None else None,
            })
        else:
            col_stat["is_numeric"] = False
            # Top frequent categories
            top_cats = con.execute(
                f"SELECT {c_esc}, count(*) as cnt FROM {table_name} WHERE {c_esc} IS NOT NULL GROUP BY {c_esc} ORDER BY cnt DESC LIMIT {max_categories}"
            ).fetchall()
            col_stat["top_values"] = [{"value": str(v), "count": int(c)} for v, c in top_cats]

        columns_summary[col_name] = col_stat

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    con.close()

    return {
        "engine": "DuckDB-OLAP",
        "total_rows": int(total_rows),
        "total_columns": len(schema_info),
        "columns": columns_summary,
        "execution_time_ms": elapsed_ms,
    }
