# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: text_layer.py
# 경로: packages/ocr/ocr/pdf/text_layer.py
# 목적: PDF 내장 네이티브 텍스트 레이어 추출 및 좌표 분석을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PDF native text-layer quality checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..pipeline.models import ErrorCode


KOREAN_RE = re.compile(r"[가-힣]")


@dataclass(frozen=True)
class PdfTextLayerQuality:
    """Quality signals for deciding native text vs OCR fallback."""

    char_count: int
    control_character_ratio: float
    broken_character_ratio: float
    korean_character_ratio: float
    valid: bool
    issues: tuple[ErrorCode, ...]


# 텍스트 layer 품질 및 지표를 평가함
def evaluate_text_layer(text: str) -> PdfTextLayerQuality:
    """Evaluate native PDF text without normalizing away evidence."""

    char_count = len(text)
    if char_count == 0:
        return PdfTextLayerQuality(
            char_count=0,
            control_character_ratio=0.0,
            broken_character_ratio=0.0,
            korean_character_ratio=0.0,
            valid=False,
            issues=(ErrorCode.TEXT_EMPTY, ErrorCode.OCR_REQUIRED),
        )
    control_chars = sum(1 for character in text if ord(character) < 32 and character not in "\n\r\t")
    broken_chars = text.count("�") + text.count("□") + text.count("▯")
    korean_chars = len(KOREAN_RE.findall(text))
    control_ratio = control_chars / char_count
    broken_ratio = broken_chars / char_count
    issues: list[ErrorCode] = []
    if char_count < 10:
        issues.append(ErrorCode.TEXT_EMPTY)
    if control_ratio >= 0.02:
        issues.append(ErrorCode.TEXT_ENCODING_ERROR)
    if broken_ratio >= 0.02:
        issues.append(ErrorCode.TEXT_BROKEN_CHARACTER)
    if issues:
        issues.append(ErrorCode.OCR_REQUIRED)
    return PdfTextLayerQuality(
        char_count=char_count,
        control_character_ratio=control_ratio,
        broken_character_ratio=broken_ratio,
        korean_character_ratio=korean_chars / char_count,
        valid=not issues,
        issues=tuple(dict.fromkeys(issues)),
    )
