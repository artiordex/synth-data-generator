# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: catalog.py
# 경로: packages/synthetic_engine/synthetic_engine/rules/catalog.py
# 목적: 시맨틱 컬럼 매퍼와 외부 프로파일 레지스트리 호환 API를 제공함
# =============================================================================
"""기존 카탈로그 API를 유지하는 선언형 프로파일 진입점.

데이터셋명·컬럼명·업무규칙의 실제 값은 ``profiles.yaml``에 있다.
이 모듈에는 특정 데이터셋별 생성 분기를 두지 않고, 기존 호출부와의
호환을 위한 ``get_dataset_catalog``/``match_dataset_schema``만 제공한다.
"""
from __future__ import annotations

import re
from os import PathLike
from typing import Any

from .base import DatasetSchemaConfig
from .profile_registry import ProfileRegistry, default_engine_settings, default_profile_registry


_SEMANTIC_SETTINGS = default_engine_settings().get("semantic", {})
_SYNONYM_PAIRS = [
    (str(pair[0]), str(pair[1]))
    for pair in _SEMANTIC_SETTINGS.get("synonym_pairs", [])
    if isinstance(pair, (list, tuple)) and len(pair) == 2
]


def resolve_column_name(target: Any, candidates: Any) -> str | None:
    """실제 컬럼명 목록에서 후보 동의어/패턴에 맞는 컬럼명을 찾는다.

    DataFrame, 리스트, 인덱스, 단일 문자열 및 인자 순서 역전을 지원한다.
    동의어 사전은 특정 데이터셋의 업무 분기가 아니라 범용 컬럼명 정규화
    규칙이므로 엔진 연산자와 함께 유지한다.
    """
    if target is None or candidates is None:
        return None

    # 인자 뒤바뀜 처리 (예: resolve_column_name("신청일자", cols))
    if isinstance(target, str) and not isinstance(candidates, str):
        target, candidates = candidates, target

    if isinstance(candidates, str):
        cand_list = [candidates]
    elif hasattr(candidates, "__iter__") and not isinstance(candidates, (bytes, bytearray)):
        cand_list = list(candidates)
    else:
        cand_list = [str(candidates)]

    if hasattr(target, "columns"):
        existing_cols = list(target.columns)
    elif hasattr(target, "__iter__") and not isinstance(target, (str, bytes, bytearray)):
        existing_cols = list(target)
    else:
        existing_cols = [str(target)]

    # 1. 완전 일치 우선 탐색
    for cand in cand_list:
        if cand in existing_cols:
            return cand

    # 2. 정규화 비교 (공백, 밑줄, 괄호 제거 후 소문자 비교)
    def normalize(text: str) -> str:
        return re.sub(r"[\s_()\[\]\-_/]", "", str(text)).lower()

    def canonicalize(text: str) -> str:
        value = normalize(text)
        for source, destination in _SYNONYM_PAIRS:
            value = value.replace(source, destination)
        return value

    normalized_map = {normalize(col): col for col in existing_cols}
    canonical_map = {canonicalize(col): col for col in existing_cols}

    for cand in cand_list:
        normalized = normalize(cand)
        if normalized in normalized_map:
            return normalized_map[normalized]
        canonical = canonicalize(cand)
        if canonical in canonical_map:
            return canonical_map[canonical]

    # 3. 부분 일치 (후보어가 컬럼명에 포함되거나 반대인 경우)
    for cand in cand_list:
        normalized = normalize(cand)
        canonical = canonicalize(cand)
        if len(normalized) < 2:
            continue
        for normalized_col, original_col in normalized_map.items():
            if normalized in normalized_col or normalized_col in normalized:
                return original_col
        for canonical_col, original_col in canonical_map.items():
            if canonical in canonical_col or canonical_col in canonical:
                return original_col

    return None


def get_dataset_catalog(
    profile_path: str | PathLike[str] | None = None,
) -> list[DatasetSchemaConfig]:
    """기본 또는 지정한 외부 프로파일 레지스트리를 반환한다."""
    return default_profile_registry(external_path=profile_path).profiles


def match_dataset_schema(
    df: Any = None,
    dataset_hint: str = "",
    *,
    cols: list[str] | None = None,
    dataset_name: str = "",
    profile_path: str | PathLike[str] | None = None,
) -> DatasetSchemaConfig | None:
    """데이터셋 힌트와 컬럼 구성으로 가장 적합한 프로파일을 찾는다.

    기존 ``df``, ``cols``, ``dataset_hint``, ``dataset_name`` 호출 형태를
    유지하면서, 테스트·운영에서 별도 레지스트리를 직접 지정할 수 있다.
    """
    registry: ProfileRegistry = default_profile_registry(external_path=profile_path)
    return registry.match(df=df, dataset_hint=dataset_hint, cols=cols, dataset_name=dataset_name)


__all__ = [
    "get_dataset_catalog",
    "match_dataset_schema",
    "resolve_column_name",
]
