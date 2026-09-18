# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: capabilities.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/capabilities.py
# 목적: 포맷별 지원 기능 및 제약 사항 메타데이터를 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Capability declarations, independent of future renderer implementations."""

from dataclasses import dataclass, fields
from typing import Iterable


@dataclass(frozen=True)
class TargetCapabilities:
    """Declare implemented native features; defaults make no support claims.

    A renderer must separately report any degradation for missing features.
    Support is not assumed merely because a file format permits a feature.
    """

    supports_pages: bool = False
    supports_headers: bool = False
    supports_footers: bool = False
    supports_nested_tables: bool = False
    supports_rowspan: bool = False
    supports_colspan: bool = False
    supports_floating_images: bool = False
    supports_text_boxes: bool = False
    supports_font_scaling: bool = False
    supports_letter_spacing: bool = False
    supports_diagonal_borders: bool = False

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        """
            @description post init 작업을 수행함
        """
        for definition in fields(self):
            if not isinstance(getattr(self, definition.name), bool):
                raise TypeError(f"{definition.name} must be a boolean.")

    # unsupported features 작업을 수행함
    def unsupported_features(self, required: Iterable[str]) -> tuple[str, ...]:
        """Return missing field names in request order, without duplicates.

        Unknown names fail explicitly so spelling mistakes cannot silently pass.
        """
        known = {definition.name for definition in fields(self)}
        missing: list[str] = []
        for name in required:
            if name not in known:
                raise ValueError(f"Unknown target capability: {name}")
            if not getattr(self, name) and name not in missing:
                missing.append(name)
        return tuple(missing)
