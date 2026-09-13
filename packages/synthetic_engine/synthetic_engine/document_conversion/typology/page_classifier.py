# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: page_classifier.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/page_classifier.py
# 목적: 표지, 목차, 본문 등 페이지 아키타입 유형을 분류함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
페이지 아키타입 분류기 모듈.
문서 내 각 페이지의 기능적·구조적 아키타입(표지, 목차, 간지, 본문 등)을 분류함.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pymupdf

from synthetic_engine.document_conversion.typology.models import (
    DocumentDesignTokens,
    PageArchetype,
)


class PageClassifier:
    """
    페이지별 텍스트 밀도, 그래픽 수, 폰트 최대치, 개요/번호 시그니처를 기반으로
    하드코딩 없이 7대 페이지 아키타입을 분류하는 분류기임.
    """

    # PageClassifier 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, tokens: DocumentDesignTokens):
        self.tokens = tokens

        self._toc_keywords = (
            "contents", "table of contents", "목차", "목 차", "차례", "차 례",
            "표 목차", "표목차", "그림 목차", "그림목차", "색인", "index"
        )
        self._colophon_keywords = (
            "발행처", "발행인", "인쇄처", "발행일", "등록번호", "isbn", "저작권",
            "all rights reserved", "판권", "기획총괄"
        )
        self._front_matter_keywords = (
            "발간사", "서문", "요약문", "요 약", "제출문", "연구진", "참여연구원", "목 적", "개 요"
        )
        self._appendix_keywords = (
            "appendix", "부록", "별첨", "부 록", "별 첨"
        )

    # classify 페이지 작업을 수행함
    def classify_page(
        self,
        page: pymupdf.Page,
        page_idx: int,
        total_pages: int,
    ) -> PageArchetype:
        """단일 페이지의 특징을 추출하여 PageArchetype을 판정함."""
        text = page.get_text().strip()
        text_len = len(re.sub(r"\s+", "", text))
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        blocks = page.get_text("dict").get("blocks", [])
        text_blocks = [b for b in blocks if "lines" in b]

        max_font_size = 0.0
        for b in text_blocks:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    max_font_size = max(max_font_size, float(s.get("size", 0)))

        drawings = page.get_drawings()
        images = page.get_images()

        # 1. 표지 판별 (첫 1~2페이지, 대형 폰트 타이틀 또는 전면 커버)
        if page_idx == 0:
            if max_font_size >= self.tokens.font_size_body * 1.5 or len(images) > 0:
                return PageArchetype.COVER

        # 2. 뒷표지/판권지 판별 (문서 최후방 1~2페이지)
        if page_idx >= total_pages - 2:
            lower_text = text.lower()
            if any(kw in lower_text for kw in self._colophon_keywords) or (text_len < 120 and len(images) > 0):
                return PageArchetype.BACK_COVER

        # 3. 부록(Appendix) 판별 (문서 후반부 부록 표제어)
        if page_idx >= total_pages * 0.7:
            lower_text = text.lower()
            if any(kw in lower_text for kw in self._appendix_keywords):
                return PageArchetype.APPENDIX

        # 4. 목차군(TOC) 판별 (TOC 표제어 또는 다수의 개요/페이지 번호 교차 구조)
        has_toc_kw = any(kw in text.lower() for kw in self._toc_keywords)
        is_toc = self._is_table_of_contents_page(lines, has_toc_kw)
        if is_toc:
            return PageArchetype.TOC

        # 5. 간지(Chapter Divider) 판별 (텍스트 밀도가 매우 낮고 대형 폰트나 챕터 번호가 존재함)
        if text_len < 80:
            has_chapter_marker = bool(re.search(r"(제\s*\d+\s*[장부편]|Chapter\s*\d+|part\s*\d+)", text, re.IGNORECASE))
            if has_chapter_marker or max_font_size >= self.tokens.font_size_h1 or len(drawings) > 10 or len(images) > 0:
                return PageArchetype.CHAPTER_DIVIDER

        # 6. 속표지/제출문/요약문 판별 (문서 초반부 1~5페이지)
        if page_idx < 6:
            lower_text = text.lower()
            if any(kw in lower_text for kw in self._front_matter_keywords) or text_len < 150:
                return PageArchetype.FRONT_MATTER

        # 7. 기본값: 일반 본문 보고서 페이지
        return PageArchetype.BODY

    # 표(테이블) of contents 페이지 여부 및 유효성을 판별함
    def _is_table_of_contents_page(self, lines: List[str], has_toc_kw: bool) -> bool:
        """라인 목록을 분석하여 목차(TOC, 표목차, 그림목차) 페이지인지 판정함."""
        if not lines or len(lines) < 3:
            return False

        outline_re = re.compile(
            r"^\s*("
            r"\d+[\.\)]"
            r"|[I|V|X|i|v|x]+[\.\)]"
            r"|[가-힣][\.\)]"
            r"|<[^>]+>"
            r"|제\s*\d+\s*[장절편부관]"
            r")",
            re.IGNORECASE,
        )

        pure_pno = sum(1 for l in lines if re.match(r"^\s*\d{1,4}\s*$", l))
        end_pno = sum(1 for l in lines if re.search(r"(?:[.\s…]{2,}|\s+)\d{1,4}\s*$", l))
        outlines = sum(1 for l in lines if outline_re.match(l))
        total = len(lines)

        # 1. 목차 표제어가 있고 번호나 개요 항목이 있는 경우
        if has_toc_kw and (pure_pno >= 2 or end_pno >= 2 or outlines >= 2):
            return True

        # 2. 표제어가 없더라도 다수 행이 개요 항목과 페이지 번호의 교차/결합 구조인 경우
        if pure_pno >= 4 and outlines >= 4 and ((pure_pno + outlines) / total) >= 0.5:
            return True

        if (end_pno / total) >= 0.4 and (outlines / total) >= 0.3:
            return True

        return False
