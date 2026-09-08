# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
import numpy as np

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from synthetic_api.core.config import settings
from synthetic_api.application.services.dataset_service import DatasetService
from synthetic_engine.profiling.analyzer import read_table

router = APIRouter(prefix="/converter", tags=["converter"])


def _convert_word_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert Word document to PDF using Windows COM or LibreOffice fallback."""
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(input_path.resolve()))
            doc.SaveAs(str(output_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
            if output_path.exists() and output_path.stat().st_size > 0:
                return
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
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


def _convert_hwp_doc(input_path: Path, output_path: Path, target_fmt: str) -> None:
    """Convert HWP document using Windows COM or specialized open-source fallbacks."""
    fmt_lower = target_fmt.lower().strip()
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        hwp = None
        try:
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
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
                fmt_arg = "PDF" if fmt_lower == "pdf" else ("HTML" if fmt_lower == "html" else "HWPX")
                saved = hwp.SaveAs(str(output_path.resolve()), fmt_arg, "")
                if saved and output_path.exists() and output_path.stat().st_size > 0:
                    return
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        pass

    # Fallbacks when Windows COM is not available
    if fmt_lower == "html":
        _convert_hwp_to_html(input_path, output_path)
    elif fmt_lower == "hwpx":
        try:
            # Fallback HWP -> HWPX via markdown/xml
            md = _convert_hwp_to_markdown(input_path)
            # Create a simple valid HWPX file with text if needed
            output_path.write_text(md, encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"HWPX 변환 실패: {str(exc)}")
    elif fmt_lower == "pdf":
        raise RuntimeError("PDF 변환을 위해 Windows 한글 오피스 또는 PDF 렌더러가 필요합니다.")


def _extract_hwp_paragraphs_pure(input_path: Path) -> List[str]:
    """Extract paragraphs from HWP using text extractors or fallback."""
    _, md = _convert_hwp_to_html_and_markdown(input_path)
    return [p.strip() for p in md.splitlines() if p.strip()]


def _validate_hwpx_output(output_path: Path) -> None:
    """Validate that output HWPX is a valid ZIP package."""
    if not output_path.exists() or not zipfile.is_zipfile(output_path):
        raise RuntimeError(f"유효하지 않은 ZIP 패키지: {output_path.name}")


def _convert_hwp_to_hwpx_pure(input_path: Path, output_path: Path) -> None:
    """Pure-python converter from HWP to HWPX package using HwpxDocument."""
    from hwpx.document import HwpxDocument
    paragraphs = _extract_hwp_paragraphs_pure(input_path)
    doc = HwpxDocument.new()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save_to_path(output_path)


def _convert_docx_to_markdown(input_path: Path) -> str:
    """Convert DOCX file to Markdown preserving headings, lists, and tables."""
    try:
        import docx
        doc = docx.Document(input_path)
        md_lines: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading 1" in style_name:
                md_lines.append(f"# {text}\n")
            elif "heading 2" in style_name:
                md_lines.append(f"## {text}\n")
            elif "heading 3" in style_name:
                md_lines.append(f"### {text}\n")
            elif "list" in style_name or "bullet" in style_name:
                md_lines.append(f"- {text}")
            else:
                md_lines.append(f"{text}\n")

        for table in doc.tables:
            t_rows = []
            col_count = 0
            for r_idx, row in enumerate(table.rows):
                cells = [c.text.strip().replace("\n", " ").replace("|", "/") for c in row.cells]
                if cells:
                    col_count = max(col_count, len(cells))
                    t_rows.append("| " + " | ".join(cells) + " |")
                    if r_idx == 0:
                        t_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
            if t_rows:
                md_lines.append("\n" + "\n".join(t_rows) + "\n")

        return "\n".join(md_lines).strip()
    except Exception as exc:
        raise RuntimeError(f"Word 마크다운 변환 실패: {str(exc)}")


def _parse_html_soup_to_clean_html_and_md(html_content: str) -> tuple[str, str]:
    """Parse HTML string and convert into styled HTML body and Markdown preserving all tables."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    html_blocks: List[str] = []
    md_blocks: List[str] = []

    body = soup.find("body") or soup

    for el in body.find_all(["h1", "h2", "h3", "h4", "p", "table", "ul", "ol"], recursive=False):
        if el.name in ("h1", "h2", "h3", "h4"):
            level = int(el.name[1])
            txt = el.get_text(strip=True)
            if txt:
                html_blocks.append(f"<{el.name}>{txt}</{el.name}>")
                md_blocks.append("#" * level + " " + txt + "\n")
        elif el.name == "p":
            txt = el.get_text(strip=True)
            if txt:
                html_blocks.append(f"<p>{txt}</p>")
                md_blocks.append(f"{txt}\n")
        elif el.name in ("ul", "ol"):
            items = []
            for li in el.find_all("li"):
                li_txt = li.get_text(strip=True)
                if li_txt:
                    items.append(f"<li>{li_txt}</li>")
                    md_blocks.append(f"- {li_txt}")
            if items:
                html_blocks.append(f"<{el.name}>\n  " + "\n  ".join(items) + f"\n</{el.name}>")
                md_blocks.append("")
        elif el.name == "table":
            t_html_rows = []
            t_md_rows = []
            rows = el.find_all("tr")
            for r_idx, r in enumerate(rows):
                r_html_cells = []
                r_md_cells = []
                for c in r.find_all(["th", "td"]):
                    colspan = c.get("colspan", "1")
                    rowspan = c.get("rowspan", "1")
                    c_txt = c.get_text(strip=True)

                    attrs = []
                    if colspan and str(colspan) != "1":
                        attrs.append(f'colspan="{colspan}"')
                    if rowspan and str(rowspan) != "1":
                        attrs.append(f'rowspan="{rowspan}"')
                    attr_str = (" " + " ".join(attrs)) if attrs else ""

                    tag = "th" if r_idx == 0 or c.name == "th" else "td"
                    r_html_cells.append(f"<{tag}{attr_str}>{c_txt}</{tag}>")
                    r_md_cells.append(c_txt.replace("\n", " ").replace("|", "/"))

                if r_html_cells:
                    t_html_rows.append(f"      <tr>{''.join(r_html_cells)}</tr>")
                if r_md_cells:
                    t_md_rows.append("| " + " | ".join(r_md_cells) + " |")
                    if r_idx == 0:
                        t_md_rows.append("| " + " | ".join(["---"] * len(r_md_cells)) + " |")

            if t_html_rows:
                table_html = (
                    '<div class="table-container">\n  <table class="styled-table">\n'
                    + "\n".join(t_html_rows)
                    + "\n  </table>\n</div>"
                )
                html_blocks.append(table_html)
            if t_md_rows:
                md_blocks.append("\n" + "\n".join(t_md_rows) + "\n")

    # If top-level recursive=False didn't capture tables
    if not any("<table" in b for b in html_blocks):
        for tbl in soup.find_all("table"):
            t_html_rows = []
            t_md_rows = []
            for r_idx, r in enumerate(tbl.find_all("tr")):
                r_html_cells = []
                r_md_cells = []
                for c in r.find_all(["th", "td"]):
                    c_txt = c.get_text(strip=True)
                    tag = "th" if r_idx == 0 or c.name == "th" else "td"
                    r_html_cells.append(f"<{tag}>{c_txt}</{tag}>")
                    r_md_cells.append(c_txt.replace("\n", " ").replace("|", "/"))
                if r_html_cells:
                    t_html_rows.append(f"      <tr>{''.join(r_html_cells)}</tr>")
                if r_md_cells:
                    t_md_rows.append("| " + " | ".join(r_md_cells) + " |")
                    if r_idx == 0:
                        t_md_rows.append("| " + " | ".join(["---"] * len(r_md_cells)) + " |")
            if t_html_rows:
                table_html = (
                    '<div class="table-container">\n  <table class="styled-table">\n'
                    + "\n".join(t_html_rows)
                    + "\n  </table>\n</div>"
                )
                html_blocks.append(table_html)
            if t_md_rows:
                md_blocks.append("\n" + "\n".join(t_md_rows) + "\n")

    return "\n".join(html_blocks), "\n".join(md_blocks).strip()


