# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: document_roundtrip_benchmark.py
# 경로: benchmarks/document_roundtrip_benchmark.py
# 목적: 문서 변환 포맷 간 왕복 변환 성능 및 충실도를 측정함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Reproducible real-format round trips; no mock parser or renderer."""
from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages' / 'synthetic_engine'))

from PIL import Image
from synthetic_engine.document_conversion.core.ir import (
    DocumentIR, SectionIR, ParagraphIR, TextRunIR, TableIR, TableCellIR, ImageIR, TabIR, LineBreakIR,
)
from synthetic_engine.document_conversion.core.serialization import document_to_json
from synthetic_engine.document_conversion.registry import parse_document, renderer_for
from synthetic_engine.document_conversion.qa.qa_auditor import audit


# checked 파일 경로 작업을 수행함
def checked_path(relative: str) -> Path:
    """Keep generated reports, fixtures and snapshots within the workspace."""
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Benchmark output escapes workspace')
    return path


# fixture 작업을 수행함
def fixture() -> DocumentIR:
    """Fixed Unicode, whitespace, controls, PNG and four nested logical tables."""
    image = BytesIO()
    Image.new('RGB', (80, 40), 'red').save(image, format='PNG')
    paragraph = ParagraphIR(inlines=[
        TextRunIR(' 일반 공백\u00a0\u3000①②③⑩㈎㉠ⓐ⑴▪▶※±≤≥食藥處 H₂O m² 참고¹) ', bold=True),
        TabIR(), TextRunIR('TAB'), LineBreakIR(), TextRunIR('다음 줄', superscript=True),
    ])
    table = TableIR(table_id='table-0', rows=[[TableCellIR(0, 0, content=[paragraph,
        ImageIR(image.getvalue(), 'image/png', 'png', 80, 40, original_width_px=80, original_height_px=40)])]],
        column_widths_pt=[180], total_width_pt=180)
    for index in range(1, 4):
        table = TableIR(table_id=f'table-{index}', rows=[[TableCellIR(0, 0, row_span=2, col_span=2,
            content=[table])], []], column_widths_pt=[100, 100], total_width_pt=200, cant_split=True)
    return DocumentIR(document_id='roundtrip-benchmark-v1', source_format='ir-fixture',
                      sections=[SectionIR(page_width_pt=595, page_height_pt=842, elements=[table])])


# main 작업을 수행함
def main() -> int:
    """Save actual measurements and per-format failures, without accuracy claims."""
    directory = checked_path('benchmarks/document-roundtrip')
    directory.mkdir(parents=True, exist_ok=True)
    checked_path('benchmarks/document-roundtrip/source.ir.json').write_text(document_to_json(fixture()), encoding='utf-8')
    results = []
    for kind in ('docx', 'html', 'hwpx', 'pdf', 'md', 'xlsx'):
        source = fixture()
        started = time.perf_counter()
        result = {'target_format': kind, 'support_status': 'PARTIALLY_SUPPORTED'}
        try:
            output = checked_path(f'benchmarks/document-roundtrip/sample.{kind}')
            renderer_for(kind).render(source, output)
            result.update(audit(source, parse_document(output)))
            result['status'] = 'measured'
            result['renderer_warnings'] = [asdict(w) for w in source.warnings]
        except Exception as exc:
            result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        result['duration_seconds'] = time.perf_counter() - started
        results.append(result)
        print(kind, result['status'], flush=True)
    report = {'benchmark': 'real_format_synthetic_fixture', 'dataset': 'single_nested_unicode_png_fixture',
              'general_fidelity_claimed': False, 'results': results}
    checked_path('benchmarks/document-latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Document Round-trip Benchmark', '',
             'Real parsers/renderers on one synthetic fixture. Scores do not establish general document fidelity.', '',
             '| Target | Status | Exact Text | Logical Cells | Images | Visual |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in results:
        lines.append(f"| {row['target_format']} | {row['status']} | {row.get('text_fidelity')} | "
                     f"{row.get('logical_cell_retention')} | {row.get('image_retention')} | unmeasured |")
    checked_path('benchmarks/document-latest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return int(any(row['status'] == 'failed' for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
