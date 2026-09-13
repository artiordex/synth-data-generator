# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: block_classifier.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/block_classifier.py
# 목적: 페이지 내 각 요소의 시맨틱 블록 유형 및 역할을 분류함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
시맨틱 블록 및 컴포넌트 분류기 모듈.
페이지 내 각 요소(텍스트, 표, 박스, 이미지)의 시맨틱 유형을 판별함.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from synthetic_engine.document_conversion.typology.models import (
    ComponentType,
    DocumentDesignTokens,
    PageArchetype,
    TypifiedBlock,
)


class BlockClassifier:
    """
    위치 좌표, 폰트 크기, 굵기, 정규식 패턴 및 디자인 토큰을 활용하여
    개별 블록의 시맨틱 역할을 18개 유형으로 분류하는 분류기임.
    """

    # BlockClassifier 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, tokens: DocumentDesignTokens):
        self.tokens = tokens

        self._table_caption_re = re.compile(r"^\s*<\s*(?:표|Table)\s*\d+[^>]*>", re.IGNORECASE)
        self._figure_caption_re = re.compile(r"^\s*<\s*(?:그림|Figure|도|차트)\s*\d+[^>]*>", re.IGNORECASE)
        self._note_re = re.compile(r"^\s*(?:\*?\s*주\s*[:\)]|자료\s*[:\)]|출처\s*[:\)]|Source\s*[:\)]|\*\s*참고\s*[:\)])", re.IGNORECASE)

        self._heading_l1_re = re.compile(r"^\s*([I|V|X]+\.|\d{2}\s+[가-힣A-Za-z]|제\s*\d+\s*[장부편])")
        self._heading_l2_re = re.compile(r"^\s*\d+\.\s+[가-힣A-Za-z0-9]")
        self._heading_l3_re = re.compile(r"^\s*(\d+\)|[가-힣]\.|\([0-9]+\))\s+[가-힣A-Za-z0-9]")

        self._bullet_re = re.compile(r"^\s*[•\-\*※]\s*")
        self._numbered_re = re.compile(r"^\s*(\d+[\.\)]|[가-힣][\.\)]|\([0-9]+\))\s*")

    # classify 문서 블록 작업을 수행함
    def classify_block(
        self,
        element: Dict[str, Any],
        page_archetype: PageArchetype,
        page_num: int,
        page_height: float,
    ) -> TypifiedBlock:
        """단일 요소 딕셔너리를 TypifiedBlock으로 변환하고 컴포넌트 유형을 판정함."""
        etype = element.get("type", "paragraph")
        bbox = element.get("bbox") or element.get("rect") or (0, 0, 0, 0)
        y0, y1 = float(bbox[1]), float(bbox[3])

        # 텍스트 추출 및 대표 폰트/색상 분석함
        text = ""
        font_size = self.tokens.font_size_body
        bold = False
        color = self.tokens.dark_color
        spans = []

        if "blocks" in element:
            text_lines = []
            for b in element["blocks"]:
                for l in b.get("lines", []):
                    line_spans = l.get("spans", []) if isinstance(l, dict) else l
                    for s in line_spans:
                        if isinstance(s, dict):
                            spans.append(s)
                            if s.get("text"):
                                text_lines.append(s["text"])
            text = "".join(text_lines).strip()
        elif "text" in element:
            text = str(element["text"]).strip()
        elif "rows" in element:
            row_texts = []
            for r in element["rows"]:
                cells = r.get("cells", []) if isinstance(r, dict) else r
                row_texts.append(" ".join(c.get("text", "") for c in cells if isinstance(c, dict)))
            text = "\n".join(row_texts).strip()

        if spans:
            dominant_span = max(spans, key=lambda s: len(s.get("text", "")), default={})
            font_size = float(dominant_span.get("size", font_size))
            bold = bool(dominant_span.get("bold", False))
            color = str(dominant_span.get("color", color))

        # 1. 런닝 헤더 판별 (본문 페이지 상단 여백 내 짧은 텍스트)
        if page_archetype in (PageArchetype.BODY, PageArchetype.APPENDIX) and y1 <= self.tokens.header_top_threshold:
            if text and len(text) < 80:
                return TypifiedBlock(
                    component_type=ComponentType.RUNNING_HEADER,
                    bbox=bbox,
                    text=text,
                    font_size=font_size,
                    bold=bold,
                    color=color,
                    raw_element=element,
                )

        # 2. 런닝 푸터 판별 (페이지 하단 여백 내 페이지 번호 등)
        if y0 >= self.tokens.footer_bottom_threshold:
            if text and (re.match(r"^\s*-\s*\d+\s*-\s*$", text) or re.match(r"^\s*\d{1,4}\s*$", text) or len(text) < 30):
                return TypifiedBlock(
                    component_type=ComponentType.RUNNING_FOOTER,
                    bbox=bbox,
                    text=text,
                    font_size=font_size,
                    bold=bold,
                    color=color,
                    raw_element=element,
                )

        # 3. 캡션 및 주석 판별
        if self._table_caption_re.search(text):
            return TypifiedBlock(ComponentType.TABLE_CAPTION, bbox, text, font_size, bold, color, spans, element)
        if self._figure_caption_re.search(text):
            return TypifiedBlock(ComponentType.FIGURE_CAPTION, bbox, text, font_size, bold, color, spans, element)
        if self._note_re.search(text):
            return TypifiedBlock(ComponentType.TABLE_NOTE, bbox, text, font_size, bold, color, spans, element)

        # 4. 표 요소 판별 및 서브 유형화
        if etype == "table":
            sub_type = self._classify_table(element)
            return TypifiedBlock(sub_type, bbox, text, font_size, bold, color, spans, element)

        # 5. 이미지/차트 요소 판별
        if etype == "image":
            return TypifiedBlock(ComponentType.FIGURE, bbox, text, font_size, bold, color, spans, element)

        # 6. 콜아웃/안내 박스 판별
        if etype in ("alert", "banner", "card", "box"):
            return TypifiedBlock(ComponentType.CALLOUT_BOX, bbox, text, font_size, bold, color, spans, element)

        # 7. 제목 위계 판별
        if font_size >= self.tokens.font_size_h1 or self._heading_l1_re.match(text):
            return TypifiedBlock(ComponentType.HEADING_L1, bbox, text, font_size, True, color, spans, element)
        if (font_size >= self.tokens.font_size_h2 and bold) or (self._heading_l2_re.match(text) and (bold or font_size >= self.tokens.font_size_body)):
            return TypifiedBlock(ComponentType.HEADING_L2, bbox, text, font_size, True, color, spans, element)
        if (font_size >= self.tokens.font_size_h3 and bold) or self._heading_l3_re.match(text):
            return TypifiedBlock(ComponentType.HEADING_L3, bbox, text, font_size, bold, color, spans, element)

        # 8. 목록 요소 판별 (글머리 기호 및 번호 목록)
        if self._bullet_re.match(text):
            return TypifiedBlock(ComponentType.LIST_BULLET, bbox, text, font_size, bold, color, spans, element)
        if self._numbered_re.match(text) and len(text) < 200:
            return TypifiedBlock(ComponentType.LIST_NUMBERED, bbox, text, font_size, bold, color, spans, element)

        # 9. 기본 본문 문단
        return TypifiedBlock(ComponentType.PARAGRAPH, bbox, text, font_size, bold, color, spans, element)

    # classify 표(테이블) 작업을 수행함
    def _classify_table(self, table_elem: Dict[str, Any]) -> ComponentType:
        """표 요소의 테두리 전략 및 행/열 구조를 바탕으로 표 서브유형을 판정함."""
        strategy = table_elem.get("strategy", {})
        v_strat = strategy.get("vertical_strategy")
        h_strat = strategy.get("horizontal_strategy")
        rows = table_elem.get("rows", [])

        if not rows or len(rows) < 2:
            return ComponentType.PARAGRAPH

        col_counts = [len(r.get("cells", [])) for r in rows if "cells" in r]
        max_cols = max(col_counts, default=0)
        if max_cols < 2:
            return ComponentType.PARAGRAPH

        # 2열 또는 4열의 키-값 그리드 구조 판정함
        if max_cols in (2, 4) and len(rows) <= 6:
            return ComponentType.TABLE_KEY_VALUE

        # 열린 표 (수평선만 존재하고 수직선은 텍스트 기반)
        if v_strat == "text" and h_strat == "lines":
            return ComponentType.TABLE_SEMI_BORDERED

        # 셀 병합 또는 불규칙 열 수를 가진 복합 표
        if len(set(col_counts)) > 1:
            return ComponentType.TABLE_COMPLEX

        return ComponentType.TABLE_BORDERED
