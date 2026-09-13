# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_foundations.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_foundations.py
# 목적: 문서 변환 기본 단위 및 공통 열거형을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Cross-module regression tests for document-conversion foundations."""

import os
import subprocess
import sys

import pytest

from synthetic_engine.document_conversion.core.enums import BorderStyle, UnderlineStyle
from synthetic_engine.document_conversion.core.ir import (
    BorderIR, DocumentIR, FieldIR, HeaderFooterIR, ImageIR, LineBreakIR,
    ParagraphIR, SectionIR, TableCellIR, TableIR, TabIR, TextRunIR,
)
from synthetic_engine.document_conversion.core.source_ref import SourceRef
from synthetic_engine.document_conversion.geometry.table_geometry import (
    build_virtual_grid, normalize_column_widths, repair_table_geometry,
)


# document 기하 구조 preserves content and resource identity 기능의 정상 동작 및 제약조건을 테스트함
def test_document_geometry_preserves_content_and_resource_identity():
    """Merged nested geometry must not rewrite text, controls or resources."""
    text = "  \u00a0\u3000\t\u2460\u2469\u321c\u3260\u24d0\u2474\u25aa\u25b6\u203b\u00b1\u2264\u2265\u98df\u85e5\u8655 H\u2082O m\u00b2  "
    source = SourceRef("hwpx", section_no=2, page_no=4, object_id="cell7", row_index=2, col_index=1)
    run = TextRunIR(text, bold=True, underline=UnderlineStyle.DOUBLE, letter_spacing_pt=0.5, scale_percent=90)
    paragraph = ParagraphIR([run, TabIR(), LineBreakIR("soft"), TextRunIR("1", superscript=True)], source_ref=source)
    payload = b"\x89PNG\r\n\x1a\nfixture-resource"
    first = ImageIR(payload, "image/png", "PNG", 80, 40, aspect_ratio=2)
    second = ImageIR(bytes(bytearray(payload)), "image/png", "PNG", 20, 10, aspect_ratio=2)
    inner = TableIR(rows=[[TableCellIR(0, 0, content=[paragraph, first])]], column_widths_pt=[300])
    for depth in range(3):
        inner = TableIR(depth=2-depth, rows=[[TableCellIR(0, 0, content=[inner], padding_pt=(0, 4, 0, 4))]], column_widths_pt=[400])
    anchor = TableCellIR(0, 0, row_span=2, col_span=2, content=[inner, second], source_ref=source,
                         borders={"slash": BorderIR(BorderStyle.SOLID, 0.5, "FF0000")})
    outer = TableIR(rows=[[anchor], []], column_widths_pt=[300, 300], repeat_header_rows=1, cant_split=True)
    footer = HeaderFooterIR([ParagraphIR([FieldIR("PAGE_NUMBER")])])
    document = DocumentIR(source_format="hwpx", sections=[SectionIR(elements=[outer], footer=footer)])
    original_blocks = list(document.iter_blocks())
    repair_table_geometry(outer)
    normalize_column_widths(outer, 240)
    grid = build_virtual_grid(outer)
    assert all(cell is anchor for row in grid for cell in row)
    assert outer.total_width_pt == pytest.approx(240)
    assert document.sections[0].footer is footer
    assert list(document.iter_blocks()) == original_blocks
    assert paragraph.inlines[0].text == text
    assert paragraph.source_ref is source
    assert anchor.borders["slash"].color_hex == "FF0000"
    assert outer.repeat_header_rows == 1 and outer.cant_split
    assert first.image_bytes is second.image_bytes
    assert len(document.resources) == 1
    assert first.width_pt / first.height_pt == first.aspect_ratio


# document import does not require synthesis dependencies 기능의 정상 동작 및 제약조건을 테스트함
def test_document_import_does_not_require_synthesis_dependencies():
    """Run a real fresh-process import without eager model dependencies."""
    script = (
        "import sys; import synthetic_engine; "
        "from synthetic_engine.document_conversion.core.ir import DocumentIR; "
        "assert DocumentIR().sections == []; "
        "assert 'torch' not in sys.modules; assert 'sdv' not in sys.modules; "
        "assert 'SyntheticPipeline' in dir(synthetic_engine); "
        "assert 'SyntheticPipeline' in synthetic_engine.__all__"
    )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=environment, check=False)
    assert result.returncode == 0, result.stderr


# lazy exports preserve resolution and 캐시 기능의 정상 동작 및 제약조건을 테스트함
def test_lazy_exports_preserve_resolution_and_cache(monkeypatch):
    """Existing top-level imports resolve their original implementation once."""
    import synthetic_engine
    from types import SimpleNamespace

    calls = []
    sentinel = object()

    # load 작업을 수행함
    def load(module, package):
        calls.append((module, package))
        return SimpleNamespace(SyntheticPipeline=sentinel)

    if "SyntheticPipeline" in vars(synthetic_engine):
        monkeypatch.delattr(synthetic_engine, "SyntheticPipeline")
    monkeypatch.setattr(synthetic_engine, "import_module", load)
    try:
        assert synthetic_engine.SyntheticPipeline is sentinel
        assert synthetic_engine.SyntheticPipeline is sentinel
        assert calls == [(".pipeline", "synthetic_engine")]
        with pytest.raises(AttributeError):
            getattr(synthetic_engine, "nonexistent_document_export")
    finally:
        vars(synthetic_engine).pop("SyntheticPipeline", None)
