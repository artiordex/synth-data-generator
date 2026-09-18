# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: markdown_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/markdown_parser.py
# 목적: 마크다운 문서를 분석하여 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Markdown semantic parsing using Python-Markdown's grammar."""
from pathlib import Path
from .html_parser import HtmlParser
from ..core.ir import ConversionWarning


class MarkdownParser:
    # parse 작업을 수행함
    def parse(self, path: Path):
        """
            @description 입력 문서를 파싱하여 중간 표현을 생성함
            @param {path} - 메서드 입력값임
        """
        import markdown
        source = path.read_text(encoding='utf-8')
        html = markdown.markdown(source, extensions=['tables', 'fenced_code', 'sane_lists'])
        document = HtmlParser().parse_content(html or '<div></div>', source_path=str(path), source_format='md')
        document.resources.add(source.encode('utf-8'), 'text/markdown')
        document.warnings.append(ConversionWarning('MARKDOWN_SYNTAX',
            'Source syntax retained as a resource; grammar parsing may resolve escapes and whitespace. No visual layout is inferred.'))
        return document
