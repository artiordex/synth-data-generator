# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/evaluation/__init__.py
# 목적: OCR 인식 품질 및 정확도 평가 모듈을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""OCR quality evaluation."""

from .metrics import evaluate_ocr_page, text_metrics

__all__ = ["evaluate_ocr_page", "text_metrics"]
