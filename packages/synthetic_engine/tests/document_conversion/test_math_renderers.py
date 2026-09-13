# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_math_renderers.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_math_renderers.py
# 목적: MathIR HTML/Markdown 출력과 복잡한 표의 반응형 표시를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Renderer-facing MathIR and responsive table regressions."""
from pathlib import Path

from lxml import html

from synthetic_engine.document_conversion.core.ir import (
    DocumentIR,
    LineBreakIR,
    MathIR,
    ParagraphIR,
    SectionIR,
    TableCellIR,
    TableIR,
    TextRunIR,
)
from synthetic_engine.document_conversion.core.resources import ResourceStore
from synthetic_engine.document_conversion.core.source_ref import SourceRef
from synthetic_engine.document_conversion.renderers.html_renderer import HtmlRenderer
from synthetic_engine.document_conversion.renderers.markdown_renderer import MarkdownRenderer


MATHML = (
    '<math xmlns="http://www.w3.org/1998/Math/MathML">'
    '<mfrac><mn>1</mn><mi>n</mi></mfrac></math>'
)


def _document(*blocks, resources=None):
    return DocumentIR(
        source_format="fixture",
        sections=[SectionIR(elements=list(blocks))],
        resources=resources or ResourceStore(),
    )


def test_html_renders_inline_latex_and_display_mathml(tmp_path):
    inline = MathIR(
        latex=r"x_{i}+1",
        source_syntax="omml",
        source_resource_id="a" * 64,
        source_ref=SourceRef("docx", section_no=1, object_id="inline-1"),
    )
    display = MathIR(
        display_mode="display",
        mathml=MATHML,
        source_syntax="mathml",
        source_resource_id="b" * 64,
        source_ref=SourceRef("docx", section_no=1, object_id="display-1"),
    )
    document = _document(ParagraphIR([TextRunIR("식 "), inline]), display)
    output = tmp_path / "math.html"

    HtmlRenderer().render(document, output)
    root = html.fromstring(output.read_text(encoding="utf-8"))

    inline_node = root.xpath('//*[@data-math-display="inline"]')[0]
    display_node = root.xpath('//*[@data-math-display="display"]')[0]
    assert inline_node.tag == "span"
    assert inline_node.text_content().strip() == r"x_{i}+1"
    assert display_node.tag == "div"
    assert display_node.xpath('.//*[local-name()="mfrac"]')
    assert not root.xpath('//*[@data-needs-review="true"]')


def test_html_math_fallback_embeds_image_and_visible_review_state(tmp_path):
    resources = ResourceStore()
    image_id = resources.add(b"not-a-real-png-but-preserved", "image/png")
    math = MathIR(
        display_mode="display",
        source_syntax="ocr-candidate",
        fallback_image_resource_id=image_id,
        confidence=0.72,
        needs_review=True,
        failure_reason="OCR structure is unverified.",
        ocr_candidates=["x^2 + y^2 = z^2"],
        source_ref=SourceRef("image", page_no=1, object_id="ocr-block:0"),
    )
    output = tmp_path / "fallback.html"

    HtmlRenderer().render(_document(math, resources=resources), output)
    root = html.fromstring(output.read_text(encoding="utf-8"))

    node = root.xpath('//*[@data-needs-review="true"]')[0]
    assert "x^2 + y^2 = z^2" in node.text_content()
    assert "수식 검토 필요" in node.text_content()
    assert "72.0%" in node.text_content()
    image = node.xpath('.//img[contains(@class,"document-math__fallback-image")]')[0]
    assert image.get("src").startswith("data:image/png;base64,")
    assert "OCR structure is unverified." in node.text_content()


def test_html_invalid_mathml_is_not_reported_as_success(tmp_path):
    math = MathIR(
        mathml='<math xmlns="http://www.w3.org/1998/Math/MathML"><script>bad()</script></math>',
        source_expression="untrusted math",
        source_syntax="mathml",
    )
    document = _document(math)
    output = tmp_path / "invalid-mathml.html"

    HtmlRenderer().render(document, output)
    root = html.fromstring(output.read_text(encoding="utf-8"))

    node = root.xpath('//*[@data-needs-review="true"]')[0]
    assert "untrusted math" in node.text_content()
    assert not root.xpath("//script")
    assert any(warning.code == "HTML_MATH_RENDER_FAILED" for warning in document.warnings)


