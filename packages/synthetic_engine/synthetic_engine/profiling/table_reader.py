"""Input table loading separated from profiling and column classification."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DOCUMENT_SUFFIXES = {".pdf", ".hwp", ".hwpx", ".hwpt", ".docx", ".doc", ".md"}
DELIMITED_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


def _read_delimited(path: Path, *, sep: str | None = None) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None
    for encoding in DELIMITED_ENCODINGS:
        try:
            kwargs = {"encoding": encoding}
            if sep is not None:
                kwargs["sep"] = sep
            return pd.read_csv(path, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error or ValueError(f"Unable to read delimited file: {path}")


def _read_json(path: Path) -> pd.DataFrame:
    try:
        return pd.read_json(path)
    except Exception:
        try:
            return pd.read_json(path, lines=True)
        except Exception:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            if isinstance(data, list):
                return pd.json_normalize(data)
            if isinstance(data, dict):
                for key in ("data", "records", "items", "rows", "values"):
                    if isinstance(data.get(key), list):
                        return pd.json_normalize(data[key])
                return pd.DataFrame(data)
            raise ValueError(f"Unable to parse JSON file as tabular dataset: {path}")


def read_table(path: Path | str, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read a tabular input and route document formats to the document reader."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    suffix = source.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source, sheet_name=sheet_name)
    if suffix == ".csv":
        return _read_delimited(source)
    if suffix in {".tsv", ".txt"}:
        return _read_delimited(source, sep="\t")
    if suffix in {".json", ".jsonl"}:
        return _read_json(source)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    if suffix in DOCUMENT_SUFFIXES:
        # Keep document-specific extraction in the profiling module until its
        # parser adapters are migrated to the shared document-conversion IR.
        from .analyzer import _read_document_as_dataframe

        return _read_document_as_dataframe(source)
    raise ValueError(
        f"Unsupported input file type: {suffix} (supported: CSV, XLSX, XLS, TSV, "
        "JSON, PARQUET, PDF, HWP, HWPX, HWPT, DOC, DOCX, MD)"
    )


__all__ = ["DOCUMENT_SUFFIXES", "read_table"]
