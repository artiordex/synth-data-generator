# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: document_conversion_service.py
# 경로: apps/api/src/synthetic_api/application/services/document_conversion_service.py
# 목적: PDF, HWPX, DOCX, HTML 등 다중 포맷 고충실도 변환을 오케스트레이션함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
"""Document conversion orchestration and legacy format adapters; no route dependency."""
from __future__ import annotations

import json
import logging
from threading import RLock
import html as html_lib
import os
import re
import sys
import tempfile
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
import numpy as np

from synthetic_api.core.config import settings
from synthetic_api.application.services.dataset_service import DatasetService
from synthetic_api.application.services.conversion_rules import (
    ConversionRuleError,
    DATASET_SOURCES,
    DOCUMENT_SOURCES,
    IMAGE_SOURCES,
    catalog,
    normalize_source,
    normalize_target,
    resolve_rule,
    source_kind,
)
from synthetic_engine.profiling.analyzer import read_table


from synthetic_engine.common.bin_finder import find_pyhwp_bin
from synthetic_engine.common.com_session import win32_com_session


class ConversionError(Exception):
    # ConversionError 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# word to PDF 문서 데이터를 대상 포맷으로 변환함
def _convert_word_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert Word document to PDF using Windows COM or LibreOffice fallback."""
    try:
        with win32_com_session("Word.Application") as word:
            word.Visible = False
            doc = word.Documents.Open(str(input_path.resolve()))
            doc.SaveAs(str(output_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
            if output_path.exists() and output_path.stat().st_size > 0:
                return
    except Exception:
        pass

    import subprocess
    try:
        cmd = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output_path.parent.resolve()), str(input_path.resolve())]
        subprocess.run(cmd, capture_output=True, timeout=30)
        default_out = output_path.parent / f"{input_path.stem}.pdf"
        if default_out.exists() and default_out != output_path:
            default_out.rename(output_path)
    except Exception as exc:
        raise RuntimeError(f"Word PDF 변환 실패: {str(exc)}")


# 한글(HWP) 워드 문서 데이터를 대상 포맷으로 변환함
def _convert_hwp_doc(input_path: Path, output_path: Path, target_fmt: str) -> None:
    """Convert HWP document using high-fidelity dual engines (Windows COM + OWPML)."""
    fmt_lower = target_fmt.lower().strip()
    if fmt_lower == "hwpx":
        from synthetic_engine.exporters.hwp_high_fidelity_hwpx_converter import convert_hwp_to_high_fidelity_hwpx
        convert_hwp_to_high_fidelity_hwpx(input_path, output_path)
        _validate_hwpx_output(output_path)
        return
    elif fmt_lower in ("docx", "doc"):
        from synthetic_engine.exporters.hwp_high_fidelity_docx_converter import convert_any_hwp_to_docx
        convert_any_hwp_to_docx(input_path, output_path)
        return
    elif fmt_lower == "html":
        _convert_hwp_to_html(input_path, output_path)
        return
    elif fmt_lower == "pdf":
        _convert_hwp_to_pdf(input_path, output_path)
        return

    # Windows COM generic fallback
    try:
        with win32_com_session("HWPFrame.HwpObject") as hwp:
            try:
                hwp.XHwpWindows.Item(0).Visible = False
            except Exception:
                pass
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass

            opened = hwp.Open(str(input_path.resolve()))
            if opened:
                fmt_arg = "PDF" if fmt_lower == "pdf" else ("HTML" if fmt_lower == "html" else ("HWP" if fmt_lower == "hwp" else "HWPX"))
                saved = hwp.SaveAs(str(output_path.resolve()), fmt_arg, "")
                if saved and output_path.exists() and output_path.stat().st_size > 0:
                    return
    except Exception:
        pass


# 한글(HWP) 문단 목록 pure 요소를 추출하여 반환함
def _extract_hwp_paragraphs_pure(input_path: Path) -> List[str]:
    """Extract paragraphs from HWP using text extractors or fallback."""
    _, md = _convert_hwp_to_html_and_markdown(input_path)
    return [p.strip() for p in md.splitlines() if p.strip()]


# 한글 표준(HWPX) output 유효성 및 제약조건을 검증함
def _validate_hwpx_output(output_path: Path) -> None:
    """Validate that output HWPX is a valid ZIP package."""
    if not output_path.exists() or not zipfile.is_zipfile(output_path):
        raise RuntimeError(f"유효하지 않은 ZIP 패키지: {output_path.name}")


# read 한글 표준(HWPX) plain 텍스트 작업을 수행함
def _read_hwpx_plain_text(document: Any) -> str:
    """Read HWPX text through the current python-hwpx API with legacy fallback."""
    text_api = getattr(document, "text", None)
    plain = getattr(text_api, "plain", None)
    if callable(plain):
        return plain()
    export_text = getattr(document, "export_text", None)
    if callable(export_text):
        return export_text()
    return ""


# 한글(HWP) to 한글 표준(HWPX) pure 데이터를 대상 포맷으로 변환함
def _convert_hwp_to_hwpx_pure(input_path: Path, output_path: Path) -> None:
    """Pure-python high-fidelity converter from HWP to HWPX package using HwpxDocument."""
    paragraphs = _extract_hwp_paragraphs_pure(input_path)
    if paragraphs and paragraphs != ["한글 문서 내용을 읽을 수 없습니다."]:
        from hwpx.document import HwpxDocument
        from synthetic_engine.exporters.hwp_high_fidelity_hwpx_converter import convert_hwp_to_high_fidelity_hwpx
        try:
            convert_hwp_to_high_fidelity_hwpx(input_path, output_path)
            _validate_hwpx_output(output_path)
            chk_doc = HwpxDocument.open(output_path)
            if "HWP document text could not be extracted" in _read_hwpx_plain_text(chk_doc) and paragraphs:
                raise ValueError("Placeholder fallback detected")
            return
        except Exception:
            doc = HwpxDocument.new()
            for p in paragraphs:
                doc.add_paragraph(p)
            doc.save_to_path(output_path)
            _validate_hwpx_output(output_path)
            return

    from synthetic_engine.exporters.hwp_high_fidelity_hwpx_converter import convert_hwp_to_high_fidelity_hwpx
    convert_hwp_to_high_fidelity_hwpx(input_path, output_path)
    _validate_hwpx_output(output_path)


# 워드(DOCX) to 마크다운 데이터를 대상 포맷으로 변환함
def _convert_docx_to_markdown(input_path: Path) -> str:
    """Convert DOCX file to Markdown preserving headings, lists, and tables."""
    try:
        from synthetic_engine.exporters.document_exporter import convert_word_to_markdown
        return convert_word_to_markdown(input_path)
    except Exception as exc:
        raise RuntimeError(f"Word 마크다운 변환 실패: {str(exc)}")


# hancom 텍스트 입력값을 안전하게 소독함
def sanitize_hancom_text(text: str) -> str:
    """Convert Hancom Office Private Use Area (PUA) characters to standard Unicode."""
    if not text:
        return ""
    pua_map = {
        0xF02B1: "①", 0xF02B2: "②", 0xF02B3: "③", 0xF02B4: "④", 0xF02B5: "⑤",
        0xF02B6: "⑥", 0xF02B7: "⑦", 0xF02B8: "⑧", 0xF02B9: "⑨", 0xF02BA: "⑩",
        0xF0020: " ", 0xF0001: "", 0xF0002: "", 0xF000A: "\n",
    }
    chars = []
    for ch in text:
        code = ord(ch)
        if code in pua_map:
            chars.append(pua_map[code])
        elif 0xE000 <= code <= 0xF8FF or 0xF0000 <= code <= 0xFFFFF:
            if 0xF02B1 <= code <= 0xF02BA:
                chars.append(chr(0x2460 + (code - 0xF02B1)))
            else:
                pass
        else:
            chars.append(ch)
    return "".join(chars)


# 표(테이블) soup to 격자 구조 HTML 웹 문서 and 마크다운 작업을 수행함
def _table_soup_to_grid_html_and_md(tbl_el: Tag) -> tuple[str, str]:
    """
    Convert a BeautifulSoup <table> element into:
    1. Clean HTML string with preserved rowspans/colspans & styling
    2. 100% valid GFM Markdown table string with equal columns in all rows
    """
    tbody = tbl_el.find("tbody", recursive=False)
    trs = (tbody.find_all("tr", recursive=False) if tbody else tbl_el.find_all("tr", recursive=False))
    if not trs:
        return "", ""

    grid_data = []
    html_trs = []

    for tr_idx, tr in enumerate(trs):
        row_cells = []
        html_cells = []
        for tc in tr.find_all(["th", "td"], recursive=False):
            try:
                cs = max(1, int(tc.get("colspan", 1) or 1))
            except Exception:
                cs = 1
            try:
                rs = max(1, int(tc.get("rowspan", 1) or 1))
            except Exception:
                rs = 1

            attrs = []
            if cs > 1:
                attrs.append(f'colspan="{cs}"')
            if rs > 1:
                attrs.append(f'rowspan="{rs}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""

            nested_tables = tc.find_all("table")
            nested_table_mds = []

            # Clone cell to extract text and images without nested tables
            from bs4 import BeautifulSoup
            tc_clone = BeautifulSoup(str(tc), "html.parser")
            for sub_tbl in tc_clone.find_all("table"):
                sub_tbl.decompose()

            cell_imgs = tc_clone.find_all("img")
            img_mds = []
            for img in cell_imgs:
                src = img.get("src", "")
                alt = img.get("alt", "이미지")
                img_mds.append(f"![{alt}]({src})" if src else "[이미지]")

            cell_txt = sanitize_hancom_text(tc_clone.get_text(strip=True)).replace("\n", " ").replace("|", "/")
            if img_mds and not cell_txt:
                cell_txt = " ".join(img_mds)
            elif img_mds and cell_txt:
                cell_txt = f"{cell_txt} " + " ".join(img_mds)

            tag_name = "th" if tr_idx == 0 or tc.name == "th" else "td"
            html_cells.append(f"<{tag_name}{attr_str}>{tc.decode_contents()}</{tag_name}>")

            row_cells.append({
                "text": cell_txt,
                "colspan": cs,
                "rowspan": rs,
            })

            # Process nested tables recursively
            for sub_tbl in nested_tables:
                _, sub_md = _table_soup_to_grid_html_and_md(sub_tbl)
                if sub_md:
                    nested_table_mds.append(sub_md)

        if html_cells:
            html_trs.append(f"      <tr>{''.join(html_cells)}</tr>")
        grid_data.append((row_cells, nested_table_mds))

    num_rows = len(grid_data)
    estimated_cols = max(sum(c["colspan"] for c in r[0]) for r in grid_data) if grid_data else 1
    matrix = [[None for _ in range(estimated_cols * 2)] for _ in range(num_rows)]
    max_c_seen = 0

    for r_idx, (r_items, _) in enumerate(grid_data):
        c_cursor = 0
        for item in r_items:
            while c_cursor < len(matrix[r_idx]) and matrix[r_idx][c_cursor] is not None:
                c_cursor += 1
            cs = item["colspan"]
            rs = item["rowspan"]
            for ri in range(r_idx, min(r_idx + rs, num_rows)):
                for ci in range(c_cursor, c_cursor + cs):
                    if ci < len(matrix[ri]):
                        if ci == c_cursor:
                            matrix[ri][ci] = item["text"]
                        else:
                            matrix[ri][ci] = ""
                        max_c_seen = max(max_c_seen, ci + 1)
            c_cursor += cs

    final_grid = []
    for r_idx in range(num_rows):
        row_cells = [matrix[r_idx][c] or "" for c in range(max_c_seen)]
        final_grid.append(row_cells)

    md_lines = []
    if final_grid and max_c_seen > 0:
        header_row = list(final_grid[0])
        if all(not h.strip() for h in header_row):
            if len(final_grid) > 1 and any(final_grid[1]):
                non_empty = [c for c in final_grid[1] if c.strip()]
                if len(non_empty) == 1 and max_c_seen == 1:
                    header_row = ["문서 제목"]
                else:
                    header_row = [f"항목 {i+1}" for i in range(len(header_row))]
            else:
                header_row = [f"구분 {i+1}" for i in range(len(header_row))]
        md_lines.append("| " + " | ".join(header_row) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(header_row)) + " |")
        for row in final_grid[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

    # Collect nested table markdown blocks
    all_nested_mds = []
    for _, nested_mds in grid_data:
        for nmd in nested_mds:
            if nmd.strip():
                all_nested_mds.append(nmd.strip())

    table_md = "\n".join(md_lines)
    if all_nested_mds:
        table_md += "\n\n" + "\n\n".join(all_nested_mds)

    table_html = (
        '<div class="table-container">\n  <table class="styled-table">\n'
        + "\n".join(html_trs)
        + "\n  </table>\n</div>"
    )
    return table_html, table_md


# HTML 웹 문서 soup to clean HTML 웹 문서 and 마크다운 데이터를 분석하여 파싱함
def _parse_html_soup_to_clean_html_and_md(html_content: str, bindata_dir: Optional[Path] = None) -> tuple[str, str]:
    """Parse HTML string and convert into styled HTML body and Markdown preserving all tables and images."""
    import base64
    from bs4 import BeautifulSoup, Tag
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Inline all images as Base64 Data URLs if bindata_dir or local src exists
    for img in soup.find_all("img"):
        src_attr = img.get("src", "")
        if src_attr:
            src_clean = src_attr.replace("\\", "/")
            img_file = None
            if bindata_dir and (bindata_dir / Path(src_clean).name).exists():
                img_file = bindata_dir / Path(src_clean).name
            elif Path(src_clean).exists():
                img_file = Path(src_clean)

            if img_file and img_file.exists():
                ext = img_file.suffix.lstrip(".").lower()
                if ext == "jpg":
                    ext = "jpeg"
                try:
                    b64 = base64.b64encode(img_file.read_bytes()).decode("ascii")
                    img["src"] = f"data:image/{ext};base64,{b64}"
                    img["style"] = "max-width: 100%; max-height: 280px; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin: 6px auto; display: block;"
                except Exception:
                    pass

    html_blocks: List[str] = []
    md_blocks: List[str] = []

    body = soup.find("body") or soup

    # node 데이터를 처리함
    def process_node(node: Tag) -> None:
        """HTML 노드를 순회하며 문서 본문 구조를 수집함"""
        for el in node.children:
            if not isinstance(el, Tag):
                continue
            if "HeaderPageFooter" in el.get("class", []) or "Page" in el.get("class", []):
                process_node(el)
                continue

            tag_name = el.name.lower()
            if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag_name[1]) if tag_name[1].isdigit() else 1
                txt = sanitize_hancom_text(el.get_text(strip=True))
                if txt:
                    html_blocks.append(f"<{tag_name}>{txt}</{tag_name}>")
                    md_blocks.append("#" * level + " " + txt + "\n")
            elif tag_name == "table":
                if el.find_parent("table") is None:
                    t_html, t_md = _table_soup_to_grid_html_and_md(el)
                    if t_html:
                        html_blocks.append(t_html)
                    if t_md:
                        md_blocks.append(t_md + "\n")

            elif tag_name == "p":
                tbls = el.find_all("table")
                if tbls:
                    for t in tbls:
                        if t.find_parent("table") is None:
                            t_html, t_md = _table_soup_to_grid_html_and_md(t)
                            if t_html:
                                html_blocks.append(t_html)
                            if t_md:
                                md_blocks.append(t_md + "\n")
                else:
                    imgs = el.find_all("img")
                    if imgs:
                        for im in imgs:
                            html_blocks.append(f'<div class="my-3 text-center">{str(im)}</div>')
                            src = im.get("src", "")
                            md_blocks.append(f"![이미지]({src})" if src else "![이미지](첨부 이미지)")
                    txt = sanitize_hancom_text(el.get_text(strip=True))
                    if txt:
                        html_blocks.append(f"<p>{txt}</p>")
                        md_blocks.append(f"{txt}\n")

            elif tag_name in ("ul", "ol"):
                items = []
                for li in el.find_all("li"):
                    li_txt = sanitize_hancom_text(li.get_text(strip=True))
                    if li_txt:
                        items.append(f"<li>{li_txt}</li>")
                        md_blocks.append(f"- {li_txt}")
                if items:
                    html_blocks.append(f"<{tag_name}>\n  " + "\n  ".join(items) + f"\n</{tag_name}>")
                    md_blocks.append("")

            elif tag_name == "img":
                html_blocks.append(f'<div class="my-3 text-center">{str(el)}</div>')
                src = el.get("src", "")
                md_blocks.append(f"![이미지]({src})" if src else "![이미지](첨부 이미지)")

            elif tag_name == "div":
                if el.find("table") or el.find("img"):
                    process_node(el)
                else:
                    txt = sanitize_hancom_text(el.get_text(strip=True))
                    if txt:
                        html_blocks.append(f"<p>{txt}</p>")
                        md_blocks.append(f"{txt}\n")
            else:
                if el.find("table") or el.find("img"):
                    process_node(el)
                else:
                    txt = sanitize_hancom_text(el.get_text(strip=True))
                    if txt:
                        html_blocks.append(f"<p>{txt}</p>")
                        md_blocks.append(f"{txt}\n")

    process_node(body)

    if not html_blocks:
        txt = sanitize_hancom_text(body.get_text(strip=True))
        if txt:
            html_blocks = [f"<p>{p}</p>" for p in txt.split("\n\n") if p.strip()]
            md_blocks = [txt]

    return "\n".join(html_blocks), "\n".join(md_blocks).strip()


# 한글(HWP) to HTML 웹 문서 and 마크다운 데이터를 대상 포맷으로 변환함
def _convert_hwp_to_html_and_markdown(input_path: Path) -> tuple[str, str]:
    """Convert HWP file to clean HTML body and Markdown with complete table preservation."""
    import tempfile
    import subprocess

    # 1. PyHWP (hwp5html) with explicit executable path
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "html_out"
            cmd = find_pyhwp_bin("hwp5html") + ["--output", str(out_dir), str(input_path.resolve())]
            res = subprocess.run(cmd, capture_output=True, timeout=60)
            index_xhtml = out_dir / "index.xhtml"
            if not index_xhtml.exists():
                index_xhtml = out_dir / "index.html"
            if index_xhtml.exists():
                html_text = index_xhtml.read_text(encoding="utf-8", errors="ignore")
                bindata_dir = out_dir / "bindata" if (out_dir / "bindata").exists() else None
                body_html, md = _parse_html_soup_to_clean_html_and_md(html_text, bindata_dir=bindata_dir)
                if body_html and body_html.strip():
                    return body_html, md
    except Exception:
        pass

    # 2. Try Windows COM if available
    try:
        with win32_com_session("HWPFrame.HwpObject") as hwp:
            hwp.XHwpWindows.Item(0).Visible = False
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass
            opened = hwp.Open(str(input_path.resolve()), "HWP", "versionwarning:False;forcedopen:True")
            if opened:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_html = Path(tmpdir) / "temp.html"
                    hwp.SaveAs(str(tmp_html.resolve()), "HTML", "")
                    if tmp_html.exists():
                        raw_bytes = tmp_html.read_bytes()
                        for enc in ("euc-kr", "cp949", "utf-8"):
                            try:
                                html_text = raw_bytes.decode(enc)
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            html_text = raw_bytes.decode("euc-kr", errors="ignore")
                        body_html, md = _parse_html_soup_to_clean_html_and_md(html_text)
                        if body_html and body_html.strip():
                            return body_html, md
    except Exception:
        pass

    # 3. Text fallback
    try:
        res = subprocess.run(find_pyhwp_bin("hwp5txt") + [str(input_path.resolve())], capture_output=True, timeout=30)
        txt = res.stdout.decode("utf-8", errors="ignore").strip()
        if txt:
            paragraphs = [f"<p>{p.strip()}</p>" for p in txt.split("\n\n") if p.strip()]
            return "\n".join(paragraphs), txt
    except Exception:
        pass

    return "<p>한글 문서 내용을 읽을 수 없습니다.</p>", "한글 문서 내용을 읽을 수 없습니다."


# 한글(HWP) to 마크다운 데이터를 대상 포맷으로 변환함
def _convert_hwp_to_markdown(input_path: Path) -> str:
    """Convert HWP file to Markdown."""
    _, md = _convert_hwp_to_html_and_markdown(input_path)
    return md


# 한글 표준(HWPX) tbl to 격자 구조 and HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_hwpx_tbl_to_grid_and_html(
    tbl: ET.Element,
    hp_ns: dict,
    bindata_map: Optional[dict] = None,
    style_maps: Optional[dict] = None,
) -> tuple[str, str]:
    """Convert HWPX table to normalized GFM markdown and HTML table with 2D matrix resolution."""
    trs = tbl.findall("./hp:tr", hp_ns)
    if not trs:
        return "", ""

    grid_data = []
    html_trs = []
    declared_cols = max(1, int(tbl.attrib.get("colCnt", 1)))
    column_widths = [0] * declared_cols

    for tr_idx, tr in enumerate(trs):
        row_cells = []
        html_cells = []
        for tc in tr.findall("./hp:tc", hp_ns):
            cell_addr = tc.find("./hp:cellAddr", hp_ns)
            cell_span = tc.find("./hp:cellSpan", hp_ns)
            try:
                cs = max(1, int(cell_span.attrib.get("colSpan", 1))) if cell_span is not None else 1
            except Exception:
                cs = 1
            try:
                rs = max(1, int(cell_span.attrib.get("rowSpan", 1))) if cell_span is not None else 1
            except Exception:
                rs = 1
            col_addr = int(cell_addr.attrib.get("colAddr", len(row_cells))) if cell_addr is not None else len(row_cells)
            row_addr = int(cell_addr.attrib.get("rowAddr", tr_idx)) if cell_addr is not None else tr_idx
            cell_size = tc.find("./hp:cellSz", hp_ns)
            cell_width = int(cell_size.attrib.get("width", 0)) if cell_size is not None else 0
            if cell_width:
                share = cell_width / cs
                for index in range(col_addr, min(declared_cols, col_addr + cs)):
                    column_widths[index] = max(column_widths[index], share)

            paragraphs = []
            for paragraph in tc.findall("./hp:subList/hp:p", hp_ns):
                value = "".join(sanitize_hancom_text(t.text) for t in paragraph.findall(".//hp:t", hp_ns) if t.text)
                if value:
                    paragraphs.append(value)
            if not paragraphs:
                paragraphs = ["".join(sanitize_hancom_text(t.text) for t in tc.findall(".//hp:t", hp_ns) if t.text)]
            cell_str = "\n".join(paragraphs).strip()

            # Check for pictures in this cell
            cell_imgs = []
            if bindata_map:
                for pic in tc.iter():
                    bin_id = next((value for key, value in pic.attrib.items()
                                   if key.rsplit("}", 1)[-1] in {"binaryItemIDRef", "binDataID", "binData"}), "")
                    if not bin_id:
                        continue
                    for k, v in bindata_map.items():
                        if bin_id == k or bin_id in k or k in bin_id:
                            media_type = "image/png" if k.lower().endswith(".png") else "image/jpeg"
                            cell_imgs.append(f"data:{media_type};base64,{v}")
                            break

            img_mds = [f"![이미지]({im})" for im in cell_imgs]
            markdown_cell = cell_str + (("\n" if cell_str else "") + " ".join(img_mds) if img_mds else "")

            attrs = []
            if cs > 1:
                attrs.append(f'colspan="{cs}"')
            if rs > 1:
                attrs.append(f'rowspan="{rs}"')
            attrs.extend((f'data-row="{row_addr}"', f'data-col="{col_addr}"'))
            attr_str = (" " + " ".join(attrs)) if attrs else ""

            tag = "td"
            inner_html = html_lib.escape(cell_str).replace("\n", "<br/>")
            if cell_imgs:
                inner_html += "".join([f'<img src="{im}" alt="" style="display:block;max-width:100%;height:auto;" />' for im in cell_imgs])
            styles = []
            margins = tc.find("./hp:cellMargin", hp_ns)
            if margins is not None:
                styles.append(
                    f'padding:{int(margins.attrib.get("top", 0))/7200*25.4:.2f}mm '
                    f'{int(margins.attrib.get("right", 0))/7200*25.4:.2f}mm '
                    f'{int(margins.attrib.get("bottom", 0))/7200*25.4:.2f}mm '
                    f'{int(margins.attrib.get("left", 0))/7200*25.4:.2f}mm'
                )
            if style_maps:
                fill = style_maps.get("cell_fills", {}).get(tc.attrib.get("borderFillIDRef"))
                if fill:
                    styles.append(f"background-color:{fill}")
                runs = tc.findall(".//hp:run", hp_ns)
                if runs and all(run.attrib.get("charPrIDRef") in style_maps.get("bold_chars", set()) for run in runs):
                    styles.append("font-weight:700")
                paragraph_alignments = {
                    style_maps.get("paragraph_alignments", {}).get(paragraph.attrib.get("paraPrIDRef"))
                    for paragraph in tc.findall("./hp:subList/hp:p", hp_ns)
                }
                paragraph_alignments.discard(None)
                if len(paragraph_alignments) == 1:
                    styles.append(f"text-align:{paragraph_alignments.pop()}")
            sub_list = tc.find("./hp:subList", hp_ns)
            vertical = (sub_list.attrib.get("vertAlign", "TOP").lower() if sub_list is not None else "top")
            styles.append("vertical-align:" + {"center": "middle", "bottom": "bottom"}.get(vertical, "top"))
            style_attr = f' style="{";".join(styles)}"' if styles else ""
            html_cells.append(f"<{tag}{attr_str}{style_attr}>{inner_html}</{tag}>")
            row_cells.append({
                "text": markdown_cell.replace("\n", "<br/>").replace("|", "\\|"),
                "row": row_addr,
                "col": col_addr,
                "colspan": cs,
                "rowspan": rs,
            })

        if html_cells:
            html_trs.append(f"      <tr>{''.join(html_cells)}</tr>")
        grid_data.append(row_cells)

    num_rows = max(
        int(tbl.attrib.get("rowCnt", len(grid_data))),
        max((cell["row"] + cell["rowspan"] for row in grid_data for cell in row), default=0),
    )
    estimated_cols = max(
        declared_cols,
        max((cell["col"] + cell["colspan"] for row in grid_data for cell in row), default=0),
    )
    matrix = [[None for _ in range(estimated_cols)] for _ in range(num_rows)]
    max_c_seen = estimated_cols

    for r_items in grid_data:
        for item in r_items:
            r_idx = item["row"]
            c_cursor = item["col"]
            cs = item["colspan"]
            rs = item["rowspan"]
            if r_idx < 0 or c_cursor < 0 or r_idx + rs > num_rows or c_cursor + cs > estimated_cols:
                raise ValueError("HWPX 표 셀이 선언된 행·열 범위를 벗어났습니다.")
            for ri in range(r_idx, r_idx + rs):
                for ci in range(c_cursor, c_cursor + cs):
                    if matrix[ri][ci] is not None:
                        raise ValueError(f"HWPX 표 병합 셀이 {ri + 1}행 {ci + 1}열에서 충돌합니다.")
                    matrix[ri][ci] = item["text"] if (ri, ci) == (r_idx, c_cursor) else ""

    final_grid = []
    for r_idx in range(num_rows):
        row_cells = [matrix[r_idx][c] or "" for c in range(max_c_seen)]
        final_grid.append(row_cells)

    md_lines = []
    if final_grid and max_c_seen > 0:
        header_row = list(final_grid[0])
        if all(not h.strip() for h in header_row):
            if len(final_grid) > 1 and any(final_grid[1]):
                non_empty = [c for c in final_grid[1] if c.strip()]
                if len(non_empty) == 1 and max_c_seen == 1:
                    header_row = ["문서 제목"]
                else:
                    header_row = [f"항목 {i+1}" for i in range(len(header_row))]
            else:
                header_row = [f"구분 {i+1}" for i in range(len(header_row))]
        md_lines.append("| " + " | ".join(header_row) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(header_row)) + " |")
        for row in final_grid[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

    table_md = "\n".join(md_lines)
    if not any(column_widths):
        column_widths = [1] * max_c_seen
    total_width = sum(column_widths[:max_c_seen]) or max_c_seen
    colgroup = "<colgroup>" + "".join(
        f'<col style="width:{width / total_width * 100:.4f}%" />' for width in column_widths[:max_c_seen]
    ) + "</colgroup>"
    table_html = (
        '<div class="table-container">\n  <table class="styled-table hwpx-table">\n'
        + colgroup
        + "\n".join(html_trs)
        + "\n  </table>\n</div>"
    )
    return table_html, table_md


# 한글 표준(HWPX) to HTML 웹 문서 and 마크다운 데이터를 대상 포맷으로 변환함
def _convert_hwpx_to_html_and_markdown(input_path: Path) -> tuple[str, str]:
    """Parse HWPX XML in sequential document order into (body_html, markdown_text) preserving all tables."""
    import base64
    hp_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    html_blocks: List[str] = []
    md_blocks: List[str] = []

    try:
        with zipfile.ZipFile(input_path, "r") as zf:
            namelist = zf.namelist()
            # Extract BinData images as Base64 map
            bindata_map = {}
            for n in namelist:
                if "bindata/" in n.lower() and not n.endswith("/"):
                    try:
                        raw_data = zf.read(n)
                        b64 = base64.b64encode(raw_data).decode("ascii")
                        bindata_map[Path(n).name] = b64
                    except Exception:
                        pass
            if "Contents/content.hpf" in namelist:
                manifest = ET.fromstring(zf.read("Contents/content.hpf"))
                for item in manifest.iter():
                    identifier, href = item.attrib.get("id"), item.attrib.get("href")
                    if identifier and href:
                        path = href if href in namelist else f"Contents/{href}"
                        if path in namelist:
                            bindata_map[identifier] = base64.b64encode(zf.read(path)).decode("ascii")

            style_maps = {"cell_fills": {}, "bold_chars": set(), "paragraph_alignments": {}}
            if "Contents/header.xml" in namelist:
                header = ET.fromstring(zf.read("Contents/header.xml"))
                for element in header.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    identifier = element.attrib.get("id")
                    if local_name == "borderFill" and identifier:
                        brush = next((item for item in element.iter() if item.tag.rsplit("}", 1)[-1] == "winBrush"), None)
                        color = brush.attrib.get("faceColor") if brush is not None else None
                        if color and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                            style_maps["cell_fills"][identifier] = color
                    elif local_name == "charPr" and identifier:
                        if any(item.tag.rsplit("}", 1)[-1] == "bold" for item in element):
                            style_maps["bold_chars"].add(identifier)
                    elif local_name == "paraPr" and identifier:
                        align = next((item for item in element if item.tag.rsplit("}", 1)[-1] == "align"), None)
                        horizontal = align.attrib.get("horizontal", "").lower() if align is not None else ""
                        if horizontal in {"left", "center", "right", "justify"}:
                            style_maps["paragraph_alignments"][identifier] = horizontal

            section_names = sorted([n for n in namelist if "section" in n.lower() and n.endswith(".xml")])
            if not section_names:
                if "Preview/PrvText.txt" in namelist:
                    txt = zf.read("Preview/PrvText.txt").decode("utf-16", errors="ignore")
                    paragraphs = [f"<p>{p.strip()}</p>" for p in txt.split("\n") if p.strip()]
                    return "\n".join(paragraphs), txt
                return "<p>본문 내용이 없습니다.</p>", "본문 내용이 없습니다."

            for s_name in section_names:
                xml_bytes = zf.read(s_name)
                root = ET.fromstring(xml_bytes)
                sec = root.find(".//hp:sec", hp_ns) or root

                for p in sec.findall("./hp:p", hp_ns):
                    # 1. Direct text in paragraph runs (excluding text inside sub-tables)
                    p_text_parts = []
                    for run in p.findall("./hp:run", hp_ns):
                        for t in run.findall("./hp:t", hp_ns):
                            if t.text:
                                p_text_parts.append(sanitize_hancom_text(t.text))

                    p_text = "".join(p_text_parts).strip()
                    if p_text:
                        html_blocks.append(f"<p>{p_text}</p>")
                        md_blocks.append(f"{p_text}\n")

                    # 2. Tables inside this paragraph
                    for tbl in p.findall("./hp:run/hp:tbl", hp_ns) or p.findall(".//hp:tbl", hp_ns):
                        table_html, table_md = _convert_hwpx_tbl_to_grid_and_html(
                            tbl, hp_ns, bindata_map=bindata_map, style_maps=style_maps
                        )
                        if table_html:
                            html_blocks.append(table_html)
                        if table_md:
                            md_blocks.append("\n" + table_md + "\n")

        return "\n".join(html_blocks), "\n".join(md_blocks).strip()
    except Exception as exc:
        return f"<pre>{str(exc)}</pre>", str(exc)


# 한글 표준(HWPX) to 마크다운 데이터를 대상 포맷으로 변환함
def _convert_hwpx_to_markdown(input_path: Path) -> str:
    """Convert HWPX file to Markdown."""
    _, md = _convert_hwpx_to_html_and_markdown(input_path)
    return md


# 분할 multiline 셀 content 작업을 수행함
def _split_multiline_cell_content(cell_text: Optional[str], n: int, is_count_col: bool = False) -> List[str]:
    """Split cell text into N sub-items corresponding to each sub-row."""
    if not cell_text or n <= 1:
        return [cell_text or ""] + [""] * max(0, n - 1)

    text = cell_text.strip()
    if is_count_col or re.match(r"^[\d\s\n]+$", text):
        parts = [p.strip() for p in text.split() if p.strip()]
        if len(parts) == n:
            return parts

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) == n:
        return lines

    blank_splits = [s.strip() for s in re.split(r"\n\s*\n", text) if s.strip()]
    if len(blank_splits) == n:
        return blank_splits

    if len(lines) > n:
        candidate_splits = []
        curr = [lines[0]]
        for l in lines[1:]:
            prev = curr[-1]
            if not prev.endswith(",") and re.search(r"\)\s*$", prev) and len(candidate_splits) < n - 1:
                candidate_splits.append(" ".join(curr))
                curr = [l]
            else:
                curr.append(l)
        candidate_splits.append(" ".join(curr))

        if len(candidate_splits) == n:
            return candidate_splits

        k, m = divmod(len(lines), n)
        chunks = []
        idx = 0
        for i in range(n):
            take = k + (1 if i < m else 0)
            chunks.append(" ".join(lines[idx:idx+take]))
            idx += take
        return chunks

    return lines + [""] * (n - len(lines))


# auto 감지 행 셀 목록 HTML 웹 문서 작업을 수행함
def _auto_detect_row_cells_html(
    row: List[Optional[str]],
    is_th: bool = False,
    is_summary: bool = False,
    custom_class: Optional[str] = None
) -> tuple[str, List[str]]:
    """
    Format a table row into HTML string with automatic colspan detection for trailing None/empty cells,
    and return (html_string, list_of_flat_values).
    """
    cells_html = []
    flat_vals = []
    n = len(row)
    tag = "th" if is_th else "td"
    i = 0

    while i < n:
        cell_val = row[i]
        val_str = (str(cell_val) if cell_val is not None else "").strip()

        # Determine colspan: count consecutive None or empty cells following a non-empty cell
        colspan = 1
        j = i + 1
        if val_str:
            while j < n and (row[j] is None or str(row[j]).strip() == ""):
                colspan += 1
                j += 1

        txt = val_str.replace("\n", "<br/>")
        if is_summary and txt:
            txt = f"<b>{txt}</b>"

        attrs = []
        if colspan > 1:
            attrs.append(f'colspan="{colspan}"')

        classes = []
        if is_summary:
            classes.append("table-summary-cell")
        if custom_class:
            classes.append(custom_class)
        if colspan > 1:
            classes.append("merged-colspan-cell")

        if classes:
            attrs.append(f'class="{" ".join(classes)}"')

        attr_str = (" " + " ".join(attrs)) if attrs else ""
        cells_html.append(f"<{tag}{attr_str}>{txt}</{tag}>")
        flat_vals.append(val_str)

        i = j if colspan > 1 else i + 1

    return "".join(cells_html), flat_vals


# format hierarchical 표(테이블) to HTML 웹 문서 and 마크다운 작업을 수행함
def _format_hierarchical_table_to_html_and_md(raw_table: List[List[Optional[str]]]) -> tuple[str, str, List[List[str]]]:
    """
    Transform raw 2D extracted table (which may have merged/grouped hierarchical cells)
    into high-precision HTML with semantic <thead>, <tbody>, <td rowspan>, <td colspan>, and clean Markdown.
    """
    if not raw_table or not any(raw_table):
        return "", "", []

    num_cols = max(len(r) for r in raw_table)
    padded = [r + [None] * (num_cols - len(r)) for r in raw_table]

    # Clean Header
    header_raw = padded[0]
    # If first header cell is empty but next is '자치구' (district), label it '지역(교육청)'
    if (header_raw[0] is None or str(header_raw[0]).strip() == "") and len(header_raw) > 1 and str(header_raw[1]).strip() == "자치구":
        header_raw[0] = "지역(교육청)"

    blocks = []
    curr_block = []

    for r_idx in range(1, len(padded)):
        row = padded[r_idx]
        is_summary = any("합계" in str(c) or "총계" in str(c) or (re.search(r"^\d+교", str(c).strip()) and r_idx == len(padded)-1) for c in row if c)
        is_continuation = (
            not is_summary and
            r_idx > 1 and
            (row[0] is None or str(row[0]).strip() == "") and
            (row[1] is None or str(row[1]).strip() == "")
        )

        if is_continuation and curr_block:
            curr_block.append(row)
        else:
            if curr_block:
                blocks.append(curr_block)
            curr_block = [row]

    if curr_block:
        blocks.append(curr_block)

    html_rows = []
    md_rows = []
    flat_rows = []

    # 1. Header HTML & Markdown
    th_html, _ = _auto_detect_row_cells_html(header_raw, is_th=True)
    html_rows.append(f"    <thead>\n      <tr>{th_html}</tr>\n    </thead>")

    clean_th_md = [(c or "").strip().replace("\n", " ").replace("|", "/") for c in header_raw]
    md_rows.append("| " + " | ".join(clean_th_md) + " |")
    md_rows.append("| " + " | ".join(["---"] * len(clean_th_md)) + " |")
    flat_rows.append([c or "" for c in header_raw])

    html_rows.append("    <tbody>")

    for block in blocks:
        first_r = block[0]
        is_summary = any("합계" in str(c) or "총계" in str(c) or re.search(r"^\d+교", str(c).strip()) for c in first_r if c)

        # A. Summary / Total Row with automatic colspan
        if is_summary:
            row_html, _ = _auto_detect_row_cells_html(first_r, is_th=False, is_summary=True)
            html_rows.append(f'      <tr class="table-summary-row">{row_html}</tr>')

            clean_r_md = [(c or "").strip().replace("\n", " ").replace("|", "/") for c in first_r if c is not None]
            md_rows.append("| " + " | ".join(clean_r_md) + " |")
            flat_rows.append([(c or "").strip() for c in first_r])
            continue

        col1_val = first_r[1] or ""
        col2_val = first_r[2] or ""

        col1_splits = [s.strip() for s in col1_val.split("\n") if s.strip()]
        col2_splits = [s.strip() for s in col2_val.split("\n") if s.strip()]

        n = max(len(col1_splits), len(col2_splits), len(block), 1)

        # B. Single Row with automatic colspan
        if n == 1:
            row_html, _ = _auto_detect_row_cells_html(first_r, is_th=False, is_summary=False)
            html_rows.append(f"      <tr>{row_html}</tr>")

            clean_r_md = [(c or "").strip().replace("\n", " ").replace("|", "/") for c in first_r]
            md_rows.append("| " + " | ".join(clean_r_md) + " |")
            flat_rows.append([(c or "").strip() for c in first_r])
            continue

        # C. Multi-level Sub-row Splitting with Rowspan & Colspan
        col0_val = (first_r[0] or "").strip()
        split_data = {}
        for c_i in range(1, num_cols):
            vert_vals = [block[r_i][c_i] for r_i in range(len(block)) if block[r_i][c_i] is not None and str(block[r_i][c_i]).strip() != ""]
            if len(vert_vals) == n:
                split_data[c_i] = [(v or "").strip() for v in vert_vals]
            elif len(block) > 1 and len(vert_vals) > 1:
                parts = []
                for sub_i in range(n):
                    if sub_i < len(block) and block[sub_i][c_i] is not None:
                        parts.append(str(block[sub_i][c_i]).strip())
                    else:
                        parts.append("")
                split_data[c_i] = parts
            else:
                raw_c = first_r[c_i] or ""
                split_data[c_i] = _split_multiline_cell_content(raw_c, n, is_count_col=(c_i == 2))

        for sub_k in range(n):
            sub_html = []
            sub_md = []
            flat_sub = [col0_val.replace("\n", " ")]

            if sub_k == 0:
                c0_html = col0_val.replace("\n", "<br/>")
                sub_html.append(f'<td rowspan="{n}" class="merged-header-cell"><b>{c0_html}</b></td>')
            sub_md.append(col0_val.replace("\n", " "))

            for c_i in range(1, num_cols):
                val = split_data[c_i][sub_k] if sub_k < len(split_data[c_i]) else ""
                val_html = val.replace("\n", "<br/>")
                val_md = val.replace("\n", " ").replace("|", "/")
                sub_html.append(f"<td>{val_html}</td>")
                sub_md.append(val_md)
                flat_sub.append(val)

            html_rows.append(f"      <tr>{''.join(sub_html)}</tr>")
            md_rows.append("| " + " | ".join(sub_md) + " |")
            flat_rows.append(flat_sub)

    html_rows.append("    </tbody>")

    table_html = (
        '<div class="table-container">\n'
        '  <table class="styled-table">\n'
        + "\n".join(html_rows)
        + '\n  </table>\n</div>'
    )
    table_md = "\n".join(md_rows)
    return table_html, table_md, flat_rows


# PDF 문서 to HTML 웹 문서 and 마크다운 데이터를 대상 포맷으로 변환함
def _convert_pdf_to_html_and_markdown(input_path: Path) -> tuple[str, str]:
    """
    Convert PDF document to high-fidelity responsive HTML body and Markdown,
    extracting 2D tables with automatic hierarchical row/cell splitting using pdfplumber with pypdf fallback.
    """
    html_blocks: List[str] = []
    md_blocks: List[str] = []

    try:
        import pdfplumber

        with pdfplumber.open(str(input_path.resolve())) as pdf:
            total_pages = len(pdf.pages)
            for p_idx, page in enumerate(pdf.pages):
                page_num = p_idx + 1
                page_html_parts: List[str] = []
                page_md_parts: List[str] = []

                page_html_parts.append(f'<div class="pdf-page-card" id="page-{page_num}">')
                page_html_parts.append(f'  <div class="pdf-page-badge">Page {page_num} / {total_pages}</div>')
                page_md_parts.append(f"## Page {page_num}\n")

                raw_candidates = page.find_tables()
                tables = []
                for t in raw_candidates:
                    raw_data = t.extract() or []
                    if len(raw_data) < 2:
                        continue
                    cols = [len([c for c in r if c and str(c).strip()]) for r in raw_data]
                    if not cols or max(cols) < 2:
                        continue
                    w = t.bbox[2] - t.bbox[0]
                    h = t.bbox[3] - t.bbox[1]
                    if w < 60 or (h > 400 and w < 120):
                        continue
                    tables.append(t)

                if not tables:
                    txt = page.extract_text() or ""
                    if txt.strip():
                        for para in txt.split("\n\n"):
                            p_clean = para.strip()
                            if p_clean:
                                page_html_parts.append(f"  <p>{p_clean.replace(chr(10), '<br/>')}</p>")
                                page_md_parts.append(f"{p_clean}\n")
                else:
                    table_bboxes = [t.bbox for t in tables]

                    # not within 표(테이블) 작업을 수행함
                    def not_within_table(obj):
                        """표 내부에 중첩된 태그를 제외함"""
                        top = obj.get("top", 0)
                        bottom = obj.get("bottom", 0)
                        x0 = obj.get("x0", 0)
                        x1 = obj.get("x1", 0)
                        for bx0, btop, bx1, bbottom in table_bboxes:
                            if not (x1 < bx0 or x0 > bx1 or bottom < btop or top > bbottom):
                                return False
                        return True

                    try:
                        filtered_page = page.filter(not_within_table)
                        outside_text = filtered_page.extract_text() or ""
                    except Exception:
                        outside_text = page.extract_text() or ""

                    if outside_text.strip():
                        for para in outside_text.split("\n\n"):
                            p_clean = para.strip()
                            if p_clean:
                                page_html_parts.append(f"  <p>{p_clean.replace(chr(10), '<br/>')}</p>")
                                page_md_parts.append(f"{p_clean}\n")

                    for t in tables:
                        raw_tbl = t.extract()
                        if not raw_tbl:
                            continue
                        tbl_html, tbl_md, _ = _format_hierarchical_table_to_html_and_md(raw_tbl)
                        if tbl_html:
                            page_html_parts.append(tbl_html)
                        if tbl_md:
                            page_md_parts.append("\n" + tbl_md + "\n")

                page_html_parts.append("</div>\n")
                html_blocks.append("\n".join(page_html_parts))
                md_blocks.append("\n".join(page_md_parts))

        if html_blocks:
            return "\n".join(html_blocks), "\n\n---\n\n".join(md_blocks).strip()
    except Exception:
        pass

    # Fallback to pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(str(input_path.resolve()))
        html_blocks = []
        md_blocks = []
        for idx, page in enumerate(reader.pages):
            p_num = idx + 1
            text = page.extract_text() or ""
            if text.strip():
                p_html = [f'<div class="pdf-page-card" id="page-{p_num}">']
                p_html.append(f'  <div class="pdf-page-badge">Page {p_num}</div>')
                for para in text.split("\n\n"):
                    p_clean = para.strip()
                    if p_clean:
                        p_html.append(f"  <p>{p_clean.replace(chr(10), '<br/>')}</p>")
                p_html.append("</div>\n")
                html_blocks.append("\n".join(p_html))
                md_blocks.append(f"## Page {p_num}\n\n{text.strip()}\n")

        if html_blocks:
            return "\n".join(html_blocks), "\n\n---\n\n".join(md_blocks).strip()
    except Exception:
        pass

    return "<p>PDF에서 텍스트를 추출할 수 없습니다 (스캔 이미지 또는 암호화된 PDF일 수 있습니다).</p>", "PDF에서 텍스트를 추출할 수 없습니다."


# PDF 문서 to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_pdf_to_html(input_path: Path, output_path: Optional[Path] = None) -> str:
    """Convert PDF file to high-fidelity responsive HTML (95%+ visual match)."""
    try:
        from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_html
        html_content = convert_pdf_to_high_fidelity_html(input_path, title=input_path.stem)
        if output_path is not None:
            output_path.write_text(html_content, encoding="utf-8")
        return html_content
    except Exception as exc:
        logging.warning("High-fidelity PDF HTML conversion failed; using fallback: %s", exc)
        body, _ = _convert_pdf_to_html_and_markdown(input_path)
        if output_path is not None:
            full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
            output_path.write_text(full_html, encoding="utf-8")
        return body


# PDF 문서 to 마크다운 데이터를 대상 포맷으로 변환함
def _convert_pdf_to_markdown(input_path: Path) -> str:
    """Convert PDF file to structured Markdown."""
    try:
        from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_markdown
        return convert_pdf_to_high_fidelity_markdown(input_path)
    except Exception as exc:
        logging.warning("High-fidelity PDF Markdown conversion failed; using fallback: %s", exc)
        _, md = _convert_pdf_to_html_and_markdown(input_path)
        return md


# 이미지 with ir 데이터를 대상 포맷으로 변환함
def _convert_image_with_ir(input_path: Path, target_format: str) -> str:
    """Convert image input through the IR OCR parser and return text output."""
    from synthetic_engine.document_conversion.pipeline import convert_document

    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=settings.OUTPUT_DIR) as tmp:
        output = convert_document(input_path, target_format, output_dir=Path(tmp))
        return output.read_text(encoding="utf-8", errors="ignore")


# 이미지 to 마크다운 데이터를 대상 포맷으로 변환함
def _convert_image_to_markdown(input_path: Path) -> str:
    return _convert_image_with_ir(input_path, "md")


# 이미지 to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_image_to_html(input_path: Path) -> str:
    return _convert_image_with_ir(input_path, "html")


# 워드 문서 텍스트 데이터를 정제 및 정리함
def _clean_doc_text(value: Any) -> str:
    """문서에서 추출한 값을 미리보기용 문자열로 정리함"""
    text = sanitize_hancom_text(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


# document soup 객체 또는 요소를 생성함
def _make_document_soup(html_content: str) -> Any:
    """HTML 문서를 미리보기 분석을 위한 BeautifulSoup 객체로 생성함"""
    from bs4 import BeautifulSoup

    for parser in ("lxml", "html5lib", "html.parser"):
        try:
            return BeautifulSoup(html_content or "", parser)
        except Exception:
            continue
    return BeautifulSoup(html_content or "", "html.parser")


# structured 표 목록 요소를 추출하여 반환함
def _extract_structured_tables(soup: Any, max_preview_rows: int = 20) -> List[Dict[str, Any]]:
    """HTML 문서의 표 구조와 미리보기 행을 추출함"""
    tables: List[Dict[str, Any]] = []
    for table_index, table in enumerate(soup.find_all("table"), start=1):
        if table.find_parent("table") is not None:
            continue

        logical_cells: List[Dict[str, Any]] = []
        occupied: set[tuple[int, int]] = set()
        row_count = 0
        max_cols = 0
        warnings: List[str] = []
        table_rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
        for row_index, tr in enumerate(table_rows):
            row_count = row_index + 1
            column_index = 0
            for cell in tr.find_all(["th", "td"], recursive=False):
                try:
                    colspan = max(1, int(cell.get("colspan", 1) or 1))
                    rowspan = max(1, int(cell.get("rowspan", 1) or 1))
                except Exception:
                    colspan = rowspan = 1
                while (row_index, column_index) in occupied:
                    column_index += 1
                try:
                    source_column = int(cell.get("data-col", column_index))
                except (TypeError, ValueError):
                    source_column = column_index
                column_index = max(column_index, source_column)
                text = _clean_doc_text(cell.get_text(" ", strip=True)).replace("|", "/")
                collision = False
                for covered_row in range(row_index, row_index + rowspan):
                    for covered_col in range(column_index, column_index + colspan):
                        if (covered_row, covered_col) in occupied:
                            collision = True
                        occupied.add((covered_row, covered_col))
                if collision:
                    warnings.append(f"{row_index + 1}행 {column_index + 1}열 병합 범위 충돌")
                logical_cells.append({
                    "row": row_index,
                    "col": column_index,
                    "rowspan": rowspan,
                    "colspan": colspan,
                    "text": text,
                    "confidence": 0.5 if collision else 1.0,
                })
                max_cols = max(max_cols, column_index + colspan)
                row_count = max(row_count, row_index + rowspan)
                column_index += colspan

        if logical_cells:
            normalized = [["" for _ in range(max_cols)] for _ in range(row_count)]
            for cell in logical_cells:
                normalized[cell["row"]][cell["col"]] = cell["text"]
            tables.append({
                "index": table_index,
                "rows": row_count,
                "columns": max_cols,
                "header": normalized[0] if normalized else [],
                "preview": normalized[:max_preview_rows],
                "cells": logical_cells,
                "confidence": 0.5 if warnings else 1.0,
                "warnings": warnings,
            })
    return tables


# structured 블록 목록 from HTML 웹 문서 요소를 추출하여 반환함
def _extract_structured_blocks_from_html(body_html: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """HTML 본문에서 문단·표 블록과 페이지 수를 추출함"""
    soup = _make_document_soup(body_html)
    root = soup.find("body") or soup
    tables = _extract_structured_tables(root)
    blocks: List[Dict[str, Any]] = []
    image_count = len(root.find_all("img"))
    seen_tables = set()

    for el in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre", "table", "img"]):
        if el.find_parent("table") is not None and el.name != "table":
            continue
        if el.name == "table":
            if el.find_parent("table") is not None:
                continue
            marker = id(el)
            if marker in seen_tables:
                continue
            seen_tables.add(marker)
            table_no = len([b for b in blocks if b["type"] == "table"]) + 1
            blocks.append({"type": "table", "table_index": table_no})
            continue
        if el.name == "img":
            src = el.get("src", "")
            blocks.append({"type": "image", "alt": el.get("alt", ""), "embedded": src.startswith("data:")})
            continue

        text = _clean_doc_text(el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name and re.fullmatch(r"h[1-6]", el.name):
            block_type = "heading"
            level = int(el.name[1])
        elif el.name == "blockquote":
            block_type = "quote"
            level = None
        elif el.name == "pre":
            block_type = "code"
            level = None
        else:
            block_type = "paragraph"
            level = None
        block: Dict[str, Any] = {"type": block_type, "text": text[:2000]}
        if level is not None:
            block["level"] = level
        blocks.append(block)

    return blocks[:300], tables, image_count


# wrap 마크다운 as HTML 웹 문서 작업을 수행함
def _wrap_markdown_as_html(title: str, markdown_text: str, filename: str) -> str:
    """Markdown 결과를 브라우저 미리보기용 HTML 문서로 감쌈"""
    try:
        import markdown
        body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "nl2br", "sane_lists"])
    except Exception:
        body = "<pre>" + html_lib.escape(markdown_text) + "</pre>"
    return _wrap_html_page(title, body, filename, is_table=False)


# structured document parse 구조를 생성 및 조립함
def _build_structured_document_parse(src_path: Path, raw_ext: str, original_filename: str = "") -> Dict[str, Any]:
    """
    Parse document formats into one reusable structure for preview, Markdown, and metadata.
    High-fidelity HTML is preserved when available; Markdown/blocks/tables are normalized for downstream export.
    """
    body_html = ""
    html_preview = ""
    markdown_text = ""
    parser_engines: List[str] = []
    fidelity_level = "best_effort"

    if raw_ext == ".pdf":
        parser_engines = ["PyMuPDF visual layout", "pdfplumber tables", "pypdf fallback"]
        try:
            from synthetic_engine.exporters.pdf_high_fidelity_converter import (
                convert_pdf_to_high_fidelity_html,
                convert_pdf_to_high_fidelity_markdown,
            )
            html_preview = convert_pdf_to_high_fidelity_html(src_path, title=src_path.stem)
            markdown_text = convert_pdf_to_high_fidelity_markdown(src_path)
            body_html = html_preview
            fidelity_level = "high"
        except Exception:
            body_html, markdown_text = _convert_pdf_to_html_and_markdown(src_path)
            html_preview = _wrap_html_page(src_path.stem, body_html, original_filename or src_path.name, is_table=False)
    elif raw_ext == ".hwp":
        parser_engines = ["Hancom COM when available", "pyhwp hwp5html", "pyhwp hwp5txt fallback"]
        body_html, markdown_text = _convert_hwp_to_html_and_markdown(src_path)
        html_preview = _wrap_html_page(src_path.stem, body_html, original_filename or src_path.name, is_table=False)
        fidelity_level = "high" if "<table" in body_html or len(markdown_text) > 40 else "best_effort"
    elif raw_ext == ".hwpx":
        parser_engines = ["OWPML XML", "python-hwpx compatible package", "embedded BinData extraction"]
        body_html, markdown_text = _convert_hwpx_to_html_and_markdown(src_path)
        html_preview = _wrap_html_page(src_path.stem, body_html, original_filename or src_path.name, is_table=False)
        fidelity_level = "high" if "<table" in body_html or len(markdown_text) > 40 else "best_effort"
    elif raw_ext in (".docx", ".doc"):
        parser_engines = ["mammoth HTML", "python-docx tables", "Word COM fallback"]
        markdown_text = _convert_docx_to_markdown(src_path)
        body_html = _convert_docx_to_html(src_path)
        html_preview = _wrap_html_page(src_path.stem, body_html, original_filename or src_path.name, is_table=False)
        fidelity_level = "high"
    elif raw_ext == ".md":
        parser_engines = ["Python-Markdown", "BeautifulSoup"]
        markdown_text = src_path.read_text(encoding="utf-8", errors="ignore")
        html_preview = _wrap_markdown_as_html(src_path.stem, markdown_text, original_filename or src_path.name)
        body_html = html_preview
        fidelity_level = "high"
    ocr_confidence = None
    if raw_ext in IMAGE_SOURCES:
        parser_engines = ["ImageParser", "OpenCV table detector", "local OCR backend"]
        from synthetic_engine.document_conversion.registry import parse_document, renderer_for
        doc = parse_document(src_path)
        raw_conf = doc.metadata.custom.get("ocr_mean_confidence")
        if raw_conf:
            try:
                ocr_confidence = float(raw_conf)
            except (TypeError, ValueError):
                ocr_confidence = None
        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=settings.OUTPUT_DIR) as tmp:
            tmp_md = Path(tmp) / f"{src_path.stem}.md"
            tmp_html = Path(tmp) / f"{src_path.stem}.html"
            renderer_for("md").render(doc, tmp_md)
            renderer_for("html").render(doc, tmp_html)
            markdown_text = tmp_md.read_text(encoding="utf-8", errors="ignore")
            html_preview = tmp_html.read_text(encoding="utf-8", errors="ignore")
        body_html = html_preview
        fidelity_level = "ocr"
    elif raw_ext in {".pdf", ".hwp", ".hwpx", ".docx", ".doc", ".md"}:
        # Other formats processed above
        pass
    else:
        raise ValueError(f"지원하지 않는 문서 형식입니다: {raw_ext}")

    blocks, tables, image_count = _extract_structured_blocks_from_html(body_html or html_preview)
    plain_text = "\n".join(block.get("text", "") for block in blocks if block.get("text")).strip()
    if not plain_text and markdown_text:
        plain_text = re.sub(r"[#>*`|_-]+", " ", markdown_text)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()

    structure = {
        "format": raw_ext.replace(".", "").upper(),
        "parser_engines": parser_engines,
        "fidelity_level": fidelity_level,
        "fidelity_target": "95%+ visual structure preservation when source contains extractable layout data",
        "pages_count": max(1, len(re.findall(r'class=["\'][^"\']*pdf-page-card', html_preview or ""))) if raw_ext == ".pdf" else 1,
        "block_count": len(blocks),
        "table_count": len(tables),
        "image_count": image_count,
        "text_length": len(markdown_text or plain_text),
        "blocks": blocks,
        "tables": tables,
    }
    from synthetic_api.application.services.conversion_quality import assess_parse_quality, build_ocr_quality_summary
    structure['quality'] = assess_parse_quality(src_path, plain_text, ocr_confidence=ocr_confidence)
    if structure['quality']['source_pages_count'] is not None:
        structure['pages_count'] = structure['quality']['source_pages_count']
    ocr_quality = build_ocr_quality_summary(
        src_path,
        html_preview=html_preview,
        tables=tables,
        pages_count=structure['pages_count'],
        base_quality=structure['quality'],
        ocr_confidence=ocr_confidence,
    )
    structure['quality'].update({
        'ocr_status': ocr_quality['ocr_status'],
        'ocr_engine': ocr_quality['ocr_engine'],
        'average_confidence': ocr_quality['average_confidence'],
        'low_confidence_regions': ocr_quality['low_confidence_regions'],
        'page_progress': ocr_quality['page_progress'],
        'warnings': ocr_quality['warnings'],
        'requires_review': ocr_quality['requires_review'],
    })

    return {
        "body_html": body_html,
        "html_preview": html_preview,
        "markdown": markdown_text,
        "plain_text": plain_text,
        "structure": structure,
    }


# ensure meaningful document parse 작업을 수행함
def _ensure_meaningful_document_parse(doc_parse: Dict[str, Any]) -> None:
    structure = doc_parse.get("structure") or {}
    has_text = bool((doc_parse.get("plain_text") or "").strip() or (doc_parse.get("markdown") or "").strip())
    has_tables = int(structure.get("table_count") or 0) > 0
    has_images = int(structure.get("image_count") or 0) > 0
    if not (has_text or has_tables or has_images):
        raise ConversionError(
            status_code=422,
            detail="문서에서 변환 가능한 텍스트, 표, 이미지를 찾지 못했습니다. 스캔 품질 또는 파일 내용을 확인하세요.",
        )


# document delivery state 작업을 수행함
def _document_delivery_state(document_structure: Dict[str, Any]) -> tuple[str, bool]:
    """Prevent unverified OCR output from being presented as production-ready."""
    quality = (document_structure or {}).get("quality") or {}
    requires_review = bool(quality.get("requires_review"))
    ocr_status = str(quality.get("ocr_status") or "").lower()
    if requires_review or ocr_status in {"review_required", "failed"}:
        return "review_required", False
    return "success", True


# ensure downloadable output 작업을 수행함
def _ensure_downloadable_output(path: Path, label: str) -> None:
    if not path.exists():
        raise ConversionError(status_code=500, detail=f"{label} 출력 파일이 생성되지 않았습니다.")
    if path.stat().st_size <= 0:
        raise ConversionError(status_code=422, detail=f"{label} 출력 파일이 비어 있어 다운로드를 차단했습니다.")


# 마크다운 to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_markdown_to_html(input_path: Path) -> str:
    """Convert Markdown file to styled HTML body."""
    try:
        md_text = input_path.read_text(encoding="utf-8", errors="ignore")
        import markdown
        return markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
        )
    except Exception:
        md_text = input_path.read_text(encoding="utf-8", errors="ignore")
        lines = []
        for line in md_text.splitlines():
            if line.startswith("# "):
                lines.append(f"<h1>{line[2:].strip()}</h1>")
            elif line.startswith("## "):
                lines.append(f"<h2>{line[3:].strip()}</h2>")
            elif line.startswith("### "):
                lines.append(f"<h3>{line[4:].strip()}</h3>")
            elif line.strip():
                lines.append(f"<p>{line.strip()}</p>")
        return "\n".join(lines)


# dataframe to 마크다운 작업을 수행함
def _dataframe_to_markdown(df, limit: int = 500) -> str:
    """Convert dataframe to GitHub Flavored Markdown table with safe pure-python fallback."""
    sample = df.head(limit)
    try:
        import tabulate  # noqa: F401
        return sample.to_markdown(index=False)
    except Exception:
        # Resilient pure-Python GFM markdown table generator
        cols = [str(c) for c in sample.columns]
        header_row = "| " + " | ".join(cols) + " |"
        sep_row = "| " + " | ".join(["---"] * len(cols)) + " |"
        rows = []
        for _, row in sample.iterrows():
            cells = [
                str(v if v is not None and not (isinstance(v, float) and v != v) else "")
                .replace("\r", "")
                .replace("\n", " ")
                .replace("|", "\\|")
                for v in row
            ]
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header_row, sep_row] + rows)


# dataframe to sql insert 작업을 수행함
def _dataframe_to_sql_insert(df: pd.DataFrame, table_name: str = "converted_data", limit: int = 50000) -> str:
    """Generate clean SQL INSERT statements for any DataFrame with safe value escaping."""
    export_df = df.head(limit)
    cols = [f"`{str(c).strip().replace('`', '')}`" for c in export_df.columns]
    col_str = ", ".join(cols)

    safe_table = table_name.strip().replace("`", "").replace(";", "").replace("'", "")
    if not safe_table:
        safe_table = "converted_data"

    lines = [
        f"-- ========================================================",
        f"-- Generated by SynthDataGenerator Universal SQL Exporter",
        f"-- Target Table: `{safe_table}`",
        f"-- Exported Rows: {len(export_df):,} / Total: {len(df):,}",
        f"-- Exported At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- ========================================================",
        ""
    ]

    batch_size = 500
    for i in range(0, len(export_df), batch_size):
        chunk = export_df.iloc[i : i + batch_size]
        val_rows = []
        for _, row in chunk.iterrows():
            row_vals = []
            for val in row:
                if pd.isna(val) or val is None:
                    row_vals.append("NULL")
                elif isinstance(val, (bool, np.bool_)):
                    row_vals.append("TRUE" if val else "FALSE")
                elif isinstance(val, (int, np.integer)):
                    row_vals.append(str(val))
                elif isinstance(val, (float, np.floating)):
                    if np.isinf(val) or np.isnan(val):
                        row_vals.append("NULL")
                    else:
                        row_vals.append(str(val))
                else:
                    clean_str = str(val).replace("\\", "\\\\").replace("'", "''")
                    row_vals.append(f"'{clean_str}'")
            val_rows.append(f"  ({', '.join(row_vals)})")

        if val_rows:
            insert_stmt = f"INSERT INTO `{safe_table}` ({col_str}) VALUES\n" + ",\n".join(val_rows) + ";"
            lines.append(insert_stmt)
            lines.append("")

    return "\n".join(lines)


# xml local name 작업을 수행함
def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# read xml 표(테이블) 작업을 수행함
def _read_xml_table(path: Path) -> pd.DataFrame:
    data = path.read_bytes()
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD 또는 외부 엔터티가 포함된 XML은 지원하지 않습니다.")
    root = ET.fromstring(data)
    nodes = list(root.iter())
    if len(nodes) > 1_000_000:
        raise ValueError("XML 노드 수가 허용 범위를 초과했습니다.")
    children = list(root)
    records = children if children and len({_xml_local_name(c.tag) for c in children}) == 1 else [root]

    # flatten 작업을 수행함
    def flatten(element: ET.Element, prefix: str = "") -> Dict[str, Any]:
        field_children = [child for child in element if _xml_local_name(child.tag) == "field" and child.attrib.get("name")]
        if field_children and len(field_children) == len(list(element)):
            return {
                child.attrib["name"]: (child.text or "").strip()
                for child in field_children
            }
        row: Dict[str, Any] = {f"{prefix}@{_xml_local_name(k)}": v for k, v in element.attrib.items()}
        grouped: Dict[str, List[ET.Element]] = {}
        for child in element:
            grouped.setdefault(_xml_local_name(child.tag), []).append(child)
        for name, values in grouped.items():
            key = f"{prefix}{name}"
            if all(not list(value) for value in values):
                row[key] = " | ".join((value.text or "").strip() for value in values)
            else:
                for index, value in enumerate(values):
                    suffix = f"[{index}]." if len(values) > 1 else "."
                    row.update(flatten(value, key + suffix))
        if not grouped and prefix:
            row[prefix.rstrip(".")] = (element.text or "").strip()
        return row

    return pd.DataFrame([flatten(record) for record in records])


# xml 표(테이블) 데이터를 파일에 기록함
def _write_xml_table(df: pd.DataFrame, path: Path) -> None:
    root = ET.Element("records")
    for values in df.astype(object).where(pd.notna(df), None).to_dict(orient="records"):
        record = ET.SubElement(root, "record")
        for column, value in values.items():
            field = ET.SubElement(record, "field", {"name": str(column)})
            field.text = "" if value is None else str(value)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


# wrap HTML 웹 문서 페이지 작업을 수행함
def _wrap_html_page(title: str, body_html: str, filename: str, is_table: bool = False) -> str:
    """HTML 본문에 공통 문서 미리보기 레이아웃을 적용함"""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table_search_block = """
    <div style="margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.75rem;">
      <input type="text" id="tableFilter" onkeyup="filterTable()" placeholder="표 내용 실시간 검색..." style="padding: 0.5rem 0.85rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--card-bg); color: var(--text-main); width: 280px; font-size: 0.875rem;">
      <span id="rowCount" style="font-size: 0.85rem; color: var(--text-sub);"></span>
    </div>
    <script>
      function filterTable() {
        const input = document.getElementById("tableFilter");
        const filter = input.value.toLowerCase();
        const table = document.querySelector("table");
        if (!table) return;
        const rows = table.querySelectorAll("tbody tr");
        let visibleCount = 0;
        rows.forEach(r => {
          const match = r.textContent.toLowerCase().includes(filter);
          r.style.display = match ? "" : "none";
          if (match) visibleCount++;
        });
        const cntElem = document.getElementById("rowCount");
        if (cntElem) {
          cntElem.textContent = filter ? `${visibleCount} / ${rows.length}행 표시 중` : `${rows.length}행`;
        }
      }
      document.addEventListener("DOMContentLoaded", () => {
        const table = document.querySelector("table");
        if (table) {
          const cntElem = document.getElementById("rowCount");
          const rows = table.querySelectorAll("tbody tr");
          if (cntElem) cntElem.textContent = `총 ${rows.length}행`;
        }
      });
    </script>
    """ if is_table else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg-color: #f8fafc;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-sub: #64748b;
      --border-color: #e2e8f0;
      --primary: #2563eb;
      --table-stripe: #f8fafc;
      --table-hover: #f1f5f9;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg-color: #0b0f17;
        --card-bg: #131b2e;
        --text-main: #f1f5f9;
        --text-sub: #94a3b8;
        --border-color: #1e293b;
        --primary: #3b82f6;
        --table-stripe: #172138;
        --table-hover: #1f2d4d;
      }}
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Pretendard", sans-serif;
      background-color: var(--bg-color);
      color: var(--text-main);
      line-height: 1.65;
      padding: 2.5rem 1.5rem;
    }}
    .container {{
      max-width: 1040px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 2.5rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }}
    .doc-header {{
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 1.25rem;
      margin-bottom: 2rem;
    }}
    .doc-title {{ font-size: 1.5rem; font-weight: 700; }}
    .doc-meta {{ font-size: 0.875rem; color: var(--text-sub); margin-top: 0.35rem; }}
    h1, h2, h3, h4, h5, h6 {{ margin-top: 1.75rem; margin-bottom: 0.75rem; font-weight: 600; line-height: 1.3; }}
    h1 {{ font-size: 1.875rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.25rem; }}
    p {{ margin-bottom: 1rem; }}
    ul, ol {{ margin-bottom: 1.25rem; padding-left: 1.75rem; }}
    li {{ margin-bottom: 0.4rem; }}
    .table-container {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin: 1.25rem 0;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 0;
      font-size: 0.9rem;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    tr, th, td {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    th, td {{
      border: 1px solid var(--border-color);
      padding: 0.65rem 0.9rem;
      text-align: left;
      vertical-align: middle;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: normal;
    }}
    th {{
      background-color: var(--table-stripe);
      font-weight: 700;
      text-align: center;
    }}
    tr:nth-child(even) td {{
      background-color: var(--table-stripe);
    }}
    .hwpx-table tr:nth-child(even) td {{
      background-color: transparent;
    }}
    tr:hover td {{
      background-color: var(--table-hover);
    }}
    .merged-header-cell {{
      background-color: var(--table-stripe) !important;
      vertical-align: middle !important;
      text-align: center !important;
      font-weight: 700 !important;
      color: var(--text-main);
      border: 1px solid var(--border-color) !important;
    }}
    .merged-colspan-cell {{
      text-align: center;
      vertical-align: middle;
      font-weight: 600;
    }}
    .table-summary-row {{
      background-color: var(--table-hover) !important;
      font-weight: 700;
      border-top: 2px solid var(--primary);
      border-bottom: 2px solid var(--primary);
    }}
    .table-summary-row td, .table-summary-cell {{
      background-color: var(--table-hover) !important;
      font-weight: 700;
      text-align: center;
      color: var(--primary);
    }}
    pre, code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.875rem;
    }}
    code {{
      background: var(--table-stripe);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      border: 1px solid var(--border-color);
    }}
    pre code {{
      border: none;
      padding: 0;
    }}
    pre {{
      background: var(--table-stripe);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      overflow-x: auto;
      margin: 1.25rem 0;
    }}
    blockquote {{
      border-left: 4px solid var(--primary);
      padding-left: 1rem;
      color: var(--text-sub);
      margin: 1.25rem 0;
    }}
    hr {{
      border: none;
      border-top: 1px solid var(--border-color);
      margin: 2rem 0;
    }}
    .pdf-page-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1.75rem 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      position: relative;
    }}
    .pdf-page-badge {{
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--primary);
      background: var(--table-stripe);
      border: 1px solid var(--border-color);
      padding: 0.2rem 0.65rem;
      border-radius: 9999px;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="doc-header">
      <div class="doc-title">{title}</div>
      <div class="doc-meta">생성 일시: {created_at} | 원본 파일: {filename}</div>
    </div>
    {table_search_block}
    <div class="doc-body">
      {body_html}
    </div>
  </div>
  <script>
  window.addEventListener('message', function(e) {{
    if (e.data && e.data.type === 'scrollToPage') {{
      var pno = e.data.page;
      var el = document.getElementById('page-' + pno) || document.getElementById('preview-page-' + pno);
      if (el) {{
        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }}
  }});
  </script>
</body>
</html>
"""


