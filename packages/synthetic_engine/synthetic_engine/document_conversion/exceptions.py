# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: exceptions.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/exceptions.py
# 목적: 문서 파싱 및 렌더링 예외 계층 구조를 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Explicit errors raised by the document conversion engine."""


class DocumentConversionError(ValueError):
    """Invalid document data or an unfulfillable conversion request."""


class GeometryError(DocumentConversionError):
    """Invalid or infeasible table geometry."""


class UnsupportedFeatureError(DocumentConversionError):
    """A requested feature has no supported representation."""
