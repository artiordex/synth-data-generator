# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: text.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/text.py
# 목적: IR 트리로부터 순수 텍스트를 추출하여 렌더링함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Literal inline text projection for targets with limited inline styling."""
from ..core.ir import TextRunIR, TabIR, LineBreakIR, HyperlinkIR, FieldIR


# inline 텍스트 작업을 수행함
def inline_text(inlines) -> str:
    result, stack = [], list(reversed(inlines))
    while stack:
        item = stack.pop()
        if isinstance(item, TextRunIR):
            result.append(item.text)
        elif isinstance(item, TabIR):
            result.append('\t')
        elif isinstance(item, LineBreakIR):
            result.append('\n')
        elif isinstance(item, HyperlinkIR):
            stack.extend(reversed(item.inlines))
        elif isinstance(item, FieldIR):
            result.append(item.cached_text or '')
    return ''.join(result)