def _convert_hwp_to_html_and_markdown(input_path: Path) -> tuple[str, str]:
    """Convert HWP file to clean HTML body and Markdown with complete table preservation."""
    import tempfile
    import subprocess

    # 1. Try Windows COM if available
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        hwp = None
        try:
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
            hwp.XHwpWindows.Item(0).Visible = False
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass
            opened = hwp.Open(str(input_path.resolve()))
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
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        pass

    # 2. PyHWP (hwp5html) Fallback (Linux / Docker / No COM)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "html_out"
            res = subprocess.run(["hwp5html", "--output", str(out_dir), str(input_path)], capture_output=True)
            index_xhtml = out_dir / "index.xhtml"
            if not index_xhtml.exists():
                index_xhtml = out_dir / "index.html"
            if index_xhtml.exists():
                html_text = index_xhtml.read_text(encoding="utf-8", errors="ignore")
                body_html, md = _parse_html_soup_to_clean_html_and_md(html_text)
                if body_html and body_html.strip():
                    return body_html, md
    except Exception:
        pass

    # 3. Text fallback
    try:
        res = subprocess.run(["hwp5txt", str(input_path)], capture_output=True)
        txt = res.stdout.decode("utf-8", errors="ignore").strip()
        if txt:
            paragraphs = [f"<p>{p.strip()}</p>" for p in txt.split("\n\n") if p.strip()]
            return "\n".join(paragraphs), txt
    except Exception:
        pass

    return "<p>한글 문서 내용을 읽을 수 없습니다.</p>", "한글 문서 내용을 읽을 수 없습니다."


