# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import base64
import re
import shutil
import subprocess
import tempfile
import zipfile
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag
from hwpx.document import HwpxDocument

HWPUNIT_PER_MM = 7200 / 25.4
PORTRAIT_TEXT_WIDTH = 48000
LANDSCAPE_TEXT_WIDTH = 72000


from synthetic_engine.common.bin_finder import find_pyhwp_bin

# valid 한글 표준(HWPX) zip 여부 및 유효성을 판별함
def _is_valid_hwpx_zip(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size < 500 or not zipfile.is_zipfile(path):
            return False
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            return (
                "mimetype" in names
                or "Contents/content.hpf" in names
                or any("section" in name.lower() and name.endswith(".xml") for name in names)
            )
    except Exception:
        return False


# 텍스트 데이터를 정제 및 정리함
def _clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return text.strip()


# length to mm 데이터를 분석하여 파싱함
def _parse_length_to_mm(value: Any) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw or raw.endswith("%"):
        return None
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(mm|cm|in|pt|px)?$", raw)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2) or "px"
    if unit == "mm":
        return amount
    if unit == "cm":
        return amount * 10
    if unit == "in":
        return amount * 25.4
    if unit == "pt":
        return amount * 25.4 / 72
    if unit == "px":
        return amount * 25.4 / 96
    return amount


# mm to hwpunit 작업을 수행함
def _mm_to_hwpunit(mm: float) -> int:
    return max(1, int(round(mm * HWPUNIT_PER_MM)))


# 이미지 크기 mm 작업을 수행함
def _image_size_mm(image: Tag, *, inline: bool = False) -> Dict[str, float]:
    style = image.get("style", "")
    style_width = re.search(r"(?:^|;)\s*width\s*:\s*([^;]+)", style)
    style_height = re.search(r"(?:^|;)\s*height\s*:\s*([^;]+)", style)
    width = _parse_length_to_mm(image.get("width")) or _parse_length_to_mm(style_width.group(1) if style_width else None)
    height = _parse_length_to_mm(image.get("height")) or _parse_length_to_mm(style_height.group(1) if style_height else None)
    max_width = 55.0 if inline else 160.0
    max_height = 55.0 if inline else 220.0
    result: Dict[str, float] = {}
    if width:
        result["width_mm"] = min(width, max_width)
    if height:
        result["height_mm"] = min(height, max_height)
    if not result:
        result["width_mm"] = 35.0 if inline else 100.0
    return result


# 한글(HWP) HTML 웹 문서 요소를 추출하여 반환함
def _extract_hwp_html(input_path: Path) -> Tuple[Optional[str], Optional[Path]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "html_out"
        cmd = find_pyhwp_bin("hwp5html") + ["--output", str(out_dir), str(input_path.resolve())]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
        except Exception:
            return None, None

        html_path = out_dir / "index.xhtml"
        if not html_path.exists():
            html_path = out_dir / "index.html"
        if not html_path.exists():
            return None, None

        bindata_dir = out_dir / "bindata"
        media_dir = bindata_dir if bindata_dir.exists() else None
        html_text = html_path.read_text(encoding="utf-8", errors="ignore")
        css_path = out_dir / 'styles.css'
        if css_path.is_file():
            html_text = '<style>' + css_path.read_text(encoding='utf-8') + '</style>' + html_text

        # Keep the temporary media files alive for the caller by copying them.
        keep_dir = Path(tempfile.mkdtemp(prefix="hwp_hwpx_media_"))
        if media_dir:
            shutil.copytree(media_dir, keep_dir / "bindata", dirs_exist_ok=True)
            media_dir = keep_dir / "bindata"
        return html_text, media_dir


# 한글(HWP) 텍스트 요소를 추출하여 반환함
def _extract_hwp_text(input_path: Path) -> str:
    try:
        res = subprocess.run(
            find_pyhwp_bin("hwp5txt") + [str(input_path.resolve())],
            capture_output=True,
            timeout=60,
        )
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                text = res.stdout.decode(enc).strip()
                if text:
                    return text
            except Exception:
                continue
    except Exception:
        pass
    return ""


# walk HTML 웹 문서 elements 작업을 수행함
def _walk_html_elements(root: Tag) -> List[Tuple[str, Tag]]:
    items: List[Tuple[str, Tag]] = []
    for child in root.children:
        if not isinstance(child, Tag):
            continue
        name = (child.name or "").lower()
        classes = child.get("class", [])
        if "HeaderPageFooter" in classes or "Page" in classes:
            items.extend(_walk_html_elements(child))
        elif name == "table":
            items.append(("table", child))
        elif name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            items.append(("heading", child))
        elif name in {"ul", "ol"}:
            items.append(("list", child))
        elif name == "img":
            items.append(("image", child))
        elif name == "p":
            direct_tables = [t for t in child.find_all("table") if t.find_parent("table") is None]
            if direct_tables:
                items.extend(("table", t) for t in direct_tables)
            else:
                if _clean_text(child.get_text(" ", strip=True)) or child.find("img"):
                    items.append(("paragraph", child))
        elif child.find("table") or child.find("img"):
            items.extend(_walk_html_elements(child))
        elif _clean_text(child.get_text(" ", strip=True)):
            items.append(("paragraph", child))
    return items


# 표(테이블) 행 목록 작업을 수행함
def _table_rows(table: Tag) -> List[Tag]:
    grouped: List[Tag] = []
    for group_name in ("thead", "tbody", "tfoot"):
        group = table.find(group_name, recursive=False)
        if group:
            grouped.extend(group.find_all("tr", recursive=False))
    return grouped or table.find_all("tr", recursive=False)


# 셀 텍스트 작업을 수행함
def _cell_text(cell: Tag) -> str:
    clone = BeautifulSoup(str(cell), "html.parser")
    root = clone.find(cell.name) or clone
    for nested in reversed(root.find_all("table")):
        grid = "\n".join("\t".join(c.get_text("", strip=False) for c in row.find_all(["td", "th"], recursive=False))
                         for row in _table_rows(nested))
        nested.replace_with("\n" + grid + "\n")
    parts = [root.get_text("", strip=False)]
    image_alts = [
        _clean_text(image.get("alt") or image.get("title") or "")
        for image in root.find_all("img")
    ]
    parts.extend(f"[Image: {alt}]" if alt else "[Image]" for alt in image_alts)
    return "\n".join(part for part in parts if part)


# HTML 웹 문서 표(테이블) 격자 구조 작업을 수행함
def _html_table_grid(table: Tag) -> Tuple[List[List[Dict[str, Any]]], int]:
    trs = _table_rows(table)
    occupied: List[set[int]] = [set() for _ in trs]
    rows: List[List[Dict[str, Any]]] = [[] for _ in trs]
    max_cols = 0
    for row_idx, tr in enumerate(trs):
        col_idx = 0
        for cell in tr.find_all(["th", "td"], recursive=False):
            while col_idx in occupied[row_idx]:
                col_idx += 1
            try:
                colspan = max(1, int(cell.get("colspan", 1) or 1))
            except Exception:
                colspan = 1
            try:
                rowspan = max(1, int(cell.get("rowspan", 1) or 1))
            except Exception:
                rowspan = 1
            if row_idx + rowspan > len(trs):
                logging.warning("Table rowspan exceeds row count at row %s col %s; extending grid", row_idx, col_idx)
                extra = row_idx + rowspan - len(occupied)
                occupied.extend(set() for _ in range(max(0, extra)))
                rows.extend([] for _ in range(max(0, extra)))
            if any(c in occupied[r] for r in range(row_idx, row_idx + rowspan)
                   for c in range(col_idx, col_idx + colspan)):
                raise ValueError(f"Overlapping table span at row {row_idx}, col {col_idx}")
            rows[row_idx].append({
                "tag": cell,
                "text": _cell_text(cell),
                "col": col_idx,
                "colspan": colspan,
                "rowspan": rowspan,
                "is_header": cell.name == "th" or tr.find_parent("thead") is not None or row_idx == 0,
            })
            for target_row in range(row_idx, row_idx + rowspan):
                for target_col in range(col_idx, col_idx + colspan):
                    occupied[target_row].add(target_col)
            max_cols = max(max_cols, col_idx + colspan)
            col_idx += colspan
        if occupied[row_idx]:
            max_cols = max(max_cols, max(occupied[row_idx]) + 1)
    return rows, max_cols


# resolve 이미지 작업을 수행함
def _resolve_image(src: str, media_dir: Optional[Path]) -> Optional[Path]:
    if not src or src.startswith("data:"):
        return None
    src_name = Path(src.replace("\\", "/")).name
    candidates = []
    if media_dir:
        candidates.append(media_dir / src_name)
    candidates.append(Path(src))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


# resolve 이미지 data 작업을 수행함
def _resolve_image_data(src: str, media_dir: Optional[Path]) -> Optional[Tuple[bytes, str]]:
    if not src:
        return None
    data_url = re.match(r"^data:image/([^;,]+);base64,(.*)$", src, flags=re.IGNORECASE | re.DOTALL)
    if data_url:
        try:
            image_format = data_url.group(1).lower()
            if image_format == "jpg":
                image_format = "jpeg"
            return base64.b64decode(data_url.group(2)), image_format
        except Exception:
            return None
    image_path = _resolve_image(src, media_dir)
    if not image_path:
        return None
    image_format = image_path.suffix.lstrip(".").lower() or "png"
    if image_format == "jpg":
        image_format = "jpeg"
    return image_path.read_bytes(), image_format


# inline content 요소를 뒤에 덧붙임
def _append_inline_content(
    doc: HwpxDocument,
    paragraph: Any,
    node: Tag,
    media_dir: Optional[Path],
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
) -> None:
    from .hwp_high_fidelity_docx_converter import _resolve_style, parse_length_to_pt
    props = _resolve_style(node, {})
    bold = bold or props.get('font-weight') in ('bold', '700', '800', '900')
    italic = italic or props.get('font-style') == 'italic'
    underline = underline or 'underline' in props.get('text-decoration', '')
    font = props.get('font-family')
    if font:
        font = font.split(',')[0].strip(' "\'')
    if node.name == 'code':
        font = 'Consolas'
    style = {'font': font, 'size': parse_length_to_pt(props.get('font-size')), 'color': props.get('color') if str(props.get('color', '')).startswith('#') else None}
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text:
                paragraph.add_run(text, bold=bold, italic=italic, underline=underline, expand_special_characters=True, **style)
            continue
        if not isinstance(child, Tag):
            continue
        name = (child.name or "").lower()
        if name == "br":
            paragraph.add_run("\n", bold=bold, italic=italic, underline=underline, expand_special_characters=True)
        elif name == "img":
            resolved = _resolve_image_data(child.get("src", ""), media_dir)
            if resolved:
                data, image_format = resolved
                binary = doc.media.add_image(data, image_format)
                kwargs = {}
                for key, value in _image_size_mm(child, inline=True).items():
                    kwargs[key.replace("_mm", "")] = _mm_to_hwpunit(value)
                paragraph.add_picture(binary.item_id, **kwargs)
            else:
                alt = _clean_text(child.get("alt") or child.get("title") or "")
                if alt:
                    paragraph.add_run(f"[Image: {alt}]", bold=bold, italic=italic, underline=underline)
        else:
            _append_inline_content(
                doc,
                paragraph,
                child,
                media_dir,
                bold=bold or name in {"b", "strong"},
                italic=italic or name in {"i", "em"},
                underline=underline or name == "u",
            )


# HTML 웹 문서 문단 항목을 목록에 추가함
def _add_html_paragraph(doc: HwpxDocument, element: Tag, media_dir: Optional[Path]) -> None:
    paragraph = doc.add_paragraph("", include_run=False)
    _append_inline_content(doc, paragraph, element, media_dir)


# 열(컬럼) 너비 목록 hwpunit 요소를 추출하여 반환함
def _extract_col_widths_hwpunit(html_table: Tag, page_width: int) -> List[int]:
    rows, count = _html_table_grid(html_table)
    if not count:
        return []
    widths = [0.0] * count

    # 너비 작업을 수행함
    def width(tag: Tag) -> float:
        match = re.search(r"(?:^|;)\s*width\s*:\s*([^;]+)", tag.get("style", ""))
        value = match.group(1).strip() if match else str(tag.get("width", ""))
        if value.endswith("%"):
            try:
                return page_width * float(value[:-1]) / 100
            except ValueError:
                return 0.0
        mm = _parse_length_to_mm(value)
        return mm * HWPUNIT_PER_MM if mm else 0.0

    index = 0
    for col in html_table.find_all("col"):
        if col.find_parent("table") is not html_table:
            continue
        for _ in range(max(1, int(col.get("span", 1)))):
            if index < count:
                widths[index] = width(col)
                index += 1
    for row in rows:
        for cell in row:
            value = width(cell["tag"]) / cell["colspan"]
            for index in range(cell["col"], cell["col"] + cell["colspan"]):
                if not widths[index] and value:
                    widths[index] = value
    known = [value for value in widths if value > 0]
    fallback = sum(known) / len(known) if known else 1
    widths = [value or fallback for value in widths]
    result = [max(1, int(page_width * value / sum(widths))) for value in widths]
    result[-1] += page_width - sum(result)
    return result


# HTML 웹 문서 표(테이블) 항목을 목록에 추가함
def _add_html_table(doc: HwpxDocument, html_table: Tag, page_width: int, media_dir: Optional[Path] = None, *, container: Any = None) -> None:
    rows, col_count = _html_table_grid(html_table)
    if not rows or not col_count:
        return
    table = (container or doc).add_table(rows=len(rows), cols=col_count)
    widths = _extract_col_widths_hwpunit(html_table, page_width)
    table.set_column_widths(widths)
    for r_idx, row in enumerate(rows):
        for cell in row:
            col = cell["col"]
            target = table.cell(r_idx, col)
            if cell["rowspan"] > 1 or cell["colspan"] > 1:
                try:
                    target = table.merge_cells(r_idx, col, r_idx + cell["rowspan"] - 1, col + cell["colspan"] - 1)
                except Exception as exc:
                    logging.warning("HWPX merge failed at row %s col %s: %s; preserving text in origin", r_idx, col, exc)
            if cell["is_header"]:
                table.set_cell_shading(r_idx, col, "#EDF2F6")
            paragraph = target.paragraphs[0] if target.paragraphs else target.add_paragraph("")
            for child in cell["tag"].children:
                if isinstance(child, Tag) and child.name == "table":
                    _add_html_table(doc, child, sum(widths[col:col + cell["colspan"]]), media_dir, container=target)
                    paragraph = target.add_paragraph("")
                elif isinstance(child, Tag) and child.find("table"):
                    # Structured fallback retains nested rows and column separators.
                    paragraph.add_run(_cell_text(child), expand_special_characters=True)
                else:
                    wrapper = BeautifulSoup("<span></span>", "html.parser").span
                    import copy
                    wrapper.append(copy.copy(child))
                    _append_inline_content(doc, paragraph, wrapper, media_dir, bold=cell["is_header"])


# 마크다운 runs 요소를 뒤에 덧붙임
def _append_markdown_runs(paragraph: Any, text: str) -> None:
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    for token in pattern.split(text):
        if not token:
            continue
        bold = token.startswith("**") and token.endswith("**")
        italic = not bold and token.startswith("*") and token.endswith("*")
        code = token.startswith("`") and token.endswith("`")
        value = token[2:-2] if bold else token[1:-1] if italic or code else token
        paragraph.add_run(value, bold=bold, italic=italic, font="Consolas" if code else None,
                          expand_special_characters=True)


# 마크다운 표(테이블) 항목을 목록에 추가함
def _add_markdown_table(doc: HwpxDocument, lines: List[str]) -> bool:
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return False
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return False
    width = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    try:
        table.set_column_widths([max(2500, int(42000 / width))] * width)
    except Exception:
        pass
    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row + [""] * (width - len(row))):
            try:
                _append_markdown_runs(table.cell(r_idx, c_idx).paragraphs[0], value)
                if r_idx == 0:
                    table.set_cell_shading(r_idx, c_idx, "#EEF3F8")
            except Exception:
                pass
    return True


# 마크다운 텍스트 to 한글 표준(HWPX) 작업을 수행함
def markdown_text_to_hwpx(markdown_text: str, output_path: Path) -> Path:
    doc = HwpxDocument.new()
    pending_table: List[str] = []

    # flush 표(테이블) 작업을 수행함
    def flush_table() -> None:
        nonlocal pending_table
        if pending_table:
            if not _add_markdown_table(doc, pending_table):
                for row in pending_table:
                    doc.add_paragraph(row)
            pending_table = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("|") and line.strip().endswith("|"):
            pending_table.append(line)
            continue
        flush_table()
        if not line.strip():
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            try:
                doc.add_heading(heading.group(2).strip(), level=len(heading.group(1)))
            except Exception:
                doc.add_paragraph(heading.group(2).strip())
        elif re.match(r"^\s*[-*+]\s+", line):
            doc.add_paragraph("- " + re.sub(r"^\s*[-*+]\s+", "", line).strip())
        else:
            _append_markdown_runs(doc.add_paragraph("", include_run=False), line)
    flush_table()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(output_path)
    return output_path


# 한글 표준(HWPX) from HTML 웹 문서 구조를 생성 및 조립함
def _build_hwpx_from_html(html_text: str, output_path: Path, media_dir: Optional[Path] = None) -> Path:
    """Build HWPX from HTML/hwp5html output without depending on API route internals."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(html_text, "html.parser")
    from .hwp_high_fidelity_docx_converter import parse_css_rules, _resolve_style
    global_css = parse_css_rules('\n'.join(tag.get_text() for tag in soup.find_all('style')))
    cache = {}
    resolved = [(tag, _resolve_style(tag, global_css, cache=cache)) for tag in soup.find_all(True) if tag.name not in ('style', 'script')]
    for tag, props in resolved:
        tag['style'] = ';'.join(f'{key}:{value}' for key, value in props.items())
    body = soup.find("body") or soup
    doc = HwpxDocument.new()

    tables = body.find_all("table")
    max_cols = max((_html_table_grid(table)[1] for table in tables), default=1)
    dense_table = any(count >= 4 and
                      sum(len(c["text"]) for row in rows for c in row) /
                      max(1, sum(len(row) for row in rows)) > 15
                      for rows, count in (_html_table_grid(t) for t in tables))
    if max_cols >= 6 or dense_table:
        try:
            doc.page.set_size(width=84188, height=59528, orientation="landscape")
        except Exception:
            try:
                doc.page.set_size(width=84188, height=59528)
            except Exception:
                pass
        page_width = LANDSCAPE_TEXT_WIDTH
    else:
        page_width = PORTRAIT_TEXT_WIDTH

    for kind, element in _walk_html_elements(body):
        if kind == "heading":
            text = _clean_text(element.get_text(" ", strip=True))
            if text:
                level = int(element.name[1]) if element.name and element.name[1].isdigit() else 1
                try:
                    doc.add_heading(text, level=level)
                except Exception:
                    doc.add_paragraph(text)
        elif kind == "paragraph":
            text = _clean_text(element.get_text(" ", strip=True))
            if text or element.find("img"):
                _add_html_paragraph(doc, element, media_dir)
                align = (element.get("style") or "").lower()
                if "text-align:center" in align or "text-align: center" in align:
                    try:
                        doc.set_paragraph_format(paragraph_index=len(doc.paragraphs) - 1, alignment="center")
                    except Exception:
                        pass
                elif "text-align:right" in align or "text-align: right" in align:
                    try:
                        doc.set_paragraph_format(paragraph_index=len(doc.paragraphs) - 1, alignment="right")
                    except Exception:
                        pass
        elif kind == "list":
            for li in element.find_all("li"):
                text = _clean_text(li.get_text(" ", strip=True))
                if text:
                    doc.add_paragraph("- " + text)
        elif kind == "image":
            resolved = _resolve_image_data(element.get("src", ""), media_dir)
            if resolved:
                data, image_format = resolved
                try:
                    doc.add_picture(data, image_format, **_image_size_mm(element))
                except Exception:
                    pass
            else:
                alt = _clean_text(element.get("alt") or element.get("title") or "")
                if alt:
                    doc.add_paragraph(f"[Image: {alt}]")
        elif kind == "table":
            _add_html_table(doc, element, page_width, media_dir)

    doc.save_to_path(output_path)
    if not _is_valid_hwpx_zip(output_path):
        raise RuntimeError(f"Invalid HWPX package: {output_path.name}")
    return output_path


# 한글(HWP) to high 충실도 한글 표준(HWPX) 데이터를 대상 포맷으로 변환함
def convert_hwp_to_high_fidelity_hwpx(input_path: Path, output_path: Path) -> Path:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_text, media_dir = _extract_hwp_html(input_path)
    if html_text:
        return _build_hwpx_from_html(html_text, output_path, media_dir=media_dir)

    doc = HwpxDocument.new()
    if not html_text:
        text = _extract_hwp_text(input_path)
        if text:
            logging.warning('HWP layout extraction failed; preserving text only for %s', input_path.name)
            markdown_text_to_hwpx(text, output_path)
            return output_path
        raise RuntimeError('HWP content could not be extracted; no substitute document was created.')

    doc.save_to_path(output_path)
    if not _is_valid_hwpx_zip(output_path):
        raise RuntimeError(f"Invalid HWPX package: {output_path.name}")
    return output_path


# any 한글(HWP) to 한글 표준(HWPX) 데이터를 대상 포맷으로 변환함
def convert_any_hwp_to_hwpx(input_path: Path, output_path: Path) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    ext = input_path.suffix.lower()

    if ext == ".hwp":
        return convert_hwp_to_high_fidelity_hwpx(input_path, output_path)
    if ext == ".hwpx":
        if input_path.resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(input_path.read_bytes())
        return output_path
    if ext == ".pdf":
        from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_hwpx
        convert_pdf_to_high_fidelity_hwpx(input_path, output_path)
        return output_path
    if ext in {".docx", ".doc"}:
        from synthetic_engine.exporters.document_exporter import convert_word_to_hwpx
        return convert_word_to_hwpx(input_path, output_path)
    if ext in {".md", ".markdown", ".txt"}:
        text = input_path.read_text(encoding="utf-8", errors="ignore")
        return markdown_text_to_hwpx(text, output_path)

    raise RuntimeError(f"Unsupported HWPX source format: {ext}")
# =============================================================================
# 파일명: hwp_high_fidelity_hwpx_converter.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/hwp_high_fidelity_hwpx_converter.py
# 목적: HWP 문서를 HWPX 구조로 고충실도 변환함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
