# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: enums.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/enums.py
# 목적: 문서 블록, 텍스트 스타일, 정렬 등 공통 열거형을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Format-independent document vocabulary."""
from enum import Enum


class UnderlineStyle(str, Enum):
    """Underline appearance."""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    DOTTED = "dotted"
    DASHED = "dashed"
    WAVY = "wavy"


class StrikeStyle(str, Enum):
    """Strike appearance."""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"


class ParagraphAlign(str, Enum):
    """Paragraph alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"
    DISTRIBUTE = "distribute"


class TableAlign(str, Enum):
    """Table alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VerticalAlign(str, Enum):
    """Cell vertical alignment."""
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class BorderStyle(str, Enum):
    """Border line patterns including explicit absence."""
    NONE = "none"
    SOLID = "solid"
    DOUBLE = "double"
    DOTTED = "dotted"
    DASHED = "dashed"
    DASH_DOT = "dash_dot"


class ImagePlacement(str, Enum):
    """Image relationship to text."""
    INLINE = "inline"
    SQUARE = "square"
    BEHIND = "behind"
    IN_FRONT = "in_front"


class PageOrientation(str, Enum):
    """Physical page orientation."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class Severity(str, Enum):
    """Diagnostic importance."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SupportStatus(str, Enum):
    """Distinguish explicit facts, inference and unsupported data."""
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    INFERRED = "inferred"


class FidelityProfile(str, Enum):
    """Conversion priority, not a quality score."""
    AUTO = "auto"
    TEXT = "text"
    STRUCTURAL = "structural"
    VISUAL = "visual"
