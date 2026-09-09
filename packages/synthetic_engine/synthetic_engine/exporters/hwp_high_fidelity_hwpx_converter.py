# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import re
import shutil
import subprocess
import sys
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


def _find_pyhwp_bin(tool_name: str) -> List[str]:
    py_dir = Path(sys.executable).parent
    for candidate in (py_dir / f"{tool_name}.exe", py_dir / tool_name):
        if candidate.exists():
            return [str(candidate)]
    which_path = shutil.which(tool_name)
    if which_path:
        return [which_path]
    if tool_name == "hwp5html":
        return [sys.executable, "-m", "hwp5.hwp5html"]
    if tool_name == "hwp5txt":
        return [sys.executable, "-m", "hwp5.hwp5txt"]
    return [tool_name]


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


def _clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return text.strip()


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


def _mm_to_hwpunit(mm: float) -> int:
    return max(1, int(round(mm * HWPUNIT_PER_MM)))


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


def _extract_hwp_html(input_path: Path) -> Tuple[Optional[str], Optional[Path]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "html_out"
        cmd = _find_pyhwp_bin("hwp5html") + ["--output", str(out_dir), str(input_path.resolve())]
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

        # Keep the temporary media files alive for the caller by copying them.
        keep_dir = Path(tempfile.mkdtemp(prefix="hwp_hwpx_media_"))
        if media_dir:
            shutil.copytree(media_dir, keep_dir / "bindata", dirs_exist_ok=True)
            media_dir = keep_dir / "bindata"
        return html_text, media_dir


def _extract_hwp_text(input_path: Path) -> str:
    try:
        res = subprocess.run(
            _find_pyhwp_bin("hwp5txt") + [str(input_path.resolve())],
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


def _table_rows(table: Tag) -> List[Tag]:
    grouped: List[Tag] = []
    for group_name in ("thead", "tbody", "tfoot"):
        group = table.find(group_name, recursive=False)
        if group:
            grouped.extend(group.find_all("tr", recursive=False))
    return grouped or table.find_all("tr", recursive=False)


def _cell_text(cell: Tag) -> str:
    clone = BeautifulSoup(str(cell), "html.parser")
    root = clone.find(cell.name) or clone
    for nested in root.find_all("table"):
        nested.decompose()
    parts = [_clean_text(root.get_text(" ", strip=True))]
    image_alts = [
        _clean_text(image.get("alt") or image.get("title") or "")
        for image in root.find_all("img")
    ]
    parts.extend(f"[Image: {alt}]" if alt else "[Image]" for alt in image_alts)
    return "\n".join(part for part in parts if part)


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
            rows[row_idx].append({
                "tag": cell,
                "text": _cell_text(cell),
                "col": col_idx,
                "colspan": colspan,
                "rowspan": rowspan,
                "is_header": cell.name == "th" or tr.find_parent("thead") is not None or row_idx == 0,
            })
            for target_row in range(row_idx, min(len(trs), row_idx + rowspan)):
                for target_col in range(col_idx, col_idx + colspan):
                    occupied[target_row].add(target_col)
            max_cols = max(max_cols, col_idx + colspan)
            col_idx += colspan
        if occupied[row_idx]:
            max_cols = max(max_cols, max(occupied[row_idx]) + 1)
    return rows, max_cols


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
    for child in node.children:
        if isinstance(child, NavigableString):
            text = re.sub(r"\s+", " ", str(child).replace("\r", "").replace("\n", " "))
            if text.strip():
                paragraph.add_run(text, bold=bold, italic=italic, underline=underline)
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


def _add_html_paragraph(doc: HwpxDocument, element: Tag, media_dir: Optional[Path]) -> None:
    paragraph = doc.add_paragraph("", include_run=False)
    _append_inline_content(doc, paragraph, element, media_dir)


def _add_html_table(doc: HwpxDocument, html_table: Tag, page_width: int, media_dir: Optional[Path] = None) -> None:
    rows, col_count = _html_table_grid(html_table)
    if not rows or col_count <= 0:
        return
    row_count = len(rows)

    table = doc.add_table(rows=row_count, cols=col_count)
    try:
        table.set_column_widths([max(2500, int(page_width / col_count))] * col_count)
    except Exception:
        pass

    occupied = [[False] * col_count for _ in range(row_count)]
    for r_idx, row in enumerate(rows):
        for cell in row:
            col = int(cell["col"])
            if col >= col_count:
                break
            colspan = min(int(cell["colspan"]), col_count - col)
            rowspan = min(int(cell["rowspan"]), row_count - r_idx)
            target_cell = table.cell(r_idx, col)
            for rr in range(r_idx, r_idx + rowspan):
                for cc in range(col, col + colspan):
                    occupied[rr][cc] = True
            try:
                table.set_cell_text(r_idx, col, cell["text"])
                if cell["is_header"] or r_idx == 0:
                    table.set_cell_shading(r_idx, col, "#EEF3F8")
                if colspan > 1 or rowspan > 1:
                    target_cell = table.merge_cells(r_idx, col, r_idx + rowspan - 1, col + colspan - 1)
                for image in cell["tag"].find_all("img"):
                    resolved = _resolve_image_data(image.get("src", ""), media_dir)
                    if not resolved:
                        continue
                    data, image_format = resolved
                    binary = doc.media.add_image(data, image_format)
                    paragraph = target_cell.paragraphs[-1] if target_cell.paragraphs else target_cell.add_paragraph("")
                    kwargs = {}
                    for key, value in _image_size_mm(image, inline=True).items():
                        kwargs[key.replace("_mm", "")] = _mm_to_hwpunit(value)
                    paragraph.add_picture(binary.item_id, **kwargs)
            except Exception:
                pass


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
                table.set_cell_text(r_idx, c_idx, value)
                if r_idx == 0:
                    table.set_cell_shading(r_idx, c_idx, "#EEF3F8")
            except Exception:
                pass
    return True


def markdown_text_to_hwpx(markdown_text: str, output_path: Path) -> Path:
    doc = HwpxDocument.new()
    pending_table: List[str] = []

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
            doc.add_paragraph(line.strip())
    flush_table()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(output_path)
    return output_path


def _build_hwpx_from_html(html_text: str, output_path: Path, media_dir: Optional[Path] = None) -> Path:
    """Build HWPX from HTML/hwp5html output without depending on API route internals."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(html_text, "html.parser")
    body = soup.find("body") or soup
    doc = HwpxDocument.new()

    tables = body.find_all("table")
    max_cols = max((_html_table_grid(table)[1] for table in tables), default=1)
    if max_cols >= 5:
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
            markdown_text_to_hwpx(text, output_path)
            return output_path
        doc.add_paragraph("HWP document text could not be extracted.")

    doc.save_to_path(output_path)
    if not _is_valid_hwpx_zip(output_path):
        raise RuntimeError(f"Invalid HWPX package: {output_path.name}")
    return output_path


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