def test_html_complex_table_uses_scroll_and_horizontal_cells(tmp_path):
    long_latex = r"\frac{population_{treatment}}{population_{control}}+" + "x" * 120
    cell = TableCellIR(
        0,
        0,
        row_span=2,
        col_span=2,
        width_pt=42,
        content=[ParagraphIR([
            MathIR(latex=long_latex, source_syntax="omml"),
            TextRunIR(" 매우 긴 한글 설명은 글자 단위 세로 열이 되지 않아야 합니다."),
            LineBreakIR(),
            TextRunIR("두 번째 줄"),
        ])],
    )
    table = TableIR(rows=[[cell], []], column_widths_pt=[21, 21], total_width_pt=42)
    output = tmp_path / "table.html"

    HtmlRenderer().render(_document(table), output)
    rendered = output.read_text(encoding="utf-8")
    root = html.fromstring(rendered)

    wrapper = root.xpath('//div[contains(@class,"document-table-scroll")]')[0]
    rendered_cell = wrapper.xpath('.//td[@rowspan="2"][@colspan="2"]')[0]
    assert "overflow-x:auto" in wrapper.get("style")
    assert "min-width:" in rendered_cell.get("style")
    assert "table-layout:auto" in wrapper.xpath("./table")[0].get("style")
    assert "word-break:break-all" not in rendered
    assert "white-space:nowrap" in rendered
    assert "두 번째 줄" in rendered_cell.text_content()


def test_markdown_emits_verified_latex_and_review_fallback(tmp_path):
    inline = MathIR(latex="x+1", source_syntax="omml")
    display = MathIR(display_mode="display", latex=r"\frac{1}{n}", source_syntax="omml")
    review = MathIR(
        source_expression="{a} over {b}",
        source_syntax="hancom-equation-script",
        source_resource_id="c" * 64,
        needs_review=True,
        failure_reason="LaTeX conversion is not implemented.",
    )
    output = tmp_path / "math.md"

    MarkdownRenderer().render(
        _document(ParagraphIR([TextRunIR("inline "), inline]), display, ParagraphIR([review])),
        output,
    )
    rendered = output.read_text(encoding="utf-8")

    assert "inline $x+1$" in rendered
    assert "$$\n\\frac{1}{n}\n$$" in rendered
    assert 'data-needs-review="true"' in rendered
    assert "{a} over {b}" in rendered
    assert "수식 검토 필요" in rendered


def test_markdown_complex_table_uses_html_fallback(tmp_path):
    review = MathIR(
        source_expression="수식 후보",
        source_syntax="ocr-candidate",
        source_resource_id="d" * 64,
        needs_review=True,
        failure_reason="검토가 필요합니다.",
    )
    cell = TableCellIR(
        0,
        0,
        row_span=2,
        col_span=2,
        content=[ParagraphIR([
            review,
            TextRunIR(" 긴 한글 설명" * 15),
            LineBreakIR(),
            TextRunIR("다음 줄"),
        ])],
    )
    table = TableIR(rows=[[cell], []], column_widths_pt=[40, 40], total_width_pt=80)
    output = tmp_path / "table.md"

    MarkdownRenderer().render(_document(table), output)
    rendered = output.read_text(encoding="utf-8")

    assert '<div class="document-table-scroll"' in rendered
    assert '<table class="document-table"' in rendered
    assert 'rowspan="2" colspan="2"' in rendered
    assert 'data-needs-review="true"' in rendered
    assert "다음 줄" in rendered and "<br>" in rendered
    assert "| ---" not in rendered


def test_web_preview_css_protects_tables_math_and_review_badges():
    repository = Path(__file__).resolve().parents[4]
    css = (repository / "apps/web/src/index.css").read_text(encoding="utf-8")

    assert ".markdown-preview-body .document-table-scroll" in css
    assert ".markdown-preview-body .document-math" in css
    assert "overflow-x: auto" in css
    assert "word-break: keep-all" in css
    assert "data-needs-review" in css
    assert "@media (max-width: 640px)" in css