def _convert_hwp_to_markdown(input_path: Path) -> str:
    """Convert HWP file to Markdown."""
    _, md = _convert_hwp_to_html_and_markdown(input_path)
    return md


def _convert_hwpx_to_html_and_markdown(input_path: Path) -> tuple[str, str]:
    """Parse HWPX XML in sequential document order into (body_html, markdown_text) preserving all tables."""
    hp_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    html_blocks: List[str] = []
    md_blocks: List[str] = []

    try:
        with zipfile.ZipFile(input_path, "r") as zf:
            section_names = sorted([n for n in zf.namelist() if "section" in n.lower() and n.endswith(".xml")])
            if not section_names:
                if "Preview/PrvText.txt" in zf.namelist():
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
                                p_text_parts.append(t.text)

                    p_text = "".join(p_text_parts).strip()
                    if p_text:
                        html_blocks.append(f"<p>{p_text}</p>")
                        md_blocks.append(f"{p_text}\n")

                    # 2. Tables inside this paragraph
                    for tbl in p.findall(".//hp:tbl", hp_ns):
                        table_html_rows = []
                        table_md_rows = []
                        trs = tbl.findall("./hp:tr", hp_ns)
                        for r_idx, tr in enumerate(trs):
                            row_html_cells = []
                            row_md_cells = []
                            for tc in tr.findall("./hp:tc", hp_ns):
                                cell_addr = tc.find("./hp:cellAddr", hp_ns)
                                colspan = cell_addr.attrib.get("colSpan", "1") if cell_addr is not None else "1"
                                rowspan = cell_addr.attrib.get("rowSpan", "1") if cell_addr is not None else "1"

                                c_texts = [t.text for t in tc.findall(".//hp:t", hp_ns) if t.text]
                                cell_str = " ".join(c_texts).strip()

                                attrs = []
                                if colspan and str(colspan) != "1":
                                    attrs.append(f'colspan="{colspan}"')
                                if rowspan and str(rowspan) != "1":
                                    attrs.append(f'rowspan="{rowspan}"')
                                attr_str = (" " + " ".join(attrs)) if attrs else ""

                                tag = "th" if r_idx == 0 else "td"
                                row_html_cells.append(f"<{tag}{attr_str}>{cell_str}</{tag}>")
                                row_md_cells.append(cell_str.replace("\n", " ").replace("|", "/"))

                            if row_html_cells:
                                table_html_rows.append(f"      <tr>{''.join(row_html_cells)}</tr>")
                            if row_md_cells:
                                table_md_rows.append("| " + " | ".join(row_md_cells) + " |")
                                if r_idx == 0:
                                    table_md_rows.append("| " + " | ".join(["---"] * len(row_md_cells)) + " |")

                        if table_html_rows:
                            table_html = (
                                '<div class="table-container">\n  <table class="styled-table">\n'
                                + "\n".join(table_html_rows)
                                + "\n  </table>\n</div>"
                            )
                            html_blocks.append(table_html)
                        if table_md_rows:
                            md_blocks.append("\n" + "\n".join(table_md_rows) + "\n")

        return "\n".join(html_blocks), "\n".join(md_blocks).strip()
    except Exception as exc:
        return f"<pre>{str(exc)}</pre>", str(exc)


def _convert_hwpx_to_markdown(input_path: Path) -> str:
    """Convert HWPX file to Markdown."""
    _, md = _convert_hwpx_to_html_and_markdown(input_path)
    return md


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

                tables = page.find_tables()

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

                    def not_within_table(obj):
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

                    for t_idx, raw_tbl in enumerate(page.extract_tables()):
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


def _convert_pdf_to_html(input_path: Path, output_path: Optional[Path] = None) -> str:
    """Convert PDF file to HTML body string, and optionally write to output_path."""
    body, _ = _convert_pdf_to_html_and_markdown(input_path)
    if output_path is not None:
        full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
        output_path.write_text(full_html, encoding="utf-8")
    return body


