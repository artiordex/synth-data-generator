# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: markdown_renderer.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/markdown_renderer.py
# 목적: IR 트리를 GitHub Flavored Markdown 문서로 변환함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Structural Markdown output; complex blocks use offline HTML fallback."""
from pathlib import Path
import tempfile
from ..core.ir import DocumentIR, SectionIR, ParagraphIR
from ..core.capabilities import TargetCapabilities
from .text import inline_text
from .html_renderer import HtmlRenderer


class MarkdownRenderer:
    capabilities = TargetCapabilities()

    # render 작업을 수행함
    def render(self, document, output_path):
        chunks = []
        for section in document.sections:
            for block in section.elements:
                if isinstance(block, ParagraphIR):
                    prefix = '#' * block.heading_level + ' ' if block.heading_level else ''
                    chunks.append(prefix + inline_text(block.inlines) + '\n\n')
                else:
                    with tempfile.TemporaryDirectory(dir=Path(output_path).parent) as directory:
                        temp = Path(directory) / 'block.html'
                        HtmlRenderer().render(DocumentIR(sections=[SectionIR(elements=[block])]), temp)
                        text = temp.read_text(encoding='utf-8')
                        chunks.append(text[text.index('<body>')+6:text.rindex('</body>')] + '\n\n')
        output_path.write_text(''.join(chunks), encoding='utf-8')
        return output_path
