# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: typology_pipeline.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/typology_pipeline.py
# 목적: 문서 레이아웃 타이폴로지 분석 파이프라인 처리를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
문서 레이아웃 유형화(Typology) 통합 파이프라인 모듈.
PDF 문서를 스타일 학습 -> 페이지 아키타입 분류 -> 블록 컴포넌트 시맨틱 분류로 전개함.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf

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


class DocumentTypologyPipeline:
    """
    하드코딩 없이 문서를 자동 학습하고 유형화하여
    95%+ 고충실도 시맨틱 모델을 생성하는 종합 파이프라인임.
    """

    # DocumentTypologyPipeline 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, doc: pymupdf.Document, pdf_path: Optional[Path] = None):
        """
            @description DocumentTypologyPipeline 인스턴스 멤버 변수 및 초기 설정을 구성함
            @param {doc} - 메서드 입력값임
            @param {pdf_path} - 메서드 입력값임
        """
        self.doc = doc
        self.pdf_path = pdf_path
        self.learner = DocumentStyleLearner(doc)

    # run 작업을 수행함
    def run(self, raw_pages_elements: Optional[List[Dict[str, Any]]] = None) -> DocumentTypologyResult:
        """
        전체 문서를 분석하여 DocumentTypologyResult를 생성함.
        raw_pages_elements가 제공되면 해당 요소들을 유형화하며, 없으면 기본 텍스트/도면 블록을 추출함.
        """
        tokens = self.learner.learn()
        page_classifier = PageClassifier(tokens)
        block_classifier = BlockClassifier(tokens)

        total_pages = len(self.doc)
        typified_pages: List[TypifiedPage] = []

        for p_idx in range(total_pages):
            page = self.doc[p_idx]
            archetype = page_classifier.classify_page(page, p_idx, total_pages)

            p_h = float(page.rect.height)
            page_elements = []

            # 사전에 추출된 고충실도 요소가 있으면 활용함
            if raw_pages_elements and p_idx < len(raw_pages_elements):
                page_elements = raw_pages_elements[p_idx].get("elements", [])
            else:
                # 기본 블록 추출함
                text_blocks = page.get_text("dict").get("blocks", [])
                for b in text_blocks:
                    if "lines" in b:
                        page_elements.append({
                            "type": "paragraph",
                            "bbox": tuple(b.get("bbox", (0, 0, 0, 0))),
                            "blocks": [b],
                            "text": "\n".join("".join(s.get("text", "") for s in l.get("spans", [])) for l in b.get("lines", [])).strip(),
                        })

            typified_blocks: List[TypifiedBlock] = []
            running_header: Optional[str] = None
            running_footer: Optional[str] = None

            for elem in page_elements:
                t_block = block_classifier.classify_block(elem, archetype, p_idx + 1, p_h)
                if t_block.component_type == ComponentType.RUNNING_HEADER:
                    running_header = t_block.text
                elif t_block.component_type == ComponentType.RUNNING_FOOTER:
                    running_footer = t_block.text
                typified_blocks.append(t_block)

            typified_pages.append(TypifiedPage(
                page_num=p_idx + 1,
                archetype=archetype,
                blocks=typified_blocks,
                running_header=running_header,
                running_footer=running_footer,
            ))

        doc_title = self.pdf_path.stem if self.pdf_path else "Document"
        return DocumentTypologyResult(
            tokens=tokens,
            pages=typified_pages,
            total_pages=total_pages,
            document_title=doc_title,
        )
