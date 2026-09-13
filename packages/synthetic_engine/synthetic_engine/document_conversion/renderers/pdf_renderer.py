# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: pdf_renderer.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/pdf_renderer.py
# 목적: IR 트리를 PDF 문서로 인쇄 렌더링함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Paginate IR-derived HTML using PyMuPDF's offline Story layout engine."""
from pathlib import Path
import tempfile
from ..core.capabilities import TargetCapabilities
from .html_renderer import HtmlRenderer


class PdfRenderer:
    capabilities = TargetCapabilities(supports_pages=True)

    # render 작업을 수행함
    def render(self, document, output_path):
        import pymupdf as fitz
        with tempfile.TemporaryDirectory(dir=Path(output_path).parent) as directory:
            html_path = Path(directory) / 'document.html'
            HtmlRenderer().render(document, html_path)
            story = fitz.Story(html=html_path.read_text(encoding='utf-8'))
            section = document.sections[0] if document.sections else None
            width = (section.page_width_pt if section else None) or 595.28
            height = (section.page_height_pt if section else None) or 841.89
            page_box = fitz.Rect(0, 0, width, height)
            content_box = fitz.Rect(36, 36, width-36, height-36)
            if content_box.is_empty:
                raise ValueError('PDF page is too small for the configured content area')
            writer = fitz.DocumentWriter(str(output_path))
            try:
                for _ in range(1000):
                    device = writer.begin_page(page_box)
                    more, _filled = story.place(content_box)
                    story.draw(device)
                    writer.end_page()
                    if not more:
                        break
                else:
                    raise ValueError('PDF layout exceeded 1000 pages')
            finally:
                writer.close()
        return output_path
