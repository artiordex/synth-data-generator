# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: style_learner.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/style_learner.py
# 목적: 원본 문서의 스타일 토큰 및 폰트 계층을 학습 추출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
문서 스타일 및 디자인 토큰 자동 학습기 모듈.
PDF 문서 전반의 타이포그래피 위계, 컬러 팔레트, 여백 규격을 통계적으로 도출함.
"""
from __future__ import annotations

import colorsys
import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

from synthetic_engine.document_conversion.typology.models import DocumentDesignTokens


# grayscale 여부 및 유효성을 판별함
def _is_grayscale(hex_c: str) -> bool:
    """색상이 무채색(그레이스케일/흑백/쿨그레이)인지 판정함."""
    if not hex_c or not hex_c.startswith("#") or len(hex_c) != 7:
        return True
    try:
        r = int(hex_c[1:3], 16)
        g = int(hex_c[3:5], 16)
        b = int(hex_c[5:7], 16)
        return max(abs(r - g), abs(g - b), abs(r - b)) <= 25
    except ValueError:
        return True


# 색상 lightness 작업을 수행함
def _color_lightness(hex_c: str) -> float:
    """색상의 명도(0.0 ~ 1.0)를 반환함."""
    try:
        r = int(hex_c[1:3], 16) / 255.0
        g = int(hex_c[3:5], 16) / 255.0
        b = int(hex_c[5:7], 16) / 255.0
        return colorsys.rgb_to_hls(r, g, b)[1]
    except Exception:
        return 0.5


class DocumentStyleLearner:
    """
    문서의 텍스트 스팬 및 그래픽 요소를 통계 분석하여
    하드코딩 없이 고유 디자인 토큰을 도출하는 학습기임.
    """

    # DocumentStyleLearner 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, doc: pymupdf.Document):
        self.doc = doc

    # learn 작업을 수행함
    def learn(self, max_pages: int = 40) -> DocumentDesignTokens:
        """
        문서 전체 또는 대표 페이지를 스캔하여 디자인 토큰을 학습 및 도출함.
        """
        sample_pages = list(range(min(len(self.doc), max_pages)))

        font_size_counts: Counter[float] = Counter()
        font_family_counts: Counter[str] = Counter()
        color_counts: Counter[str] = Counter()
        non_gray_colors: Counter[str] = Counter()

        page_widths: List[float] = []
        page_heights: List[float] = []

        for p_idx in sample_pages:
            page = self.doc[p_idx]
            page_widths.append(float(page.rect.width))
            page_heights.append(float(page.rect.height))

            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        char_len = len(text)
                        if char_len == 0:
                            continue

                        raw_size = round(float(span.get("size", 10.0)), 1)
                        font_name = str(span.get("font", "")).split("+")[-1]
                        color_int = span.get("color", 0)
                        hex_color = f"#{color_int:06x}" if isinstance(color_int, int) else "#000000"

                        font_size_counts[raw_size] += char_len
                        font_family_counts[font_name] += char_len
                        color_counts[hex_color] += char_len

                        if not _is_grayscale(hex_color):
                            l = _color_lightness(hex_color)
                            if 0.15 <= l <= 0.85:
                                non_gray_colors[hex_color] += char_len

        # 기본 페이지 규격 도출함
        p_w = page_widths[0] if page_widths else 595.3
        p_h = page_heights[0] if page_heights else 841.9

        # 본문 기본 폰트 크기 도출함 (최다 빈도 폰트 크기)
        base_size = 9.5
        if font_size_counts:
            # 7pt ~ 13pt 사이에서 최다 빈도 폰트를 본문 기본 크기로 지정함
            body_candidates = [sz for sz, cnt in font_size_counts.most_common() if 7.5 <= sz <= 13.0]
            if body_candidates:
                base_size = body_candidates[0]
            else:
                base_size = font_size_counts.most_common(1)[0][0]

        # 기본 폰트 패밀리 도출함
        base_family = "Noto Sans KR"
        if font_family_counts:
            dominant_font = font_family_counts.most_common(1)[0][0]
            # 글꼴 이름 정리함 (KoPubDotum, Malgun, Arial 등 감지)
            if any(k in dominant_font.lower() for k in ("kopub", "gothic", "dotum", "nanum", "noto", "malgun")):
                base_family = dominant_font
            else:
                base_family = dominant_font

        # 브랜드 대표 컬러 및 다크 텍스트 컬러 도출함
        primary_c = "#2563eb"
        if non_gray_colors:
            primary_c = non_gray_colors.most_common(1)[0][0]

        dark_c = "#222222"
        if color_counts:
            for col, _ in color_counts.most_common(5):
                if _is_grayscale(col) and _color_lightness(col) < 0.35:
                    dark_c = col
                    break

        # 제목 위계 스케일 도출함
        larger_sizes = sorted([sz for sz in font_size_counts.keys() if sz > base_size], reverse=True)
        smaller_sizes = sorted([sz for sz in font_size_counts.keys() if sz < base_size])

        h1_size = base_size * 1.45
        h2_size = base_size * 1.20
        h3_size = base_size * 1.08
        caption_size = base_size * 0.88

        if len(larger_sizes) >= 3:
            h1_size = larger_sizes[0]
            h2_size = larger_sizes[1]
            h3_size = larger_sizes[2]
        elif len(larger_sizes) == 2:
            h1_size = larger_sizes[0]
            h2_size = larger_sizes[1]
            h3_size = base_size * 1.08
        elif len(larger_sizes) == 1:
            h1_size = larger_sizes[0]
            h2_size = base_size * 1.20

        if smaller_sizes:
            caption_size = smaller_sizes[-1]

        # 런닝 헤더/푸터 마진 경계 도출함 (페이지 상단 8~10%, 하단 7~9%)
        header_top = min(75.0, p_h * 0.09)
        footer_bottom = max(p_h - 65.0, p_h * 0.92)

        return DocumentDesignTokens(
            primary_color=primary_c,
            dark_color=dark_c,
            muted_color="#64748b",
            surface_bg="#f8fafc",
            border_color="#cbd5e1",
            base_font_family=base_family,
            font_size_body=base_size,
            font_size_h1=h1_size,
            font_size_h2=h2_size,
            font_size_h3=h3_size,
            font_size_caption=caption_size,
            header_top_threshold=header_top,
            footer_bottom_threshold=footer_bottom,
            page_width=p_w,
            page_height=p_h,
        )
