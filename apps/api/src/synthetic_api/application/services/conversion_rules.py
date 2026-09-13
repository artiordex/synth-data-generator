# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: conversion_rules.py
# 경로: apps/api/src/synthetic_api/application/services/conversion_rules.py
# 목적: 문서 포맷 간 변환 규칙, 매핑 및 제약사항을 관리함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
"""Central conversion contract used by the upload API and clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


class ConversionRuleError(ValueError):
    """Raised when a source/target pair is outside the supported contract."""


SourceKind = Literal["document", "dataset"]
PreviewMode = Literal["html", "markdown", "sql", "table", "none"]


@dataclass(frozen=True)
class ConversionRule:
    source: str
    source_kind: SourceKind
    target: str
    output_extension: str
    preview_mode: PreviewMode
    description: str


SOURCE_ALIASES = {".pq": ".parquet"}
TARGET_ALIASES = {
    "markdown": "md", "md": "md", "htm": "html", "html": "html",
    "word": "docx", "doc": "docx", "docx": "docx",
    "xls": "xlsx", "xlsx": "xlsx", "pq": "parquet", "parquet": "parquet",
}

IMAGE_SOURCES = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".heic"})
DOCUMENT_SOURCES = frozenset({".hwp", ".hwpx", ".doc", ".docx", ".pdf", ".md"}) | IMAGE_SOURCES
DATASET_SOURCES = frozenset({".csv", ".xlsx", ".xls", ".tsv", ".txt", ".json", ".jsonl", ".xml", ".parquet", ".pq"})

# This matrix mirrors the implemented branches in converter.py. A new exporter
# must be added here before it is exposed by the API or UI.
DOCUMENT_TARGETS = {
    ".hwp": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx", "hwp"}),
    ".hwpx": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx", "hwp"}),
    ".doc": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx"}),
    ".docx": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx"}),
    ".pdf": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx", "hwp"}),
    ".md": frozenset({"md", "txt", "pdf", "hwpx", "html", "xlsx", "docx"}),
    ".png": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".jpg": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".jpeg": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".tif": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".tiff": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".bmp": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".webp": frozenset({"md", "txt", "html", "docx", "pdf"}),
    ".heic": frozenset({"md", "txt", "html", "docx", "pdf"}),
}
DATASET_TARGETS = frozenset({"md", "html", "csv", "xlsx", "tsv", "json", "jsonl", "xml", "parquet", "sql"})


# 입력 파일명 또는 확장자 문자열을 표준 소문자 확장자로 정규화함
def normalize_source(filename_or_extension: str) -> str:
    value = filename_or_extension.strip().lower()
    extension = value if value.startswith(".") else Path(value).suffix
    extension = SOURCE_ALIASES.get(extension, extension)
    if not extension:
        raise ConversionRuleError("파일 확장자를 확인할 수 없습니다.")
    return extension


# 변환 대상 포맷 문자열을 표준 타깃 코드로 정규화함
def normalize_target(target: str) -> str:
    if not isinstance(target, str) or not target.strip():
        raise ConversionRuleError("변환 대상 포맷이 필요합니다.")
    value = target.strip().lower().lstrip(".")
    return TARGET_ALIASES.get(value, value)


# 입력 포맷이 문서(document)인지 데이터셋(dataset)인지 구분 판별함
def source_kind(source: str) -> SourceKind:
    normalized = normalize_source(source)
    if normalized in DOCUMENT_SOURCES:
        return "document"
    if normalized in DATASET_SOURCES:
        return "dataset"
    raise ConversionRuleError(f"지원하지 않는 입력 포맷입니다: {normalized}")


# 타깃 포맷과 소스 유형에 적합한 미리보기 렌더링 모드를 결정함
def _preview_mode(target: str, kind: SourceKind) -> PreviewMode:
    if target == "html":
        return "html"
    if target == "md":
        return "markdown"
    if target == "sql":
        return "sql"
    if kind == "dataset" and target in {"csv", "xlsx", "tsv", "json", "jsonl", "xml", "parquet"}:
        return "table"
    return "none"


# 입력 포맷과 타깃 포맷 쌍에 대한 변환 규칙 및 출력 스펙을 확정함
def resolve_rule(filename_or_extension: str, target: str) -> ConversionRule:
    source = normalize_source(filename_or_extension)
    target_code = normalize_target(target)
    kind = source_kind(source)
    allowed = DOCUMENT_TARGETS[source] if kind == "document" else DATASET_TARGETS
    if target_code not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ConversionRuleError(
            f"{source}에서 {target_code} 변환은 지원하지 않습니다. 허용 대상: {allowed_text}"
        )
    return ConversionRule(
        source=source,
        source_kind=kind,
        target=target_code,
        output_extension=f".{target_code}",
        preview_mode=_preview_mode(target_code, kind),
        description=f"{source.removeprefix('.').upper()} → {target_code.upper()}",
    )


# 특정 입력 포맷에서 변환 가능한 모든 타깃 규칙 목록을 반환함
def rules_for_source(filename_or_extension: str) -> list[dict[str, str]]:
    source = normalize_source(filename_or_extension)
    kind = source_kind(source)
    targets = DOCUMENT_TARGETS[source] if kind == "document" else DATASET_TARGETS
    return [asdict(resolve_rule(source, target)) for target in sorted(targets)]


# 시스템 전체에서 지원하는 모든 입력 포맷별 변환 규칙 카탈로그를 반환함
def catalog() -> dict[str, list[dict[str, str]]]:
    aliases = set(SOURCE_ALIASES)
    sources = sorted((DOCUMENT_SOURCES | DATASET_SOURCES) - aliases)
    return {source: rules_for_source(source) for source in sources}
