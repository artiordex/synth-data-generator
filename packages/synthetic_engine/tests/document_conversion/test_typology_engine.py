# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_typology_engine.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_typology_engine.py
# 목적: 문서 레이아웃 유형화(Typology) 엔진 및 컴포넌트 분류 기능을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-12
# 수정일: 2026-09-12
# =============================================================================
from __future__ import annotations

import tempfile
from pathlib import Path

import pymupdf
import pytest

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
from synthetic_engine.document_conversion.typology.style_learner import (
    DocumentStyleLearner,
    _color_lightness,
    _is_grayscale,
)
from synthetic_engine.document_conversion.typology.typology_pipeline import DocumentTypologyPipeline
from synthetic_engine.exporters.pdf_high_fidelity_converter import HighFidelityPdfDoc


# 그레이스케일 및 명도 유틸리티 함수를 검증함
def test_color_utilities():
    # 무채색 판정 검증함
    assert _is_grayscale("#ffffff") is True
    assert _is_grayscale("#000000") is True
    assert _is_grayscale("#333333") is True
    assert _is_grayscale("#cbd5e1") is True

    # 유채색(브랜드 컬러 등) 판정 검증함
    assert _is_grayscale("#2563eb") is False
    assert _is_grayscale("#e11d48") is False
    assert _is_grayscale("#41515f") is False

    # 명도 계산 범위 검증함
    assert _color_lightness("#ffffff") > 0.95
    assert _color_lightness("#000000") < 0.05
    assert 0.3 < _color_lightness("#41515f") < 0.7


# 가상 합성 PDF 문서를 생성하여 디자인 토큰 학습을 검증함
def test_document_style_learner_synthetic():
    doc = pymupdf.open()

    # 1. 표지 페이지 생성함 (대형 제목 28pt, 브랜드 색상 #41515f)
    p1 = doc.new_page(width=595.3, height=841.9)
    p1.insert_text(pymupdf.Point(100, 300), "2025년도 연구개발사업 심층 분석 보고서", fontsize=28, color=(0.25, 0.32, 0.37))
    p1.insert_text(pymupdf.Point(100, 350), "부산산업과학혁신원", fontsize=14, color=(0.25, 0.32, 0.37))

    # 2. 본문 페이지 1 생성함 (본문 9.5pt 다수, 중제목 16pt, 런닝 헤더 8pt, 푸터 9pt)
    p2 = doc.new_page(width=595.3, height=841.9)
    p2.insert_text(pymupdf.Point(50, 45), "제1장 분석개요 | 연구자 특성", fontsize=8, color=(0.4, 0.4, 0.4))
    p2.insert_text(pymupdf.Point(50, 100), "1. 분석 배경 및 목적", fontsize=16, color=(0.25, 0.32, 0.37))
    for i in range(12):
        p2.insert_text(pymupdf.Point(50, 140 + i * 22), f"본 연구는 지역 과학기술 인력의 통계적 특성을 다각도로 분석함 (문단 {i+1}).", fontsize=9.5, color=(0.1, 0.1, 0.1))
    p2.insert_text(pymupdf.Point(280, 800), "- 1 -", fontsize=9, color=(0.4, 0.4, 0.4))

    # 3. 본문 페이지 2 생성함
    p3 = doc.new_page(width=595.3, height=841.9)
    p3.insert_text(pymupdf.Point(50, 45), "제1장 분석개요 | 연구자 특성", fontsize=8, color=(0.4, 0.4, 0.4))
    for i in range(15):
        p3.insert_text(pymupdf.Point(50, 100 + i * 22), f"지역 R&D 혁신 생태계 구축을 위한 조사 분석 결과를 수록함 (문단 {i+1}).", fontsize=9.5, color=(0.1, 0.1, 0.1))
    p3.insert_text(pymupdf.Point(280, 800), "- 2 -", fontsize=9, color=(0.4, 0.4, 0.4))

    learner = DocumentStyleLearner(doc)
    tokens = learner.learn()

    # 도출된 토큰 규격 검증함
    assert tokens.font_size_body == pytest.approx(9.5, abs=0.5)
    assert tokens.font_size_h1 > tokens.font_size_body
    assert tokens.header_top_threshold > 30.0
    assert tokens.footer_bottom_threshold < 820.0
    assert tokens.primary_color.startswith("#")
    doc.close()