def _convert_pdf_to_markdown(input_path: Path) -> str:
    """Convert PDF file to Markdown string."""
    _, md = _convert_pdf_to_html_and_markdown(input_path)
    return md


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


def _wrap_html_page(title: str, body_html: str, filename: str, is_table: bool = False) -> str:
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
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0;
      font-size: 0.9rem;
    }}
    th, td {{
      border: 1px solid var(--border-color);
      padding: 0.65rem 0.9rem;
      text-align: left;
      vertical-align: middle;
    }}
    th {{
      background-color: var(--table-stripe);
      font-weight: 700;
      text-align: center;
      white-space: nowrap;
    }}
    tr:nth-child(even) td {{
      background-color: var(--table-stripe);
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
</body>
</html>
"""


def _convert_docx_to_html(input_path: Path) -> str:
    """Convert DOCX to clean HTML using mammoth or fallback via markdown."""
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
            return f"<pre>{md}</pre>"


def _convert_word_to_html(input_path: Path, output_path: Path) -> None:
    """Convert Word DOC/DOCX to HTML."""
    if input_path.suffix.lower() == ".docx":
        body = _convert_docx_to_html(input_path)
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")
        return

    # For legacy .doc: Use Word COM if possible, else text fallback
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(input_path.resolve()))
            doc.SaveAs(str(output_path.resolve()), FileFormat=8)  # 8 = wdFormatHTML
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        md = _convert_docx_to_markdown(input_path)
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")


def _convert_hwp_to_html(input_path: Path, output_path: Path) -> None:
    """Convert HWP to rich HTML web document with complete table preservation."""
    body, _ = _convert_hwp_to_html_and_markdown(input_path)
    full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
    output_path.write_text(full_html, encoding="utf-8")


def _convert_hwpx_to_html(input_path: Path, output_path: Path) -> None:
    """Convert HWPX to rich HTML web document with complete table preservation."""
    body, _ = _convert_hwpx_to_html_and_markdown(input_path)
    full_html = _wrap_html_page(input_path.stem, body, input_path.name, is_table=False)
    output_path.write_text(full_html, encoding="utf-8")


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


def _convert_hwp_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert HWP to PDF using Windows COM if available, or 100% open-source HTML->PDF renderer."""
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        hwp = None
        try:
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
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
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        pass

    body_html, _ = _convert_hwp_to_html_and_markdown(input_path)
    _render_html_to_pdf(body_html, output_path, title=input_path.stem)


def _convert_hwpx_to_pdf(input_path: Path, output_path: Path) -> None:
    """Convert HWPX to PDF using Windows COM if available, or 100% open-source HTML->PDF renderer."""
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        hwp = None
        try:
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
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
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        pass

    body_html, _ = _convert_hwpx_to_html_and_markdown(input_path)
    _render_html_to_pdf(body_html, output_path, title=input_path.stem)


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


@router.post("/convert")
async def convert_file(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    encoding: Optional[str] = Form("utf-8"),
    table_name: Optional[str] = Form("converted_data"),
):
    """
    Convert datasets (CSV, XLSX, TSV, JSON, Parquet, SQL, Markdown) or documents (HWP, HWPX, DOCX, PDF -> PDF, HWPX, MD, TXT, HTML).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 필요합니다.")

    conv_dir = settings.OUTPUT_DIR / "converted"
    conv_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    raw_ext = Path(file.filename).suffix.lower()
    stem = Path(file.filename).stem
    target_fmt = target_format.lower().strip()

    # 1. Save uploaded file
    try:
        saved_info = DatasetService.save_upload_file(file.file, file.filename, unique=True)
        src_path = Path(saved_info["path"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(exc)}")
    finally:
        file.file.close()

    doc_exts = {".hwp", ".hwpx", ".doc", ".docx", ".pdf", ".md"}
    data_exts = {".csv", ".xlsx", ".xls", ".tsv", ".txt", ".json", ".jsonl", ".parquet", ".pq"}

    # 2. Document Conversion branch
    if raw_ext in doc_exts:
        # A. Markdown Conversion (.md)
        if target_fmt in ("md", "markdown"):
            out_name = f"{stem}_{uid}.md"
            out_path = conv_dir / out_name

            if raw_ext in (".docx", ".doc"):
                md_text = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                md_text = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                md_text = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".pdf":
                md_text = _convert_pdf_to_markdown(src_path)
            elif raw_ext == ".md":
                md_text = src_path.read_text(encoding="utf-8", errors="ignore")
            else:
                raise HTTPException(status_code=400, detail=f"{raw_ext} 마크다운 변환을 지원하지 않습니다.")

            out_path.write_text(md_text, encoding="utf-8")
            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "markdown_preview": md_text[:5000],
                "message": f"{file.filename} 파일이 마크다운(.md)으로 성공적으로 변환되었습니다."
            }

        # B. Pure Text Conversion (.txt)
        elif target_fmt == "txt":
            out_name = f"{stem}_{uid}.txt"
            out_path = conv_dir / out_name
            if raw_ext in (".docx", ".doc"):
                txt = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                txt = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                txt = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".pdf":
                txt = _convert_pdf_to_markdown(src_path)
            else:
                txt = src_path.read_text(encoding="utf-8", errors="ignore")

            out_path.write_text(txt, encoding="utf-8")
            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "TXT",
                "markdown_preview": txt[:5000],
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
                else:
                    raise HTTPException(status_code=400, detail=f"{raw_ext} PDF 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PDF 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "PDF",
                "message": f"{file.filename} 고해상도 PDF 변환 완료."
            }

        # D. HWPX Conversion
        elif target_fmt == "hwpx":
            out_name = f"{stem}_{uid}.hwpx"
            out_path = conv_dir / out_name
            try:
                if raw_ext == ".hwp":
                    _convert_hwp_doc(src_path, out_path, "hwpx")
                else:
                    raise HTTPException(status_code=400, detail="HWPX 변환은 구형 HWP 파일만 지원합니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"HWPX 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWPX",
                "message": f"{file.filename} 개방형 HWPX 변환 완료."
            }

        # E. HTML Web Document Conversion (.html)
        elif target_fmt in ("html", "htm"):
            out_name = f"{stem}_{uid}.html"
            out_path = conv_dir / out_name
            try:
                if raw_ext in (".docx", ".doc"):
                    _convert_word_to_html(src_path, out_path)
                elif raw_ext == ".hwp":
                    _convert_hwp_to_html(src_path, out_path)
                elif raw_ext == ".hwpx":
                    _convert_hwpx_to_html(src_path, out_path)
                elif raw_ext == ".pdf":
                    body = _convert_pdf_to_html(src_path)
                    full_html = _wrap_html_page(stem, body, file.filename)
                    out_path.write_text(full_html, encoding="utf-8")
                elif raw_ext == ".md":
                    body = _convert_markdown_to_html(src_path)
                    full_html = _wrap_html_page(stem, body, file.filename)
                    out_path.write_text(full_html, encoding="utf-8")
                else:
                    raise HTTPException(status_code=400, detail=f"{raw_ext} HTML 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"HTML 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            html_content = out_path.read_text(encoding="utf-8", errors="ignore")

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "html_preview": html_content[:25000],
                "message": f"{file.filename} 파일이 반응형 HTML 웹 문서로 성공적으로 변환되었습니다."
            }

        # F. Excel Spreadsheet Conversion (.xlsx)
        elif target_fmt in ("xlsx", "xls"):
            out_name = f"{stem}_{uid}.xlsx"
            out_path = conv_dir / out_name
            try:
                _convert_document_to_excel(src_path, out_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Excel 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "XLSX",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "XLSX",
                "message": f"{file.filename} 내의 모든 표가 엑셀(.xlsx) 스프레드시트로 성공적으로 변환되었습니다."
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"문서 파일({raw_ext})은 'xlsx', 'html', 'pdf', 'hwpx', 'md', 'txt' 형식으로 변환할 수 있습니다."
            )

    # 3. Tabular Dataset Conversion branch
    elif raw_ext in data_exts:
        try:
            df = read_table(src_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"데이터셋 파싱 실패: {str(exc)}")

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
                html_preview_text = full_html[:25000]
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
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 대상 데이터 포맷입니다: {target_fmt}"
                )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"데이터 변환 처리 실패: {str(exc)}")

        download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
        file_size = out_path.stat().st_size
        preview_records = df.head(15).fillna("").to_dict(orient="records")

        entry = {
            "id": uid,
            "category": "dataset",
            "original_filename": file.filename,
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
            "download_url": download_url,
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
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {raw_ext}. 지원 형식: CSV, XLSX, TSV, JSON, Parquet, HWP, HWPX, DOCX, PDF, MD"
        )


@router.get("/history")
async def get_converter_history():
    conv_dir = settings.OUTPUT_DIR / "converted"
    hist_file = conv_dir / "converter_history.json"
    if not hist_file.exists():
        return []
    try:
        with hist_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _record_history(conv_dir: Path, entry: Dict[str, Any]) -> None:
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
    try:
        with hist_file.open("w", encoding="utf-8") as f:
            json.dump(hist_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
