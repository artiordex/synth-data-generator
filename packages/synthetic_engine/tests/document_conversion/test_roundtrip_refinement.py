# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_roundtrip_refinement.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_roundtrip_refinement.py
# 목적: 포맷 간 왕복 변환 손실 방지 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Exercise real renderer/parser boundaries with nested merged cells and Unicode."""
from io import BytesIO

import pytest
from PIL import Image

from synthetic_engine.document_conversion.core.enums import UnderlineStyle, BorderStyle
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR, SectionIR, TableIR, TableCellIR, ParagraphIR, TextRunIR,
    ImageIR, TabIR, LineBreakIR, BorderIR,
)
from synthetic_engine.document_conversion.geometry.table_geometry import validate_spans
from synthetic_engine.document_conversion.registry import parse_document, renderer_for
from synthetic_engine.document_conversion.qa.qa_auditor import audit


TEXT = ' A\u00a0\u3000①②③⑩㈎㉠ⓐ⑴▪▶※±≤≥食藥處 H₂O m² 참고¹) '


# complex document 작업을 수행함
def complex_document() -> DocumentIR:
    """Shared fixture retains real PNG bytes and logical merge anchors."""
    buffer = BytesIO()
    Image.new('RGB', (40, 20), 'red').save(buffer, format='PNG')
    paragraph = ParagraphIR(inlines=[TextRunIR(TEXT, bold=True, underline=UnderlineStyle.DOUBLE),
                                    TabIR(), TextRunIR('tab'), LineBreakIR(),
                                    TextRunIR('super', superscript=True), TextRunIR('sub', subscript=True)])
    image = ImageIR(buffer.getvalue(), 'image/png', 'png', 40, 20,
                    original_width_px=40, original_height_px=20)
    inner = TableIR(rows=[[TableCellIR(0, 0, content=[paragraph, image])]],
                    column_widths_pt=[100], total_width_pt=100)
    for depth in range(3):
        cell = TableCellIR(0, 0, row_span=2, col_span=2, content=[inner],
                           borders={'top': BorderIR(BorderStyle.NONE),
                                    'slash': BorderIR(BorderStyle.SOLID, 0.5, '112233')})
        inner = TableIR(depth=depth, rows=[[cell], []], column_widths_pt=[60, 60],
                        total_width_pt=120, repeat_header_rows=1, cant_split=True)
    return DocumentIR(source_format='fixture', sections=[SectionIR(
        page_width_pt=595, page_height_pt=842, elements=[inner])])


# nested 병합 이미지 unicode roundtrip 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('target', ['docx', 'html'])
def test_nested_merge_image_unicode_roundtrip(tmp_path, target):
    source = complex_document()
    output = tmp_path / ('roundtrip.' + target)
    renderer_for(target).render(source, output)
    parsed = parse_document(output)
    tables = [b for b in parsed.iter_blocks() if isinstance(b, TableIR)]
    assert len(tables) == 4
    for table in tables:
        validate_spans(table)
    score = audit(source, parsed)
    assert score['logical_cell_retention'] == 1
    assert score['image_retention'] == 1
    assert score['image_aspect_ratio_errors'] == 0
    paragraphs = [b for b in parsed.iter_blocks() if isinstance(b, ParagraphIR)]
    runs = [r for p in paragraphs for r in p.inlines if isinstance(r, TextRunIR)]
    assert any(r.text == TEXT and r.bold and r.underline == UnderlineStyle.DOUBLE for r in runs)
    assert any(r.superscript for r in runs)
    assert any(r.subscript for r in runs)
    assert any(isinstance(r, TabIR) for p in paragraphs for r in p.inlines)
    assert any(isinstance(r, LineBreakIR) for p in paragraphs for r in p.inlines)


# 워드(DOCX) to HTML 웹 문서 keeps logical 셀 목록 and 이미지 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_docx_to_html_keeps_logical_cells_and_images(tmp_path):
    first, second = tmp_path / 'source.docx', tmp_path / 'target.html'
    renderer_for('docx').render(complex_document(), first)
    source = parse_document(first)
    renderer_for('html').render(source, second)
    score = audit(source, parse_document(second))
    assert score['text_fidelity'] >= 0.99
    assert score['logical_cell_retention'] == 1
    assert score['image_retention'] == 1