# 워드(DOCX) to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_docx_to_html(input_path: Path) -> str:
    """Convert DOCX to clean HTML while preserving paragraph/table order."""
    try:
        from synthetic_engine.exporters.document_exporter import convert_word_to_html
        return convert_word_to_html(input_path)
    except Exception:
        try:
            import mammoth
            with open(input_path, "rb") as docx_file:
                res = mammoth.convert_to_html(docx_file)
                return res.value
        except Exception:
            md = _convert_docx_to_markdown(input_path)
            try:
                import markdown
                return markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
            except Exception:
                return f"<pre>{html_lib.escape(md)}</pre>"


# word to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_word_to_html(input_path: Path, output_path: Path) -> None:
    """Convert Word DOC/DOCX to HTML."""
    if input_path.suffix.lower() == ".docx":
        body = _convert_docx_to_html(input_path)
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")
        return

    # For legacy .doc: Use Word COM if possible, else text fallback
    try:
        with win32_com_session("Word.Application") as word:
            word.Visible = False
            doc = word.Documents.Open(str(input_path.resolve()))
            doc.SaveAs(str(output_path.resolve()), FileFormat=8)  # 8 = wdFormatHTML
    except Exception:
        md = _convert_docx_to_markdown(input_path)
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")


# 한글(HWP) to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_hwp_to_html(input_path: Path, output_path: Path) -> None:
    """Convert HWP to rich HTML web document with complete table preservation."""
    body, _ = _convert_hwp_to_html_and_markdown(input_path)
    full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
    output_path.write_text(full_html, encoding="utf-8")


