# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/text/__init__.py
# 목적: 텍스트 정규화 및 한국어 품질 검사 모듈을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Text normalization helpers that preserve raw OCR separately."""

from .layout import cluster_words_into_lines, merge_touching_fragments, render_lines
from .korean_quality import (
    is_ocr_noise_text,
    korean_quality_score,
    needs_secondary_check,
    ocr_candidate_score,
    ocr_result_quality,
    special_character_ratio,
)
from .normalization import normalize_ocr_text, normalize_structured_token

__all__ = [
    "cluster_words_into_lines",
    "is_ocr_noise_text",
    "korean_quality_score",
    "merge_touching_fragments",
    "needs_secondary_check",
    "ocr_candidate_score",
    "ocr_result_quality",
    "normalize_ocr_text",
    "normalize_structured_token",
    "render_lines",
    "special_character_ratio",
]
