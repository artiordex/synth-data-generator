"""Supported export formats and their canonical aliases."""
from __future__ import annotations


FORMAT_ALIASES = {
    "pq": "parquet",
    "htm": "html",
    "hwpt": "hwpt",
}

SUPPORTED_EXPORT_FORMATS = frozenset(
    {
        "csv",
        "tsv",
        "xlsx",
        "xls",
        "json",
        "parquet",
        "txt",
        "md",
        "html",
        "docx",
        "hwpx",
        "hwp",
        "hwpt",
        "pdf",
    }
)


def normalize_export_format(value: str | None) -> str:
    """Normalize a requested format while preserving legacy aliases."""
    raw = (value or "csv").strip().lower().lstrip(".")
    return FORMAT_ALIASES.get(raw, raw)


__all__ = ["FORMAT_ALIASES", "SUPPORTED_EXPORT_FORMATS", "normalize_export_format"]