# 페이지 아키타입 분류기의 판별 로직을 검증함
def test_page_classifier_archetypes():
    tokens = DocumentDesignTokens(
        font_size_body=9.5,
        font_size_h1=24.0,
        font_size_h2=16.0,
        font_size_caption=8.0,
        header_top_threshold=70.0,
        footer_bottom_threshold=780.0,
        page_height=841.9,
    )
    classifier = PageClassifier(tokens)

    doc = pymupdf.open()

    # 표지 페이지 (p_idx=0, 단어 적고 큰 폰트)
    p_cover = doc.new_page(width=595.3, height=841.9)
    p_cover.insert_text(pymupdf.Point(100, 300), "Annual Report 2025", fontsize=28)
    archetype_cover = classifier.classify_page(p_cover, 0, 10)
    assert archetype_cover == PageArchetype.COVER

    # 목차 페이지 (TOC 키워드 및 점선/페이지 번호 패턴)
    p_toc = doc.new_page(width=595.3, height=841.9)
    p_toc.insert_text(pymupdf.Point(250, 80), "TABLE OF CONTENTS", fontsize=18)
    p_toc.insert_text(pymupdf.Point(80, 150), "1. Introduction ..................................... 1", fontsize=10)
    p_toc.insert_text(pymupdf.Point(80, 180), "2. Main Research ..................................... 15", fontsize=10)
    archetype_toc = classifier.classify_page(p_toc, 2, 10)
    assert archetype_toc == PageArchetype.TOC

    # 일반 본문 페이지 (많은 문단)
    p_body = doc.new_page(width=595.3, height=841.9)
    for i in range(25):
        p_body.insert_text(pymupdf.Point(50, 80 + i * 25), f"General report body text paragraph content line {i+1} for testing.", fontsize=9.5)
    archetype_body = classifier.classify_page(p_body, 4, 10)
    assert archetype_body == PageArchetype.BODY

    # 부록 페이지 (후반부 80% 이후)
    p_app = doc.new_page(width=595.3, height=841.9)
    p_app.insert_text(pymupdf.Point(80, 80), "APPENDIX: Regional Researcher Survey Statistics", fontsize=14)
    for i in range(10):
        p_app.insert_text(pymupdf.Point(80, 120 + i * 25), f"Item {i+1}: 123.45 count", fontsize=9)
    archetype_app = classifier.classify_page(p_app, 8, 10)
    assert archetype_app == PageArchetype.APPENDIX

    doc.close()


# 시맨틱 블록 분류기의 컴포넌트 식별 로직을 검증함
def test_block_classifier_components():
    tokens = DocumentDesignTokens(
        font_size_body=9.5,
        font_size_h1=22.0,
        font_size_h2=15.0,
        font_size_h3=11.0,
        font_size_caption=8.2,
        header_top_threshold=70.0,
        footer_bottom_threshold=780.0,
        page_height=841.9,
    )
    classifier = BlockClassifier(tokens)
    p_h = 841.9

    # 1. 런닝 헤더 검증함 (y0 < header_top_threshold)
    header_block = {
        "type": "paragraph",
        "bbox": (50.0, 35.0, 300.0, 50.0),
        "text": "2025년도 부산 연구개발사업 심층 조사·분석",
        "blocks": [{"lines": [{"spans": [{"text": "2025년도 부산 연구개발사업 심층 조사·분석", "size": 8.0, "bold": False}]}]}],
    }
    tb_header = classifier.classify_block(header_block, PageArchetype.BODY, 2, p_h)
    assert tb_header.component_type == ComponentType.RUNNING_HEADER

    # 2. 런닝 푸터 검증함 (y0 > footer_bottom_threshold)
    footer_block = {
        "type": "footer",
        "bbox": (280.0, 805.0, 315.0, 820.0),
        "text": "- 12 -",
        "blocks": [{"lines": [{"spans": [{"text": "- 12 -", "size": 8.5, "bold": False}]}]}],
    }
    tb_footer = classifier.classify_block(footer_block, PageArchetype.BODY, 12, p_h)
    assert tb_footer.component_type == ComponentType.RUNNING_FOOTER

    # 3. 표 캡션 검증함 (< 표 1-1 > 패턴)
    tbl_cap_block = {
        "type": "paragraph",
        "bbox": (50.0, 150.0, 300.0, 168.0),
        "text": "< 표 1-1 > 연구개발사업 수행 현황",
        "blocks": [{"lines": [{"spans": [{"text": "< 표 1-1 > 연구개발사업 수행 현황", "size": 8.5, "bold": True}]}]}],
    }
    tb_tbl_cap = classifier.classify_block(tbl_cap_block, PageArchetype.BODY, 2, p_h)
    assert tb_tbl_cap.component_type == ComponentType.TABLE_CAPTION

    # 4. 그림 캡션 검증함 (< 그림 2-3 > 패턴)
    fig_cap_block = {
        "type": "paragraph",
        "bbox": (150.0, 350.0, 400.0, 368.0),
        "text": "< 그림 2-3 > 연도별 연구개발비 추이",
        "blocks": [{"lines": [{"spans": [{"text": "< 그림 2-3 > 연도별 연구개발비 추이", "size": 8.5, "bold": True}]}]}],
    }
    tb_fig_cap = classifier.classify_block(fig_cap_block, PageArchetype.BODY, 2, p_h)
    assert tb_fig_cap.component_type == ComponentType.FIGURE_CAPTION

    # 5. 주석/출처 블록 검증함 (* 주: ..., 자료: ...)
    note_block = {
        "type": "paragraph",
        "bbox": (50.0, 400.0, 400.0, 415.0),
        "text": "* 주: 1) 통계청 2024년 기준 자료를 바탕으로 재가공함.",
        "blocks": [{"lines": [{"spans": [{"text": "* 주: 1) 통계청 2024년 기준 자료를 바탕으로 재가공함.", "size": 8.0, "bold": False}]}]}],
    }
    tb_note = classifier.classify_block(note_block, PageArchetype.BODY, 2, p_h)
    assert tb_note.component_type == ComponentType.TABLE_NOTE

    # 6. 대제목(Heading L1) 검증함
    h1_block = {
        "type": "paragraph",
        "bbox": (50.0, 100.0, 450.0, 135.0),
        "text": "제1장 조사 및 분석 개요",
        "blocks": [{"lines": [{"spans": [{"text": "제1장 조사 및 분석 개요", "size": 22.0, "bold": True}]}]}],
    }
    tb_h1 = classifier.classify_block(h1_block, PageArchetype.BODY, 2, p_h)
    assert tb_h1.component_type == ComponentType.HEADING_L1

    # 7. 중제목(Heading L2) 검증함
    h2_block = {
        "type": "paragraph",
        "bbox": (50.0, 140.0, 400.0, 165.0),
        "text": "1. 분석 배경 및 필요성",
        "blocks": [{"lines": [{"spans": [{"text": "1. 분석 배경 및 필요성", "size": 15.0, "bold": True}]}]}],
    }
    tb_h2 = classifier.classify_block(h2_block, PageArchetype.BODY, 2, p_h)
    assert tb_h2.component_type == ComponentType.HEADING_L2

    # 8. 불릿 목록 검증함 (- 항목 또는 • 기호)
    bullet_block = {
        "type": "paragraph",
        "bbox": (50.0, 200.0, 400.0, 218.0),
        "text": "- 주요 산학연관 협력 연구비 비중 확대",
        "blocks": [{"lines": [{"spans": [{"text": "- 주요 산학연관 협력 연구비 비중 확대", "size": 9.5, "bold": False}]}]}],
    }
    tb_bullet = classifier.classify_block(bullet_block, PageArchetype.BODY, 2, p_h)
    assert tb_bullet.component_type == ComponentType.LIST_BULLET


