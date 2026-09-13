# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: models.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/typology/models.py
# 목적: 타이폴로지 아키타입 및 디자인 토큰 데이터 모델을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""
문서 구조 및 레이아웃 유형화(Typology) 모델 정의 모듈.
페이지 아키타입, 시맨틱 컴포넌트 분류 및 문서 디자인 토큰 구조를 제공함.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PageArchetype(str, Enum):
    """문서 내 페이지의 구조적·기능적 아키타입 유형임."""
    COVER = "cover"                      # 표지
    FRONT_MATTER = "front_matter"        # 속표지, 발간사, 요약문, 제출문
    TOC = "toc"                          # 목차군 (목차, 표목차, 그림목차)
    CHAPTER_DIVIDER = "chapter_divider"  # 챕터 간지 (전면 배경/대형 챕터 표제)
    BODY = "body"                        # 일반 본문 보고서 페이지
    APPENDIX = "appendix"                # 부록 및 별첨 데이터
    BACK_COVER = "back_cover"            # 판권지 및 뒷표지


class ComponentType(str, Enum):
    """문서 내 개별 시맨틱 블록/컴포넌트 유형임."""
    RUNNING_HEADER = "running_header"    # 상단 런닝 헤더 (문서명, 챕터명)
    RUNNING_FOOTER = "running_footer"    # 하단 런닝 푸터 (페이지 번호)
    HEADING_L1 = "heading_l1"            # 대제목 (제1장, 01 대주제)
    HEADING_L2 = "heading_l2"            # 중제목 (1. 추진 배경 등)
    HEADING_L3 = "heading_l3"            # 소제목 (가. 세부 내용, 1) 등)
    PARAGRAPH = "paragraph"              # 일반 본문 문단
    LIST_NUMBERED = "list_numbered"      # 번호 매기기 목록
    LIST_BULLET = "list_bullet"          # 글머리 기호 목록 (•, -, ※)
    CALLOUT_BOX = "callout_box"          # 안내/요약/강조 박스 카드
    TABLE_BORDERED = "table_bordered"    # 전면 테두리 격자 표
    TABLE_SEMI_BORDERED = "table_semi"   # 상하단/헤더선 열린 표
    TABLE_COMPLEX = "table_complex"      # 다중 헤더/병합 셀 복합 표
    TABLE_KEY_VALUE = "table_kv"         # 메타데이터 라벨-값 그리드
    TABLE_CAPTION = "table_caption"      # < 표 N > 캡션
    TABLE_NOTE = "table_note"            # 표 하단 주석/출처 (* 주:, 자료:)
    FIGURE = "figure"                    # 도표, 차트, 인포그래픽 이미지
    FIGURE_CAPTION = "figure_caption"    # < 그림 N > 캡션
    FIGURE_NOTE = "figure_note"          # 그림 하단 주석/출처


@dataclass
class DocumentDesignTokens:
    """PDF 문서에서 통계적으로 학습·도출된 디자인 시스템 토큰임."""
    primary_color: str = "#2563eb"       # 대표 브랜드 컬러 (비그레이스케일 주 색상)
    dark_color: str = "#222222"          # 본문 텍스트 기본 색상
    muted_color: str = "#666666"         # 보조/캡션 텍스트 색상
    surface_bg: str = "#f8fafc"          # 카드/콜아웃 기본 배경색
    border_color: str = "#cbd5e1"        # 기본 구분선/테두리 색상
    base_font_family: str = "Noto Sans KR"  # 문서 최다 빈도 폰트 패밀리
    font_size_body: float = 9.5          # 본문 기준 폰트 크기 (pt)
    font_size_h1: float = 14.0           # 대제목 판별 임계치 (pt)
    font_size_h2: float = 11.5           # 중제목 판별 임계치 (pt)
    font_size_h3: float = 10.2           # 소제목 판별 임계치 (pt)
    font_size_caption: float = 8.2       # 캡션/주석 판별 임계치 (pt)
    header_top_threshold: float = 75.0   # 상단 런닝 헤더 경계 (pt)
    footer_bottom_threshold: float = 60.0  # 하단 런닝 푸터 경계 (높이 - pt)
    page_width: float = 595.3            # 기본 페이지 폭 (pt)
    page_height: float = 841.9           # 기본 페이지 높이 (pt)


@dataclass
class TypifiedBlock:
    """유형화 체계가 부여된 시맨틱 콘텐츠 블록임."""
    component_type: ComponentType
    bbox: Tuple[float, float, float, float]
    text: str = ""
    font_size: float = 9.5
    bold: bool = False
    color: str = "#000000"
    spans: List[Dict[str, Any]] = field(default_factory=list)
    raw_element: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TypifiedPage:
    """유형화 체계가 적용된 개별 페이지 모델임."""
    page_num: int                        # 1-based 페이지 번호
    archetype: PageArchetype             # 페이지 아키타입 유형
    blocks: List[TypifiedBlock] = field(default_factory=list)
    running_header: Optional[str] = None # 상단 런닝 헤더 텍스트
    running_footer: Optional[str] = None # 하단 런닝 푸터/페이지 번호
    raw_page_meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentTypologyResult:
    """문서 전체의 스타일 토큰 및 페이지별 유형화 분석 종합 결과임."""
    tokens: DocumentDesignTokens
    pages: List[TypifiedPage] = field(default_factory=list)
    total_pages: int = 0
    document_title: str = ""
    report_metadata: Dict[str, Any] = field(default_factory=dict)
