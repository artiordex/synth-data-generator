# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_qa_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_qa_refinement.py
# 목적: 변환 품질 검사 및 감사 기능 개선 사항을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Metrics reveal text, span and resource losses independently."""
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR, SectionIR, ParagraphIR, TextRunIR, HyperlinkIR, FieldIR, TableIR, TableCellIR,
)
from synthetic_engine.document_conversion.qa.qa_auditor import audit, snapshot


# links fields and significant whitespace are audited 기능의 정상 동작 및 제약조건을 테스트함
def test_links_fields_and_significant_whitespace_are_audited():
    source = DocumentIR(sections=[SectionIR(elements=[ParagraphIR(inlines=[
        HyperlinkIR('https://example.invalid', [TextRunIR(' A\u00a0\u3000\t')]),
        FieldIR('PAGE_NUMBER', cached_text='7'),
    ])])])
    target = DocumentIR(sections=[SectionIR(elements=[ParagraphIR(inlines=[TextRunIR('A7')])])])
    assert snapshot(source)[0] == ' A\u00a0\u3000\t7\u2029'
    assert audit(source, target)['exact_text_fidelity'] < 1
    assert audit(source, target)['visual_fidelity'] is None


# identical counts do not hide 병합 손실 기능의 정상 동작 및 제약조건을 테스트함
def test_identical_counts_do_not_hide_merge_loss():
    source = DocumentIR(source_format='hwpx', sections=[SectionIR(elements=[
        TableIR(rows=[[TableCellIR(0, 0, col_span=2)]])])])
    target = DocumentIR(sections=[SectionIR(elements=[TableIR(rows=[[TableCellIR(0, 0)]])])])
    result = audit(source, target)
    assert result['cells_source'] == result['cells_target'] == 1
    assert result['logical_cell_retention'] == 0
    assert result['structure_fidelity'] < 1
    ref = result['qa_warnings'][0]['source_ref']
    assert ref['table_id'] == source.sections[0].elements[0].table_id
    assert ref['row_index'] == ref['col_index'] == 0


# resource 손실 is not reported as perfect 기능의 정상 동작 및 제약조건을 테스트함
def test_resource_loss_is_not_reported_as_perfect():
    source, target = DocumentIR(), DocumentIR()
    source.resources.add(b'original')
    assert audit(source, target)['resource_fidelity'] == 0
    target.resources.add(b'original')
    assert audit(source, target)['resource_fidelity'] == 1
