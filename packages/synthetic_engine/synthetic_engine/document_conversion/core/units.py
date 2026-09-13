# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: units.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/units.py
# 목적: pt, px, mm, emu 등 문서 좌표 및 단위 변환 유틸리티를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Conversions to and from points, the document IR's single layout unit."""

from math import isfinite


# finite 작업을 수행함
def _finite(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("A document length must be a real number, not a boolean.")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("Document lengths must be finite.") from exc
    if not isfinite(result):
        raise ValueError("Document lengths must be finite.")
    return result


# scale 작업을 수행함
def _scale(value: float, factor: float) -> float:
    return _finite(_finite(value) * factor)


# inch to pt 작업을 수행함
def inch_to_pt(value: float) -> float:
    """Convert inches to points without quantization."""
    return _scale(value, 72.0)


# pt to inch 작업을 수행함
def pt_to_inch(value: float) -> float:
    """Convert points to inches without quantization."""
    return _finite(value) / 72.0


# hwpunit to pt 작업을 수행함
def hwpunit_to_pt(value: float) -> float:
    """Convert HWPUNIT (1/7200 inch) to points."""
    return _finite(value) / 100.0


# pt to hwpunit 작업을 수행함
def pt_to_hwpunit(value: float) -> float:
    """Convert points to HWPUNIT; serialization decides integer rounding."""
    return _scale(value, 100.0)


# emu to pt 작업을 수행함
def emu_to_pt(value: float) -> float:
    """Convert English Metric Units to points."""
    return _finite(value) / 12700.0


# pt to emu 작업을 수행함
def pt_to_emu(value: float) -> float:
    """Convert points to EMU without premature integer rounding."""
    return _scale(value, 12700.0)


# twip to pt 작업을 수행함
def twip_to_pt(value: float) -> float:
    """Convert twentieths of a point to points."""
    return _finite(value) / 20.0


# pt to twip 작업을 수행함
def pt_to_twip(value: float) -> float:
    """Convert points to twentieths of a point."""
    return _scale(value, 20.0)
