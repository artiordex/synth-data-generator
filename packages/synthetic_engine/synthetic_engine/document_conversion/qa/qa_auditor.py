# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: qa_auditor.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/qa/qa_auditor.py
# 목적: 변환 전후 문서의 시각적/구조적 품질 지표를 검증함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Audit reparsed output without rewriting source text or inventing visual scores."""
from collections import Counter
from dataclasses import asdict
from difflib import SequenceMatcher
from hashlib import sha256
from typing import Any
import unicodedata

from ..core.ir import (DocumentIR, ParagraphIR, TableIR, ImageIR, ConversionWarning,
                       TextRunIR, TabIR, LineBreakIR, HyperlinkIR, FieldIR)
from ..core.source_ref import SourceRef
from ..renderers.text import inline_text


# calculate 텍스트 retention 작업을 수행함
def calculate_text_retention(source: str, target: str) -> float:
    """Ordered exact character similarity including all whitespace."""
    return SequenceMatcher(None, source, target, autojunk=False).ratio()


# compare 텍스트 작업을 수행함
def compare_text(source: str, target: str) -> dict[str, float]:
    """NFC comparison is supplementary; the exact score remains authoritative."""
    return {
        'text_fidelity': calculate_text_retention(source, target),
        'exact_text_fidelity': calculate_text_retention(source, target),
        'normalized_text_fidelity': calculate_text_retention(
            unicodedata.normalize('NFC', source), unicodedata.normalize('NFC', target)),
    }


# snapshot 작업을 수행함
def snapshot(document: DocumentIR) -> tuple[str, dict[str, int]]:
    """Count logical occurrences and retain paragraph boundaries and link text."""
    text: list[str] = []
    counts = {'paragraphs': 0, 'tables': 0, 'cells': 0, 'images': 0}
    for block in document.iter_blocks():
        if isinstance(block, ParagraphIR):
            counts['paragraphs'] += 1
            text.extend((inline_text(block.inlines), '\u2029'))
        elif isinstance(block, TableIR):
            counts['tables'] += 1
            counts['cells'] += sum(len(row) for row in block.rows)
        elif isinstance(block, ImageIR):
            counts['images'] += 1
    return ''.join(text), counts


# structure 작업을 수행함
def _structure(document: DocumentIR) -> list[tuple]:
    tokens: list[tuple] = [('sections', len(document.sections))]
    for block in document.iter_blocks():
        tokens.append((type(block).__name__,))
        if isinstance(block, TableIR):
            tokens.extend(('cell', c.row_index, c.col_index, c.row_span, c.col_span)
                          for row in block.rows for c in row)
        elif isinstance(block, ParagraphIR):
            stack = list(reversed(block.inlines))
            while stack:
                inline = stack.pop()
                if isinstance(inline, HyperlinkIR):
                    tokens.append(('hyperlink', inline.target))
                    stack.extend(reversed(inline.inlines))
                elif isinstance(inline, FieldIR):
                    tokens.append(('field', inline.field_type))
                elif isinstance(inline, TabIR):
                    tokens.append(('tab',))
                elif isinstance(inline, LineBreakIR):
                    tokens.append(('break', inline.kind))
    return tokens


# compare structure 작업을 수행함
def compare_structure(source: DocumentIR, target: DocumentIR) -> float:
    """Ordered block and logical span similarity, not merely count retention."""
    return SequenceMatcher(None, _structure(source), _structure(target), autojunk=False).ratio()


# calculate 셀 retention 작업을 수행함
def calculate_cell_retention(source: DocumentIR, target: DocumentIR) -> float:
    """Fraction of cells retaining ordered-table coordinates and spans."""
    # 셀 목록 작업을 수행함
    def cells(document: DocumentIR) -> Counter:
        tables = (b for b in document.iter_blocks() if isinstance(b, TableIR))
        return Counter((i, c.row_index, c.col_index, c.row_span, c.col_span)
                       for i, table in enumerate(tables) for row in table.rows for c in row)
    before, after = cells(source), cells(target)
    return sum((before & after).values()) / sum(before.values()) if before else 1.0