# 한글 표준(HWPX) to HTML 웹 문서 데이터를 대상 포맷으로 변환함
def _convert_hwpx_to_html(input_path: Path, output_path: Path) -> None:
    """Convert HWPX to rich HTML web document with complete table preservation."""
    body, _ = _convert_hwpx_to_html_and_markdown(input_path)
    full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
    output_path.write_text(full_html, encoding="utf-8")


# HTML 웹 문서 to PDF 문서 데이터를 타깃 포맷으로 렌더링함
def _render_html_to_pdf(html_body: str, output_path: Path, title: str = "문서") -> None:
    """Render HTML body into a print-ready A4 PDF with 100% open-source multi-engine fallbacks."""
    import tempfile
    import subprocess

    print_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
  size: A4 portrait;
  margin: 18mm 14mm 18mm 14mm;
  @bottom-right {{
    content: counter(page) " / " counter(pages);
    font-size: 8pt;
    color: #64748b;
  }}
}}
body {{
  font-family: 'NanumGothic', 'Noto Sans CJK KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
  color: #1e293b;
  line-height: 1.6;
  font-size: 9.5pt;
}}
h1 {{ font-size: 16pt; margin-bottom: 10pt; color: #0f172a; border-bottom: 2px solid #2563eb; padding-bottom: 4pt; }}
h2 {{ font-size: 13pt; margin-top: 12pt; margin-bottom: 6pt; color: #1e40af; }}
h3 {{ font-size: 11pt; margin-top: 10pt; margin-bottom: 4pt; color: #334155; }}
p {{ margin-bottom: 6pt; text-align: justify; word-break: keep-all; }}
.table-container {{ margin: 8pt 0; width: 100%; }}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 6pt 0;
  page-break-inside: auto;
  font-size: 8.5pt;
}}
tr {{
  page-break-inside: avoid;
  page-break-after: auto;
}}
th, td {{
  border: 1px solid #475569;
  padding: 5pt 7pt;
  text-align: left;
  vertical-align: middle;
}}
th {{
  background-color: #f1f5f9;
  font-weight: bold;
  color: #0f172a;
  text-align: center;
}}
.merged-header-cell {{
  background-color: #f8fafc !important;
  vertical-align: middle !important;
  text-align: center !important;
  font-weight: bold !important;
}}
.merged-colspan-cell {{
  text-align: center;
  vertical-align: middle;
  font-weight: bold;
}}
.table-summary-row {{
  background-color: #f1f5f9 !important;
  font-weight: bold;
  border-top: 2px solid #2563eb;
  border-bottom: 2px solid #2563eb;
}}
.table-summary-row td, .table-summary-cell {{
  background-color: #f1f5f9 !important;
  font-weight: bold;
  text-align: center;
  color: #1e40af;
}}
ul, ol {{ margin-bottom: 8pt; padding-left: 18pt; }}
li {{ margin-bottom: 3pt; }}
</style>
</head>
<body>
  {html_body}
</body>
</html>"""

    # 1. WeasyPrint (Standard for Linux / Docker container)
    try:
        import weasyprint
        weasyprint.HTML(string=print_html).write_pdf(str(output_path))
        if output_path.exists() and output_path.stat().st_size > 0:
            return
    except Exception:
        pass

    # 2. Chrome / Edge / Chromium headless CLI (Native on Windows, Linux, Mac)
    try:
        import shutil
        candidate_bins = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
        ]
        browser_bin = next((str(p) for p in candidate_bins if (isinstance(p, Path) and p.exists()) or (isinstance(p, str) and Path(p).exists())), None)
        if not browser_bin:
            browser_bin = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")

        if browser_bin:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_html = Path(tmpdir) / "print_doc.html"
                tmp_html.write_text(print_html, encoding="utf-8")
                cmd = [
                    str(browser_bin),
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    f"--print-to-pdf={output_path.resolve()}",
                    str(tmp_html.resolve())
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)
                if output_path.exists() and output_path.stat().st_size > 0:
                    return
    except Exception:
        pass

    # 3. Playwright / Chromium headless (if available)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(print_html, wait_until="networkidle")
            page.pdf(path=str(output_path), format="A4", print_background=True, margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
            browser.close()
            if output_path.exists() and output_path.stat().st_size > 0:
                return
    except Exception:
        pass

    # 3. LibreOffice headless via temp HTML
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_html = Path(tmpdir) / "print_doc.html"
            tmp_html.write_text(print_html, encoding="utf-8")
            cmd = ["soffice", "--headless", "--convert-to", "pdf", str(tmp_html.resolve()), "--outdir", str(output_path.parent.resolve())]
            subprocess.run(cmd, capture_output=True, timeout=30)
            default_out = output_path.parent / "print_doc.pdf"
            if default_out.exists():
                default_out.rename(output_path)
                return
    except Exception:
        pass

    # 4. xhtml2pdf / pisa fallback
    try:
        from xhtml2pdf import pisa
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(print_html, dest=pdf_file)
            if not pisa_status.err and output_path.exists() and output_path.stat().st_size > 0:
                return
    except Exception:
        pass

    # 5. ReportLab basic canvas fallback
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(output_path), pagesize=A4)
        c.drawString(100, 750, title)
        c.save()
        if output_path.exists() and output_path.stat().st_size > 0:
            return
    except Exception:
        pass

    raise RuntimeError("오픈소스 PDF 렌더러(WeasyPrint, Playwright, LibreOffice, xhtml2pdf) 실행에 실패했습니다.")


# 한글(HWP) to PDF 문서 데이터를 대상 포맷으로 변환함
def _convert_hwp_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert HWP to PDF using Windows COM if available, or 100% open-source HTML->PDF renderer."""
    try:
        with win32_com_session("HWPFrame.HwpObject") as hwp:
            hwp.XHwpWindows.Item(0).Visible = False
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass
            opened = hwp.Open(str(input_path.resolve()))
            if opened:
                saved = hwp.SaveAs(str(output_path.resolve()), "PDF", "")
                if saved and output_path.exists() and output_path.stat().st_size > 0:
                    return
    except Exception:
        pass

    body_html, _ = _convert_hwp_to_html_and_markdown(input_path)
    _render_html_to_pdf(body_html, output_path, title=input_path.stem)


# 한글 표준(HWPX) to PDF 문서 데이터를 대상 포맷으로 변환함
def _convert_hwpx_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert HWPX to PDF using Windows COM if available, or 100% open-source HTML->PDF renderer."""
    try:
        with win32_com_session("HWPFrame.HwpObject") as hwp:
            hwp.XHwpWindows.Item(0).Visible = False
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass
            opened = hwp.Open(str(input_path.resolve()))
            if opened:
                saved = hwp.SaveAs(str(output_path.resolve()), "PDF", "")
                if saved and output_path.exists() and output_path.stat().st_size > 0:
                    return
    except Exception:
        pass

    body_html, _ = _convert_hwpx_to_html_and_markdown(input_path)
    _render_html_to_pdf(body_html, output_path, title=input_path.stem)


# document to excel 데이터를 대상 포맷으로 변환함
def _convert_document_to_excel(input_path: Path, output_path: Path) -> None:
    """Extract all tables from HWP, HWPX, DOCX, PDF, or MD and write them into structured Excel sheets."""
    import pandas as pd
    from bs4 import BeautifulSoup

    ext = input_path.suffix.lower()
    tables_data: List[List[List[str]]] = []

    if ext == ".hwp":
        body_html, _ = _convert_hwp_to_html_and_markdown(input_path)
        soup = BeautifulSoup(body_html, "html.parser")
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                row = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if any(row):
                    rows.append(row)
            if rows:
                tables_data.append(rows)

    elif ext == ".hwpx":
        body_html, _ = _convert_hwpx_to_html_and_markdown(input_path)
        soup = BeautifulSoup(body_html, "html.parser")
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                row = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if any(row):
                    rows.append(row)
            if rows:
                tables_data.append(rows)

    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(input_path)
            for table in doc.tables:
                rows = []
                for row in table.rows:
                    r_cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                    if any(r_cells):
                        rows.append(r_cells)
                if rows:
                    tables_data.append(rows)
        except Exception:
            pass

    elif ext == ".pdf":
        try:
            from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_excel
            convert_pdf_to_high_fidelity_excel(input_path, output_path)
            return
        except Exception:
            try:
                import pdfplumber
                with pdfplumber.open(str(input_path.resolve())) as pdf:
                    for page in pdf.pages:
                        for raw_tbl in page.extract_tables():
                            if not raw_tbl:
                                continue
                            _, _, flat_rows = _format_hierarchical_table_to_html_and_md(raw_tbl)
                            if flat_rows and len(flat_rows) > 1:
                                tables_data.append(flat_rows)
                            else:
                                clean_rows = []
                                for r in raw_tbl:
                                    clean_r = [(c or "").strip().replace("\n", " ") for c in r]
                                    if any(clean_r):
                                        clean_rows.append(clean_r)
                                if clean_rows:
                                    tables_data.append(clean_rows)
            except Exception:
                pass

    elif ext == ".md":
        md_text = input_path.read_text(encoding="utf-8", errors="ignore")
        import markdown
        html = markdown.markdown(md_text, extensions=["tables"])
        soup = BeautifulSoup(html, "html.parser")
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                row = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if any(row):
                    rows.append(row)
            if rows:
                tables_data.append(rows)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if tables_data:
            for idx, rows in enumerate(tables_data):
                max_cols = max(len(r) for r in rows)
                padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                header = padded_rows[0]

                unique_header = []
                seen: Dict[str, int] = {}
                for c_idx, h in enumerate(header):
                    col_name = h.strip() if h.strip() else f"컬럼_{c_idx+1}"
                    if col_name in seen:
                        seen[col_name] += 1
                        unique_header.append(f"{col_name}_{seen[col_name]}")
                    else:
                        seen[col_name] = 0
                        unique_header.append(col_name)

                df = pd.DataFrame(padded_rows[1:], columns=unique_header)
                sheet_name = f"표_{idx+1}" if len(tables_data) > 1 else "데이터_표"
                df.to_excel(writer, sheet_name=sheet_name[:30], index=False)
        else:
            text_lines = []
            if ext == ".hwp":
                _, md = _convert_hwp_to_html_and_markdown(input_path)
                text_lines = [line.strip() for line in md.splitlines() if line.strip()]
            elif ext == ".hwpx":
                _, md = _convert_hwpx_to_html_and_markdown(input_path)
                text_lines = [line.strip() for line in md.splitlines() if line.strip()]
            else:
                text_lines = [line.strip() for line in input_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]

            df = pd.DataFrame({"문서_내용": text_lines})
            df.to_excel(writer, sheet_name="본문_내용", index=False)


# document previews 정보를 조회하여 반환함
def _get_document_previews(src_path: Path, raw_ext: str, original_filename: str = "") -> tuple[Optional[str], Optional[str]]:
    """
    Extract high-fidelity visual HTML preview and structured Markdown preview for any document format.
    Returns: (html_preview, markdown_preview)
    """
    try:
        parsed = _build_structured_document_parse(src_path, raw_ext, original_filename)
        return parsed["html_preview"], parsed["markdown"]
    except Exception:
        pass

    return None, None


# download 다운로드 URL 형식으로 변환하여 반환함
def _to_download_url(file_path: Path) -> str:
    """파일 경로를 ROOT_DIR 기준 상대 경로로 변환하여 안전한 다운로드 URL을 생성함"""
    try:
        rel = file_path.relative_to(settings.ROOT_DIR).as_posix()
    except Exception:
        rel = file_path.as_posix()
    return f"/api/v1/files/download?path={rel}"


# conversion 명령 또는 파이프라인을 실행함
def _execute_conversion(
    file: Any,
    target_format: str,
    encoding: Optional[str] = "utf-8",
    table_name: Optional[str] = "converted_data",
    engine: str = "legacy",
    strict: bool = False,
):
    """데이터셋 또는 문서 파일을 지정한 형식으로 변환함

    @param file 업로드된 원본 파일
    @param target_format 변환 대상 형식
    @param encoding 정형 데이터의 문자 인코딩
    @param table_name SQL 출력 시 사용할 테이블명
    @return 변환 결과, 다운로드 경로, 구조화 미리보기를 포함한 응답
    @raises ConversionError 파일 형식이 지원되지 않거나 변환에 실패한 경우
    """
    if not file.filename:
        raise ConversionError(status_code=400, detail="파일명이 필요합니다.")
    if engine not in {"legacy", "ir"}:
        raise ConversionError(status_code=400, detail="알 수 없는 변환 엔진입니다.")

    conv_dir = settings.OUTPUT_DIR / "converted"
    conv_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    raw_ext = Path(file.filename).suffix.lower()
    stem = Path(file.filename).stem
    try:
        if engine == 'ir':
            from synthetic_engine.document_conversion.registry import RENDERER_REGISTRY
            target_fmt = normalize_target(target_format)
            if target_fmt not in RENDERER_REGISTRY:
                raise ConversionRuleError('IR 엔진에서 지원하지 않는 출력 포맷입니다.')
        else:
            conversion_rule = resolve_rule(raw_ext, target_format)
            target_fmt = conversion_rule.target
    except ConversionRuleError as exc:
        raise ConversionError(status_code=400, detail=str(exc)) from exc

    # 1. Save uploaded file
    try:
        saved_info = DatasetService.save_upload_file(file.file, file.filename, unique=True)
        src_path = Path(saved_info["path"])
    except Exception as exc:
        raise ConversionError(status_code=500, detail=f"파일 업로드 실패: {str(exc)}")
    finally:
        file.file.close()

    original_file_url = _to_download_url(src_path)

    doc_exts = DOCUMENT_SOURCES
    data_exts = DATASET_SOURCES

    if engine == 'ir':
        from synthetic_engine.document_conversion.pipeline import convert_document
        try:
            out_path = convert_document(src_path, target_fmt,
                                               output_dir=conv_dir, strict=strict)
            _ensure_downloadable_output(out_path, "IR 변환")
            report_path = out_path.with_suffix('.conversion-report.json')
            _ensure_downloadable_output(report_path, "IR 변환 보고서")
            report = json.loads(report_path.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise ConversionError(status_code=422, detail=str(exc)) from exc
        entry = {
            'id': uid, 'category': 'document', 'original_filename': file.filename,
            'original_file_url': original_file_url,
            'output_filename': out_path.name, 'source_format': raw_ext.lstrip('.').upper(),
            'target_format': target_fmt.upper(), 'file_size': out_path.stat().st_size,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'download_url': _to_download_url(out_path),
            'report_download_url': _to_download_url(report_path),
            'download_ready': True,
            'engine': 'ir',
        }
        _record_history(conv_dir, entry)
        return {**entry, 'status': 'success', 'file_name': out_path.name,
                'conversion_report': report, 'message': 'IR 변환 완료. 손실 보고서를 확인하세요.'}

    # 2. Document Conversion branch
    if raw_ext in doc_exts:
        try:
            doc_parse = _build_structured_document_parse(src_path, raw_ext, file.filename)
            _ensure_meaningful_document_parse(doc_parse)
        except Exception as exc:
            if isinstance(exc, ConversionError):
                raise
            raise ConversionError(status_code=400, detail=f"문서 구조화 파싱 실패: {str(exc)}")
        doc_html_preview = doc_parse["html_preview"]
        doc_md_preview = doc_parse["markdown"]
        doc_structure = doc_parse["structure"]
        delivery_status, delivery_ready = _document_delivery_state(doc_structure)

        # A. Markdown Conversion (.md)
        if target_fmt in ("md", "markdown"):
            out_name = f"{stem}_{uid}.md"
            out_path = conv_dir / out_name

            if doc_md_preview:
                md_text = doc_md_preview
            elif raw_ext in (".docx", ".doc"):
                md_text = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                md_text = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                md_text = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".pdf":
                md_text = _convert_pdf_to_markdown(src_path)
            elif raw_ext == ".md":
                md_text = src_path.read_text(encoding="utf-8", errors="ignore")
            elif raw_ext in IMAGE_SOURCES:
                md_text = _convert_image_to_markdown(src_path)
            else:
                raise ConversionError(status_code=400, detail=f"{raw_ext} 마크다운 변환을 지원하지 않습니다.")

            out_path.write_text(md_text, encoding="utf-8")
            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "Markdown")
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "markdown_preview": md_text,
                "html_preview": doc_html_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 파일이 마크다운(.md)으로 성공적으로 변환되었습니다."
            }

        # B. Pure Text Conversion (.txt)
        elif target_fmt == "txt":
            out_name = f"{stem}_{uid}.txt"
            out_path = conv_dir / out_name
            if doc_md_preview:
                txt = doc_md_preview
            elif raw_ext in (".docx", ".doc"):
                txt = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                txt = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                txt = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".pdf":
                txt = _convert_pdf_to_markdown(src_path)
            elif raw_ext in IMAGE_SOURCES:
                txt = _convert_image_to_markdown(src_path)
            else:
                txt = src_path.read_text(encoding="utf-8", errors="ignore")

            out_path.write_text(txt, encoding="utf-8")
            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "TXT")
            file_size = out_path.stat().st_size
            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "TXT",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)
            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "TXT",
                "markdown_preview": txt,
                "html_preview": doc_html_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 텍스트 추출 완료."
            }

        # C. PDF Conversion
        elif target_fmt == "pdf":
            out_name = f"{stem}_{uid}.pdf"
            out_path = conv_dir / out_name
            try:
                if raw_ext in (".doc", ".docx"):
                    _convert_word_to_pdf(src_path, out_path)
                elif raw_ext == ".hwp":
                    _convert_hwp_to_pdf(src_path, out_path)
                elif raw_ext == ".hwpx":
                    _convert_hwpx_to_pdf(src_path, out_path)
                elif raw_ext == ".md":
                    body = _convert_markdown_to_html(src_path)
                    _render_html_to_pdf(body, out_path, title=stem)
                elif raw_ext in IMAGE_SOURCES:
                    from synthetic_engine.document_conversion.pipeline import convert_document
                    generated = convert_document(src_path, "pdf", output_dir=conv_dir)
                    generated.replace(out_path)
                else:
                    raise ConversionError(status_code=400, detail=f"{raw_ext} PDF 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise ConversionError(status_code=500, detail=f"PDF 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "PDF")
            file_size = out_path.stat().st_size
            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "PDF",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)
            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "PDF",
                "html_preview": doc_html_preview,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 고해상도 PDF 변환 완료."
            }

        # D. HWPX Conversion
        elif target_fmt == "hwpx":
            out_name = f"{stem}_{uid}.hwpx"
            out_path = conv_dir / out_name
            try:
                from synthetic_engine.exporters.hwp_high_fidelity_hwpx_converter import convert_any_hwp_to_hwpx
                convert_any_hwp_to_hwpx(src_path, out_path)
                _validate_hwpx_output(out_path)
            except Exception as exc:
                raise ConversionError(status_code=500, detail=f"HWPX 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "HWPX")
            file_size = out_path.stat().st_size
            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWPX",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)
            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWPX",
                "html_preview": doc_html_preview,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 개방형 HWPX 변환 완료."
            }

        # E. HTML Web Document Conversion (.html)
        elif target_fmt in ("html", "htm"):
            out_name = f"{stem}_{uid}.html"
            out_path = conv_dir / out_name
            try:
                if doc_html_preview:
                    out_path.write_text(doc_html_preview, encoding="utf-8")
                elif raw_ext == ".pdf":
                    from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_html
                    full_html = convert_pdf_to_high_fidelity_html(src_path, title=stem)
                    out_path.write_text(full_html, encoding="utf-8")
                elif raw_ext == ".md":
                    body = _convert_markdown_to_html(src_path)
                    full_html = _wrap_html_page(stem, body, file.filename)
                    out_path.write_text(full_html, encoding="utf-8")
                else:
                    raise ConversionError(status_code=400, detail=f"{raw_ext} HTML 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise ConversionError(status_code=500, detail=f"HTML 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "HTML")
            file_size = out_path.stat().st_size
            html_content = out_path.read_text(encoding="utf-8", errors="ignore")

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "html_preview": html_content,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 파일이 반응형 HTML 웹 문서로 성공적으로 변환되었습니다."
            }

        # F. Excel Spreadsheet Conversion (.xlsx)
        elif target_fmt in ("xlsx", "xls"):
            out_name = f"{stem}_{uid}.xlsx"
            out_path = conv_dir / out_name
            try:
                _convert_document_to_excel(src_path, out_path)
            except Exception as exc:
                raise ConversionError(status_code=500, detail=f"Excel 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "Excel")
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "XLSX",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "XLSX",
                "html_preview": doc_html_preview,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 내의 모든 표가 엑셀(.xlsx) 스프레드시트로 성공적으로 변환되었습니다."
            }

        # G. Word Document Conversion (.docx)
        elif target_fmt in ("docx", "doc", "word"):
            out_name = f"{stem}_{uid}.docx"
            out_path = conv_dir / out_name
            try:
                if raw_ext == ".pdf":
                    from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_docx
                    convert_pdf_to_high_fidelity_docx(src_path, out_path)
                elif raw_ext in (".docx", ".doc"):
                    import shutil
                    shutil.copyfile(src_path, out_path)
                elif raw_ext in (".hwp", ".hwpx"):
                    from synthetic_engine.exporters.hwp_high_fidelity_docx_converter import convert_any_hwp_to_docx
                    convert_any_hwp_to_docx(src_path, out_path)
                elif raw_ext == ".md":
                    md_text = src_path.read_text(encoding="utf-8", errors="ignore")
                    import docx
                    d = docx.Document()
                    for line in md_text.splitlines():
                        if line.startswith("# "):
                            d.add_heading(line[2:].strip(), level=1)
                        elif line.startswith("## "):
                            d.add_heading(line[3:].strip(), level=2)
                        elif line.strip():
                            d.add_paragraph(line.strip())
                    d.save(out_path)
                elif raw_ext in IMAGE_SOURCES:
                    from synthetic_engine.document_conversion.pipeline import convert_document
                    generated = convert_document(src_path, "docx", output_dir=conv_dir)
                    generated.replace(out_path)
                else:
                    raise ConversionError(status_code=400, detail=f"{raw_ext} Word 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise ConversionError(status_code=500, detail=f"Word 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "Word")
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "DOCX",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "DOCX",
                "html_preview": doc_html_preview,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 파일이 MS Word(.docx) 서식 문서로 성공적으로 변환되었습니다."
            }

        # H. HWP Document Conversion (.hwp)
        elif target_fmt == "hwp":
            out_name = f"{stem}_{uid}.hwp"
            out_path = conv_dir / out_name
            try:
                if raw_ext == ".hwp":
                    import shutil
                    shutil.copyfile(src_path, out_path)
                elif raw_ext == ".hwpx":
                    _convert_hwp_doc(src_path, out_path, "hwp")
                elif raw_ext == ".pdf":
                    from synthetic_engine.exporters.pdf_high_fidelity_converter import convert_pdf_to_high_fidelity_hwp
                    convert_pdf_to_high_fidelity_hwp(src_path, out_path)
                else:
                    raise ConversionError(status_code=400, detail=f"{raw_ext} HWP 변환을 지원하지 않습니다.")
                if not out_path.exists() or out_path.stat().st_size == 0:
                    raise RuntimeError("HWP 출력 파일이 생성되지 않았습니다.")
            except Exception as exc:
                if isinstance(exc, ConversionError):
                    raise
                raise ConversionError(status_code=500, detail=f"HWP 변환 실패: {str(exc)}")

            download_url = _to_download_url(out_path)
            _ensure_downloadable_output(out_path, "HWP")
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWP",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": delivery_status,
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "original_file_url": original_file_url,
                "download_url": download_url,
                "download_ready": delivery_ready,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWP",
                "html_preview": doc_html_preview,
                "markdown_preview": doc_md_preview,
                "document_structure": doc_structure,
                "message": f"{file.filename} 파일이 한글 HWP(.hwp) 문서로 성공적으로 변환되었습니다."
            }

        else:
            raise ConversionError(
                status_code=400,
                detail=f"문서 파일({raw_ext})은 'docx', 'hwpx', 'hwp', 'xlsx', 'html', 'pdf', 'md', 'txt' 형식으로 변환할 수 있습니다."
            )

    # 3. Tabular Dataset Conversion branch
    elif raw_ext in data_exts:
        try:
            df = _read_xml_table(src_path) if raw_ext == ".xml" else read_table(src_path)
        except Exception as exc:
            raise ConversionError(status_code=400, detail=f"데이터셋 파싱 실패: {str(exc)}")

        raw_table = (table_name or stem or "converted_data").strip()
        clean_table = re.sub(r"[^\w\-]+", "_", raw_table).strip("_") or "converted_data"
        md_preview_text = None
        html_preview_text = None

        try:
            if target_fmt in ("md", "markdown"):
                out_name = f"{stem}_{uid}.md"
                out_path = conv_dir / out_name
                # Convert up to 500 rows to markdown table
                md_preview_text = _dataframe_to_markdown(df, limit=500)
                header_comment = f"<!-- Converted from {file.filename} ({len(df):,} rows, {len(df.columns)} columns) -->\n\n"
                out_path.write_text(header_comment + md_preview_text, encoding="utf-8")
            elif target_fmt in ("html", "htm"):
                out_name = f"{stem}_{uid}.html"
                out_path = conv_dir / out_name
                # Convert dataset to styled HTML table with live search
                sample_df = df.head(1000)
                table_raw_html = sample_df.to_html(classes="dataframe styled-table", index=False, border=0)
                table_wrapper = f'<div class="table-container">{table_raw_html}</div>'
                full_html = _wrap_html_page(
                    title=f"{clean_table} 데이터 테이블",
                    body_html=table_wrapper,
                    filename=file.filename,
                    is_table=True
                )
                out_path.write_text(full_html, encoding="utf-8")
                html_preview_text = full_html
            elif target_fmt == "csv":
                out_name = f"{stem}_{uid}.csv"
                out_path = conv_dir / out_name
                df.to_csv(out_path, index=False, encoding="utf-8-sig")
            elif target_fmt in ("xlsx", "xls"):
                out_name = f"{stem}_{uid}.xlsx"
                out_path = conv_dir / out_name
                df.to_excel(out_path, index=False)
            elif target_fmt == "tsv":
                out_name = f"{stem}_{uid}.tsv"
                out_path = conv_dir / out_name
                df.to_csv(out_path, sep="\t", index=False, encoding="utf-8-sig")
            elif target_fmt == "json":
                out_name = f"{stem}_{uid}.json"
                out_path = conv_dir / out_name
                df.to_json(out_path, orient="records", force_ascii=False, indent=2)
            elif target_fmt == "jsonl":
                out_name = f"{stem}_{uid}.jsonl"
                out_path = conv_dir / out_name
                df.to_json(out_path, orient="records", lines=True, force_ascii=False)
            elif target_fmt == "xml":
                out_name = f"{stem}_{uid}.xml"
                out_path = conv_dir / out_name
                _write_xml_table(df, out_path)
            elif target_fmt in ("parquet", "pq"):
                out_name = f"{stem}_{uid}.parquet"
                out_path = conv_dir / out_name
                df.to_parquet(out_path, index=False)
            elif target_fmt == "sql":
                out_name = f"{stem}_{uid}.sql"
                out_path = conv_dir / out_name
                sql_content = _dataframe_to_sql_insert(df, table_name=clean_table, limit=min(len(df), 50000))
                out_path.write_text(sql_content, encoding="utf-8")
                md_preview_text = f"```sql\n{sql_content[:4000]}\n```"
            else:
                raise ConversionError(
                    status_code=400,
                    detail=f"지원하지 않는 대상 데이터 포맷입니다: {target_fmt}"
                )
        except Exception as exc:
            raise ConversionError(status_code=500, detail=f"데이터 변환 처리 실패: {str(exc)}")

        download_url = _to_download_url(out_path)
        _ensure_downloadable_output(out_path, "데이터")
        file_size = out_path.stat().st_size
        preview_records = df.head(100).fillna("").to_dict(orient="records")

        entry = {
            "id": uid,
            "category": "dataset",
            "original_filename": file.filename,
            "original_file_url": original_file_url,
            "output_filename": out_name,
            "source_format": raw_ext.replace(".", "").upper(),
            "target_format": target_fmt.upper(),
            "file_size": file_size,
            "rows_count": len(df),
            "columns_count": len(df.columns),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": download_url,
        }
        _record_history(conv_dir, entry)

        return {
            "status": "success",
            "category": "dataset",
            "file_name": out_name,
            "original_filename": file.filename,
            "original_file_url": original_file_url,
            "download_url": download_url,
            "download_ready": True,
            "file_size": file_size,
            "source_format": raw_ext.replace(".", "").upper(),
            "target_format": target_fmt.upper(),
            "rows_count": len(df),
            "columns_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview_records,
            "markdown_preview": md_preview_text,
            "html_preview": html_preview_text,
            "message": f"{file.filename} ({len(df):,}행)이 {target_fmt.upper()} 포맷으로 성공적으로 변환되었습니다."
        }

    else:
        raise ConversionError(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {raw_ext}. 지원 형식: CSV, XLSX, TSV, JSON, XML, Parquet, HWP, HWPX, DOCX, PDF, MD"
        )


# converter 작업 이력 정보를 조회하여 반환함
def _get_converter_history():
    """최근 문서·데이터 변환 이력을 조회함"""
    conv_dir = settings.OUTPUT_DIR / "converted"
    hist_file = conv_dir / "converter_history.json"
    if not hist_file.exists():
        return []
    try:
        with hist_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


_history_lock = RLock()


# record 작업 이력 작업을 수행함
def _record_history(conv_dir: Path, entry: Dict[str, Any]) -> None:
    with _history_lock:
        _write_history(conv_dir, entry)


# 작업 이력 데이터를 파일에 기록함
def _write_history(conv_dir: Path, entry: Dict[str, Any]) -> None:
    """변환 이력을 JSON 파일에 최신순으로 저장함"""
    hist_file = conv_dir / "converter_history.json"
    hist_list = []
    if hist_file.exists():
        try:
            with hist_file.open("r", encoding="utf-8") as f:
                hist_list = json.load(f)
        except Exception:
            hist_list = []
    hist_list.insert(0, entry)
    hist_list = hist_list[:50]
    temporary = hist_file.with_name(f'.history-{uuid.uuid4().hex}.tmp')
    try:
        with temporary.open("w", encoding="utf-8") as f:
            json.dump(hist_list, f, ensure_ascii=False, indent=2)
        temporary.replace(hist_file)
    except Exception as exc:
        logging.warning('Conversion history persistence failed: %s', exc)
    finally:
        temporary.unlink(missing_ok=True)

# PDF 문서 내 텍스트 내용을 추출하여 검사함
def inspect_pdf_text(source: Path) -> str:
    from synthetic_engine.document_conversion.parsers.pdf import parse_pdf, page_texts
    return '\n'.join(page_texts(parse_pdf(source)))


class DocumentConversionService:
    convert = staticmethod(_execute_conversion)
    history = staticmethod(_get_converter_history)
    convert_word_to_pdf = staticmethod(_convert_word_to_pdf)
    convert_hwp_doc = staticmethod(_convert_hwp_doc)
    convert_hwp_to_html_and_markdown = staticmethod(_convert_hwp_to_html_and_markdown)
    convert_hwpx_to_html_and_markdown = staticmethod(_convert_hwpx_to_html_and_markdown)
    convert_document_to_excel = staticmethod(_convert_document_to_excel)
    format_hierarchical_table_to_html_and_md = staticmethod(_format_hierarchical_table_to_html_and_md)
    get_document_previews = staticmethod(_get_document_previews)
    build_structured_document_parse = staticmethod(_build_structured_document_parse)
