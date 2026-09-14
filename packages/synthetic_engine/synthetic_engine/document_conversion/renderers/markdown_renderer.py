# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: markdown_renderer.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/markdown_renderer.py
# 목적: IR 트리를 GitHub Flavored Markdown 문서로 변환함
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-14
# =============================================================================
"""Structural Markdown output; complex blocks use offline HTML fallback."""
from pathlib import Path
import tempfile
from ..core.ir import (
    DocumentIR, FieldIR, HyperlinkIR, LineBreakIR, MathIR, ParagraphIR,
    SectionIR, TabIR, TextRunIR,
)
from ..core.capabilities import TargetCapabilities
from .html_renderer import HtmlRenderer, _math


# 인라인 요소 목록을 마크다운 텍스트 및 LaTeX 문자열로 변환함
def _markdown_inlines(inlines, document):
    chunks = []
    stack = list(reversed(inlines))
    while stack:
        item = stack.pop()
        if isinstance(item, TextRunIR):
            chunks.append(item.text)
        elif isinstance(item, TabIR):
            chunks.append('\t')
        elif isinstance(item, LineBreakIR):
            chunks.append('\n')
        elif isinstance(item, HyperlinkIR):
            stack.extend(reversed(item.inlines))
        elif isinstance(item, FieldIR):
            chunks.append(item.cached_text or '')
        elif isinstance(item, MathIR):
            if item.latex and not item.needs_review:
                if item.display_mode == 'display':
                    chunks.append('\n\n$$\n' + item.latex + '\n$$\n\n')
                else:
                    chunks.append('$' + item.latex + '$')
            else:
                chunks.append(_math(item, document.warnings, document.resources))
    return ''.join(chunks)


class MarkdownRenderer:
    capabilities = TargetCapabilities()

    # DocumentIR 문서를 마크다운 형식으로 변환하여 파일로 출력함
    def render(self, document, output_path):
        chunks = []
        for section in document.sections:
            for block in section.elements:
                if isinstance(block, ParagraphIR):
                    prefix = '#' * block.heading_level + ' ' if block.heading_level else ''
                    chunks.append(prefix + _markdown_inlines(block.inlines, document) + '\n\n')
                elif isinstance(block, MathIR) and block.latex and not block.needs_review:
                    chunks.append(
                        ('$' + block.latex + '$' if block.display_mode == 'inline'
                         else '$$\n' + block.latex + '\n$$') + '\n\n'
                    )
                elif isinstance(block, MathIR):
                    chunks.append(_math(block, document.warnings, document.resources) + '\n\n')
                else:
                    with tempfile.TemporaryDirectory(dir=Path(output_path).parent) as directory:
                        temp = Path(directory) / 'block.html'
                        HtmlRenderer().render(DocumentIR(
                            sections=[SectionIR(elements=[block])],
                            resources=document.resources,
                            warnings=document.warnings,
                        ), temp)
                        text = temp.read_text(encoding='utf-8')
                        chunks.append(text[text.index('<body>')+6:text.rindex('</body>')] + '\n\n')
        output_path.write_text(''.join(chunks), encoding='utf-8')
        return output_path