# calculate resource retention 작업을 수행함
def calculate_resource_retention(source: DocumentIR, target: DocumentIR) -> float:
    """Fraction of unique original binaries present unchanged in output IR.

    Retained source archive parts are included. This is stricter than image
    retention and does not imply source extraction completeness.
    """
    # digests 작업을 수행함
    def digests(document: DocumentIR) -> set[str]:
        return set(document.resources.digests()) | {
            sha256(b.image_bytes).hexdigest() for b in document.iter_blocks() if isinstance(b, ImageIR)}
    before, after = digests(source), digests(target)
    return len(before & after) / len(before) if before else 1.0


# compare 표 목록 작업을 수행함
def compare_tables(source: DocumentIR, target: DocumentIR) -> list[ConversionWarning]:
    """Locate changed or lost logical cells using original provenance."""
    targets = [b for b in target.iter_blocks() if isinstance(b, TableIR)]
    warnings: list[ConversionWarning] = []
    for index, table in enumerate(b for b in source.iter_blocks() if isinstance(b, TableIR)):
        actual = {(c.row_index, c.col_index): c for row in targets[index].rows for c in row} if index < len(targets) else {}
        for row in table.rows:
            for cell in row:
                matched = actual.get((cell.row_index, cell.col_index))
                if matched is None or (matched.row_span, matched.col_span) != (cell.row_span, cell.col_span):
                    values = asdict(cell.source_ref or table.source_ref or SourceRef(source.source_format))
                    values.update(table_id=table.table_id, row_index=cell.row_index, col_index=cell.col_index)
                    warnings.append(ConversionWarning('QA_CELL_CHANGED',
                        'Logical cell or merge differs in reparsed output.',
                        source_ref=SourceRef(**values), feature='table_geometry'))
    return warnings


# compare 이미지 목록 작업을 수행함
def compare_images(source: DocumentIR, target: DocumentIR) -> dict[str, Any]:
    """Compare image occurrences and payloads independently of archive parts."""
    before = [b for b in source.iter_blocks() if isinstance(b, ImageIR)]
    after = [b for b in target.iter_blocks() if isinstance(b, ImageIR)]
    counts = Counter(sha256(b.image_bytes).hexdigest() for b in after)
    retained = 0
    warnings: list[ConversionWarning] = []
    for image in before:
        digest = sha256(image.image_bytes).hexdigest()
        if counts[digest]:
            retained += 1
            counts[digest] -= 1
        else:
            warnings.append(ConversionWarning('QA_IMAGE_RESOURCE_CHANGED',
                'Image occurrence is missing or its bytes changed.', source_ref=image.source_ref, feature='images'))
    aspect_errors = sum(1 for b in after if b.height_pt <= 0 or
                        abs(b.width_pt / b.height_pt - b.aspect_ratio) > b.aspect_ratio * 0.001)
    return {'image_retention': retained / len(before) if before else 1.0,
            'image_aspect_ratio_errors': aspect_errors, 'warnings': [asdict(w) for w in warnings]}


# 감사 로그 작업을 수행함
def audit(source: DocumentIR, target: DocumentIR) -> dict[str, Any]:
    """Audit target IR; rendered visual fidelity remains explicitly unmeasured."""
    a, before = snapshot(source)
    b, after = snapshot(target)
    images = compare_images(source, target)
    warnings = [asdict(w) for w in compare_tables(source, target)] + images.pop('warnings')
    original_paragraphs = [p for p in source.iter_blocks() if isinstance(p, ParagraphIR)]
    target_paragraphs = [p for p in target.iter_blocks() if isinstance(p, ParagraphIR)]
    for index, paragraph in enumerate(original_paragraphs):
        if index >= len(target_paragraphs) or inline_text(paragraph.inlines) != inline_text(target_paragraphs[index].inlines):
            warnings.append(asdict(ConversionWarning('QA_PARAGRAPH_TEXT_CHANGED',
                'Text differs at the corresponding ordered paragraph position.',
                source_ref=paragraph.source_ref, feature='paragraph_text')))
    result = {
        **compare_text(a, b), 'structure_fidelity': compare_structure(source, target),
        'visual_fidelity': None, 'resource_fidelity': calculate_resource_retention(source, target),
        'logical_cell_retention': calculate_cell_retention(source, target), **images,
        'counts_source': before, 'counts_target': after, 'qa_warnings': warnings,
        'measurement_note': 'Exact Unicode including paragraph boundaries; normalized score uses NFC only. '
                            'Resource score includes retained source archive parts. Visual fidelity is unmeasured.',
    }
    for name in before:
        result[name + '_source'] = before[name]
        result[name + '_target'] = after[name]
    return result