# 실제 108페이지 타깃 PDF가 존재하는 경우 전체 파이프라인 정밀도를 검증함
def test_target_pdf_typology_fidelity():
    target_pdf = Path("storage/uploads/c9463d3638de4a2d9c355985c425056d_2025년도 부산 연구개발사업 심층 조사·분석 지역 연구자 특성 분석 보고서_final.pdf")
    if not target_pdf.exists():
        pytest.skip("타깃 샘플 PDF 파일이 로컬 스토리지에 존재하지 않으므로 건너뜀")

    converter = HighFidelityPdfDoc(target_pdf)
    try:
        # 1. 유형화 결과 유효성 검증함
        assert hasattr(converter, "typology_result")
        res: DocumentTypologyResult = converter.typology_result
        assert res.total_pages == 108

        # 2. 통계적으로 학습된 디자인 토큰 검증함
        tokens = converter.tokens
        assert tokens.font_size_body == pytest.approx(9.0, abs=1.0)
        assert tokens.primary_color == "#41515f"
        assert "KoPub" in tokens.base_font_family

        # 3. 페이지 아키타입 분포 검증함
        archetypes = [p.archetype for p in res.pages]
        assert PageArchetype.COVER in archetypes
        assert PageArchetype.TOC in archetypes
        assert PageArchetype.BODY in archetypes
        assert PageArchetype.APPENDIX in archetypes

        # 표지(P1) 검증함
        assert res.pages[0].archetype == PageArchetype.COVER

        # 본문 페이지(P12~P15) 런닝 헤더/푸터 분리 검증함
        p12 = res.pages[11]
        assert p12.archetype == PageArchetype.BODY
        assert p12.running_header is not None
        assert "2025년도 부산 연구개발사업" in p12.running_header
        assert p12.running_footer == "2"

        # 4. 고충실도 HTML 출력 검증함
        html_out = converter.to_html()
        assert "var(--primary-navy)" in html_out or "#41515f" in html_out
        assert "pdf-running-header" in html_out
        assert "pdf-running-footer" in html_out
        assert "pdf-page-cover" in html_out

        # 5. 마크다운 출력 검증함
        md_out = converter.to_markdown()
        assert "## Page 1" in md_out
        assert "2025년도 부산 연구개발사업" in md_out
        assert "*2*" in md_out  # 푸터 페이지 번호

        # 6. 워드(DOCX) 및 HWPX 생성 무결성 검증함
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_docx = Path(tmp_dir) / "test_output.docx"
            converter.to_docx(tmp_docx)
            assert tmp_docx.exists()
            assert tmp_docx.stat().st_size > 1000

            tmp_hwpx = Path(tmp_dir) / "test_output.hwpx"
            converter.to_hwpx(tmp_hwpx)
            assert tmp_hwpx.exists()
            assert tmp_hwpx.stat().st_size > 1000
    finally:
        converter.close()
