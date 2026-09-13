# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/__init__.py
# 목적: 문서 타이폴로지 및 레이아웃 양식 분류 모듈을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
문서 구조 및 레이아웃 유형화(Typology) 패키지.
하드코딩 없이 스타일 학습 및 시맨틱 아키타입 분류를 제공함.
"""
from synthetic_engine.document_conversion.typology.block_classifier import BlockClassifier
from synthetic_engine.document_conversion.typology.models import (
    ComponentType,
    DocumentDesignTokens,
    DocumentTypologyResult,
    PageArchetype,
    TypifiedBlock,
    TypifiedPage,
)
from synthetic_engine.document_conversion.typology.page_classifier import PageClassifier
from synthetic_engine.document_conversion.typology.style_learner import DocumentStyleLearner
from synthetic_engine.document_conversion.typology.typology_pipeline import DocumentTypologyPipeline

__all__ = [
    "BlockClassifier",
    "ComponentType",
    "DocumentDesignTokens",
    "DocumentStyleLearner",
    "DocumentTypologyPipeline",
    "DocumentTypologyResult",
    "PageArchetype",
    "PageClassifier",
    "TypifiedBlock",
    "TypifiedPage",
]
