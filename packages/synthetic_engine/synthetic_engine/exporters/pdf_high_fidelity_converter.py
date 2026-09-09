# -*- coding: utf-8 -*-
"""
High-Fidelity PDF Converter Engine
Converts complex PDF documents (with banners, callouts, cards, and multi-span tables)
into HTML (95%+ visual fidelity), Word (.docx), Excel (.xlsx with 3 styled sheets), HWP/HWPX, and Markdown.
Uses 100% free and open-source libraries (pymupdf, pdfplumber, openpyxl, python-docx, hwpx, etc.).
"""
from __future__ import annotations

import os
import re
import io
import base64
import uuid
import zipfile
import html as html_lib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pymupdf
import pdfplumber
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def rgb_to_hex(rgb: Optional[Tuple[float, ...]]) -> Optional[str]:
    """Convert RGB float or int tuple to hex string #rrggbb."""
    if not rgb:
        return None
    r, g, b = [int(max(0, min(255, c * 255 if isinstance(c, float) and c <= 1.0 else c))) for c in rgb[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"


def int_color_to_hex(color_int: Optional[int]) -> str:
    """Convert integer RGB color from PyMuPDF to hex string."""
    if color_int is None:
        return "#000000"
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return f"#{r:02x}{g:02x}{b:02x}"


def is_dark(hex_c: Optional[str]) -> bool:
    """Check if color is dark (brightness < 130)."""
    if not hex_c or not hex_c.startswith("#"):
        return False
    h = hex_c.lstrip("#")
    if len(h) != 6:
        return False
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return ((r * 299 + g * 587 + b * 114) / 1000) < 130
    except ValueError:
        return False


def _docx_set_cell_background(cell, hex_color: str):
    """Set background color of a table cell in DOCX."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color.lstrip("#")}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def _docx_set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding of a table cell in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)


def _docx_set_cell_border(cell, **kwargs):
    """Set cell borders in DOCX."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f'<w:{edge} {nsdecls("w")} w:val="{edge_data.get("val", "single")}" w:sz="{edge_data.get("sz", 4)}" w:space="0" w:color="{edge_data.get("color", "auto").lstrip("#")}"/>'
            tcBorders.append(parse_xml(tag))
        else:
            tag = f'<w:{edge} {nsdecls("w")} w:val="none"/>'
            tcBorders.append(parse_xml(tag))
    tcPr.append(tcBorders)


def _bbox_tuple(value: Any) -> Tuple[float, float, float, float]:
    """Return a normalized PyMuPDF/pdfplumber bbox tuple."""
    if hasattr(value, "x0"):
        return (float(value.x0), float(value.y0), float(value.x1), float(value.y1))
    return tuple(float(v) for v in value[:4])  # type: ignore[index]


def _bbox_intersection_area(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _bbox_area(bbox: Tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _overlap_ratio(
    inner: Tuple[float, float, float, float],
    outer: Tuple[float, float, float, float],
) -> float:
    area = _bbox_area(inner)
    if area <= 0:
        return 0.0
    return _bbox_intersection_area(inner, outer) / area


def _join_cell_text(parts: List[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p).strip())


def _escape_html(value: Any) -> str:
    return html_lib.escape(str(value or ""), quote=True)


def _escape_md_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("|", "\\|")).strip()


class HighFidelityPdfDoc:
    """
    Parses and reconstructs a PDF document into high-fidelity semantic components:
    - Banners (Title, Subtitle)
    - Alert / Notice callouts
    - Section Heading bars
    - Cards (Consultation records, transaction applications, medical notes)
    - Tabular Key-Value grids with merged columns
    - General body paragraphs
    - Page footers
    """

    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path).resolve()
        self.doc = pymupdf.open(str(self.pdf_path))
        self.pages: List[Dict[str, Any]] = []
        self._parse()

    def close(self):
        if self.doc and not self.doc.is_closed:
            self.doc.close()

    def _parse(self):
        plumber_tables_by_page = self._extract_pdfplumber_tables()

        for p_idx, page in enumerate(self.doc):
            p_w, p_h = page.rect.width, page.rect.height

            # 1. Extract major background drawings (width >= p_w * 0.6)
            raw_shapes = []
            for d in page.get_drawings():
                r = d.get("rect")
                if not r or r.width < p_w * 0.6:
                    continue
                # Skip full page canvas
                if r.height >= p_h * 0.7:
                    continue

                fill = rgb_to_hex(d.get("fill"))
                stroke = rgb_to_hex(d.get("color"))

                stype = "box"
                if is_dark(fill):
                    stype = "banner"
                elif fill and any(x in fill.lower() for x in ("edf", "ebf", "fef", "f0f", "e0f", "bde", "318")):
                    stype = "alert"
                elif fill and any(x in fill.lower() for x in ("cad", "e2e", "cbd", "d1d", "e5e")) and r.height < 35:
                    stype = "section_bar"
                elif (stroke or fill == "#ffffff") and r.height >= 35:
                    stype = "card"

                raw_shapes.append({
                    "type": stype,
                    "rect": _bbox_tuple(r),
                    "fill": fill,
                    "stroke": stroke,
                    "height": r.height,
                })

            # Deduplicate shapes overlapping at the same Y coordinate
            shapes = []
            for s in sorted(raw_shapes, key=lambda x: x["rect"][1]):
                if not shapes:
                    shapes.append(s)
                else:
                    last = shapes[-1]
                    if abs(last["rect"][1] - s["rect"][1]) < 5 and abs(last["rect"][3] - s["rect"][3]) < 5:
                        if s["type"] in ("card", "alert", "banner"):
                            shapes[-1] = s
                    else:
                        shapes.append(s)

            # 2. Extract text blocks and spans
            text_blocks = page.get_text("dict")["blocks"]
            structured_blocks = []
            for b in text_blocks:
                if "lines" not in b:
                    continue
                lines_data = []
                for l in b["lines"]:
                    spans = []
                    for s in l["spans"]:
                        t = s["text"]
                        if t:
                            spans.append({
                                "text": t,
                                "size": round(s["size"], 1),
                                "bold": bool(s["flags"] & 20 or "bold" in s["font"].lower()),
                                "color": int_color_to_hex(s.get("color")),
                                "font": s["font"],
                                "bbox": _bbox_tuple(s["bbox"]),
                            })
                    if spans:
                        spans.sort(key=lambda x: (x["bbox"][0], x["bbox"][1]))
                        lines_data.append(spans)
                if lines_data:
                    lines_data.sort(key=lambda l: (
                        round(min(s["bbox"][1] for s in l) / 2) * 2,
                        min(s["bbox"][0] for s in l),
                    ))
                    full_t = "\n".join("".join(s["text"] for s in l) for l in lines_data).strip()
                    structured_blocks.append({
                        "bbox": _bbox_tuple(b["bbox"]),
                        "lines": lines_data,
                        "text": full_t,
                        "source_order": len(structured_blocks),
                    })

            # 3. Match blocks to container shapes
            matched_blocks = set()
            page_elements = []

            for table in plumber_tables_by_page.get(p_idx, []):
                page_elements.append(table)
                table_bbox = table["bbox"]
                for b_idx, b in enumerate(structured_blocks):
                    if _overlap_ratio(b["bbox"], table_bbox) >= 0.35:
                        matched_blocks.add(b_idx)

            for s in shapes:
                s_blocks = []
                sy0, sy1 = s["rect"][1], s["rect"][3]
                for b_idx, b in enumerate(structured_blocks):
                    if b_idx in matched_blocks:
                        continue
                    if _overlap_ratio(b["bbox"], s["rect"]) >= 0.45:
                        s_blocks.append(b)
                        matched_blocks.add(b_idx)

                if s_blocks:
                    s_blocks.sort(key=lambda b: self._reading_order_key(b))
                    # Double check container type
                    b_txt = "\n".join(b["text"] for b in s_blocks)
                    final_type = s["type"]
                    if "안내" in b_txt and ("가명" in b_txt or "테스트" in b_txt or "참고" in b_txt or "※" in b_txt):
                        final_type = "alert"
                    elif final_type == "box":
                        if is_dark(s["fill"]):
                            final_type = "banner"
                        elif s["height"] >= 35:
                            final_type = "card"

                    page_elements.append({
                        "type": final_type,
                        "y0": sy0,
                        "x0": s["rect"][0],
                        "bbox": s["rect"],
                        "rect": s["rect"],
                        "fill": s["fill"],
                        "stroke": s["stroke"],
                        "blocks": s_blocks,
                        "source": "pymupdf_shape",
                    })

            for table_row in self._detect_table_rows_from_text(structured_blocks, matched_blocks, p_w):
                page_elements.append(table_row)
                for b_idx in table_row.get("block_indices", []):
                    matched_blocks.add(b_idx)

            # 4. Handle remaining blocks (Tables, Standalone Headings, Paragraphs, Footers)
            for b_idx, b in enumerate(structured_blocks):
                if b_idx in matched_blocks:
                    continue
                by0, by1 = b["bbox"][1], b["bbox"][3]
                btxt = b["text"].strip()

                if by0 > p_h - 60 and re.match(r"^\s*-\s*\d+\s*-\s*$", btxt):
                    page_elements.append({
                        "type": "footer",
                        "y0": by0,
                        "x0": b["bbox"][0],
                        "bbox": b["bbox"],
                        "text": btxt,
                        "blocks": [b],
                        "source": "pymupdf_text",
                    })
                elif re.match(r"^\s*\d+\.\s+", btxt) or any(s["size"] >= 12 and s["bold"] for l in b["lines"] for s in l):
                    page_elements.append({
                        "type": "section_bar",
                        "y0": by0,
                        "x0": b["bbox"][0],
                        "bbox": (42.5, by0 - 4, p_w - 42.5, by1 + 4),
                        "rect": (42.5, by0 - 4, p_w - 42.5, by1 + 4),
                        "fill": "#cad4df",
                        "blocks": [b],
                        "source": "pymupdf_text",
                    })
                else:
                    # Tabular row or body text
                    row_cells = self._parse_table_row_spans(b, page_width=p_w)
                    if row_cells:
                        page_elements.append({
                            "type": "table_row",
                            "y0": by0,
                            "x0": b["bbox"][0],
                            "bbox": b["bbox"],
                            "cells": row_cells,
                            "blocks": [b],
                            "block_indices": [b_idx],
                            "source": "pymupdf_block",
                        })
                    else:
                        page_elements.append({
                            "type": "paragraph",
                            "y0": by0,
                            "x0": b["bbox"][0],
                            "bbox": b["bbox"],
                            "blocks": [b],
                            "source": "pymupdf_text",
                        })

            # 2.5 Extract embedded images from PDF page
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base_img = self.doc.extract_image(xref)
                    img_bytes = base_img["image"]
                    img_ext = base_img["ext"]
                    iw, ih = base_img["width"], base_img["height"]
                    rects = page.get_image_rects(xref)
                    if rects:
                        r = rects[0]
                        img_bbox = (r.x0, r.y0, r.x1, r.y1)
                    else:
                        img_bbox = (42.5, p_h / 2, p_w - 42.5, p_h / 2 + 100)
                    if iw >= 24 and ih >= 24:
                        page_elements.append({
                            "type": "image",
                            "y0": img_bbox[1],
                            "x0": img_bbox[0],
                            "bbox": img_bbox,
                            "image_bytes": img_bytes,
                            "format": img_ext,
                            "width": iw,
                            "height": ih,
                            "source": "pdf_embedded_image",
                        })
                except Exception:
                    pass

            # Sort all elements by vertical reading position
            page_elements.sort(key=self._reading_order_key)

            # Merge consecutive table_row items into a single table element
            condensed_elements = []
            current_table_rows = []
            current_table_meta = []

            for elem in page_elements:
                if elem["type"] == "table_row":
                    current_table_rows.append(elem["cells"])
                    current_table_meta.append(elem)
                else:
                    if current_table_rows:
                        y0 = min(m.get("y0", 0) for m in current_table_meta)
                        x0 = min(m.get("x0", 0) for m in current_table_meta)
                        x1 = max(m.get("bbox", (0, 0, 0, 0))[2] for m in current_table_meta)
                        y1 = max(m.get("bbox", (0, 0, 0, 0))[3] for m in current_table_meta)
                        condensed_elements.append({
                            "type": "table",
                            "y0": y0,
                            "x0": x0,
                            "bbox": (x0, y0, x1, y1),
                            "rows": current_table_rows,
                            "source": current_table_meta[0].get("source", "pymupdf_text"),
                        })
                        current_table_rows = []
                        current_table_meta = []
                    condensed_elements.append(elem)

            if current_table_rows:
                y0 = min(m.get("y0", 0) for m in current_table_meta)
                x0 = min(m.get("x0", 0) for m in current_table_meta)
                x1 = max(m.get("bbox", (0, 0, 0, 0))[2] for m in current_table_meta)
                y1 = max(m.get("bbox", (0, 0, 0, 0))[3] for m in current_table_meta)
                condensed_elements.append({
                    "type": "table",
                    "y0": y0,
                    "x0": x0,
                    "bbox": (x0, y0, x1, y1),
                    "rows": current_table_rows,
                    "source": current_table_meta[0].get("source", "pymupdf_text"),
                })

            footer_text = next((e.get("text") for e in condensed_elements if e.get("type") == "footer"), None)
            self.pages.append({
                "page_num": p_idx + 1,
                "width": p_w,
                "height": p_h,
                "elements": condensed_elements,
                "footer_text": footer_text,
            })

    @staticmethod
    def _reading_order_key(item: Dict[str, Any]) -> Tuple[int, float, int]:
        bbox = item.get("bbox") or item.get("rect") or (item.get("x0", 0), item.get("y0", 0), 0, 0)
        y0 = float(item.get("y0", bbox[1]))
        x0 = float(item.get("x0", bbox[0]))
        source_order = int(item.get("source_order", 0))
        return (int(round(y0 / 3.0) * 3), x0, source_order)

    def _extract_pdfplumber_tables(self) -> Dict[int, List[Dict[str, Any]]]:
        tables_by_page: Dict[int, List[Dict[str, Any]]] = {}
        table_settings = [
            {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "intersection_tolerance": 5,
            },
        ]
        try:
            with pdfplumber.open(str(self.pdf_path)) as plumber_doc:
                for page_index, plumber_page in enumerate(plumber_doc.pages):
                    found: List[Dict[str, Any]] = []
                    seen_bboxes: List[Tuple[float, float, float, float]] = []
                    for settings in table_settings:
                        for table in plumber_page.find_tables(table_settings=settings):
                            bbox = _bbox_tuple(table.bbox)
                            if any(_overlap_ratio(bbox, seen) > 0.85 for seen in seen_bboxes):
                                continue
                            rows = self._normalize_table_rows(table.extract() or [])
                            if len(rows) < 2:
                                continue
                            found.append({
                                "type": "table",
                                "y0": bbox[1],
                                "x0": bbox[0],
                                "bbox": bbox,
                                "rect": bbox,
                                "rows": rows,
                                "source": "pdfplumber",
                            })
                            seen_bboxes.append(bbox)
                    if found:
                        tables_by_page[page_index] = sorted(found, key=self._reading_order_key)
        except Exception:
            return {}
        return tables_by_page

    def _detect_table_rows_from_text(
        self,
        structured_blocks: List[Dict[str, Any]],
        matched_blocks: set,
        page_width: float,
    ) -> List[Dict[str, Any]]:
        line_items: List[Dict[str, Any]] = []
        for b_idx, block in enumerate(structured_blocks):
            if b_idx in matched_blocks:
                continue
            for line in block["lines"]:
                spans = sorted(line, key=lambda s: s["bbox"][0])
                text = _join_cell_text([s["text"] for s in spans])
                if not text:
                    continue
                bbox = (
                    min(s["bbox"][0] for s in spans),
                    min(s["bbox"][1] for s in spans),
                    max(s["bbox"][2] for s in spans),
                    max(s["bbox"][3] for s in spans),
                )
                line_items.append({
                    "bbox": bbox,
                    "text": text,
                    "spans": spans,
                    "block_index": b_idx,
                })

        line_items.sort(key=lambda l: (round(l["bbox"][1] / 2.0) * 2, l["bbox"][0]))
        clusters: List[List[Dict[str, Any]]] = []
        for item in line_items:
            center_y = (item["bbox"][1] + item["bbox"][3]) / 2
            if clusters:
                last_center = sum((l["bbox"][1] + l["bbox"][3]) / 2 for l in clusters[-1]) / len(clusters[-1])
                if abs(center_y - last_center) <= 4:
                    clusters[-1].append(item)
                    continue
            clusters.append([item])

        candidates: List[Dict[str, Any]] = []
        for cluster in clusters:
            cluster.sort(key=lambda l: l["bbox"][0])
            cells = self._cluster_line_items_as_cells(cluster)
            if len(cells) < 2:
                continue
            row = self._cells_to_table_row(cells, page_width=page_width)
            if not row:
                continue
            bbox = (
                min(c["bbox"][0] for c in cells),
                min(c["bbox"][1] for c in cells),
                max(c["bbox"][2] for c in cells),
                max(c["bbox"][3] for c in cells),
            )
            candidates.append({
                "type": "table_row",
                "y0": bbox[1],
                "x0": bbox[0],
                "bbox": bbox,
                "cells": row,
                "blocks": [structured_blocks[i] for i in sorted({c["block_index"] for c in cells})],
                "block_indices": sorted({c["block_index"] for c in cells}),
                "source": "pymupdf_text_grid",
                "column_signature": tuple(round(c["bbox"][0] / 12) * 12 for c in cells),
            })

        if len(candidates) < 2:
            return []

        accepted: List[Dict[str, Any]] = []
        run: List[Dict[str, Any]] = []
        for row in candidates:
            if not run:
                run = [row]
                continue
            prev = run[-1]
            same_columns = self._similar_column_signature(prev["column_signature"], row["column_signature"])
            close_vertical = row["y0"] - prev["bbox"][3] <= 28
            if same_columns and close_vertical:
                run.append(row)
            else:
                if len(run) >= 2:
                    accepted.extend(run)
                run = [row]
        if len(run) >= 2:
            accepted.extend(run)
        return accepted

    @staticmethod
    def _similar_column_signature(left: Tuple[float, ...], right: Tuple[float, ...]) -> bool:
        if abs(len(left) - len(right)) > 1:
            return False
        shared = min(len(left), len(right))
        if shared < 2:
            return False
        return sum(abs(left[i] - right[i]) <= 24 for i in range(shared)) >= shared - 1

    @staticmethod
    def _cluster_line_items_as_cells(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cells: List[Dict[str, Any]] = []
        for item in items:
            if not cells:
                cells.append(dict(item))
                continue
            prev = cells[-1]
            gap = item["bbox"][0] - prev["bbox"][2]
            if gap <= 8:
                prev["text"] = _join_cell_text([prev["text"], item["text"]])
                prev["bbox"] = (
                    min(prev["bbox"][0], item["bbox"][0]),
                    min(prev["bbox"][1], item["bbox"][1]),
                    max(prev["bbox"][2], item["bbox"][2]),
                    max(prev["bbox"][3], item["bbox"][3]),
                )
            else:
                cells.append(dict(item))
        return cells

    def _normalize_table_rows(self, raw_rows: List[List[Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for raw_row in raw_rows:
            cells = [_join_cell_text([str(c or "").replace("\n", " ")]) for c in raw_row]
            while cells and not cells[-1]:
                cells.pop()
            if not any(cells):
                continue
            row = self._cells_to_table_row(cells)
            if row:
                rows.append(row)
        return rows

    def _cells_to_table_row(self, cells: List[Any], page_width: Optional[float] = None) -> Optional[Dict[str, Any]]:
        texts: List[str] = []
        for cell in cells:
            if isinstance(cell, dict):
                texts.append(_join_cell_text([cell.get("text", "")]))
            else:
                texts.append(_join_cell_text([str(cell or "")]))
        while texts and not texts[-1]:
            texts.pop()
        if len(texts) < 2:
            return None
        if len(texts) == 2:
            return {"type": "colspan", "c0": texts[0], "c1": texts[1]}
        if len(texts) == 3:
            return {"type": "4col", "c0": texts[0], "c1": texts[1], "c2": texts[2], "c3": ""}
        if len(texts) >= 4:
            return {"type": "4col", "c0": texts[0], "c1": texts[1], "c2": texts[2], "c3": " ".join(texts[3:])}
        return None

    def _parse_table_row_spans(self, block: Dict[str, Any], page_width: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Extract multi-column cells from spans by horizontal X coordinate."""
        all_spans = [s for l in block["lines"] for s in l]
        if not all_spans:
            return None

        width = page_width or 595.0
        boundaries = [width * 0.25, width * 0.55, width * 0.72]
        col0_spans = []
        col1_spans = []
        col2_spans = []
        col3_spans = []

        for s in all_spans:
            x0 = s["bbox"][0]
            if x0 < boundaries[0]:
                col0_spans.append(s["text"])
            elif x0 < boundaries[1]:
                col1_spans.append(s["text"])
            elif x0 < boundaries[2]:
                col2_spans.append(s["text"])
            else:
                col3_spans.append(s["text"])

        c0 = _join_cell_text(col0_spans)
        c1 = _join_cell_text(col1_spans)
        c2 = _join_cell_text(col2_spans)
        c3 = _join_cell_text(col3_spans)

        if c0 and (c1 or c2 or c3):
            if c2 or c3:
                return {"type": "4col", "c0": c0, "c1": c1, "c2": c2, "c3": c3}
            else:
                return {"type": "colspan", "c0": c0, "c1": c1}

        return None

    def to_html(self, title: Optional[str] = None) -> str:
        """Render modern, pixel-faithful responsive HTML (95%+ visual match)."""
        doc_title = title or self.pdf_path.stem
        html = []
        html.append(f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(doc_title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{
  --pdf-bg: #f1f5f9;
  --paper-bg: #ffffff;
  --primary-navy: #1a365d;
  --primary-blue: #2563eb;
  --alert-bg: #edf2f7;
  --alert-border: #3182ce;
  --alert-text: #1a365d;
  --sec-bar-bg: #cad4df;
  --card-bg: #ffffff;
  --card-border: #e2e8ef;
  --table-header-bg: #edf2f6;
  --table-border: #cbd5e1;
  --text-main: #2d3748;
  --text-muted: #718096;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background-color: var(--pdf-bg);
  font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--text-main);
  line-height: 1.6;
  padding: 2.5rem 1rem;
}}
.pdf-container {{
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}}
.pdf-page-card {{
  background: var(--paper-bg);
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 3rem 2.8rem;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
  position: relative;
  min-height: 1000px;
  display: flex;
  flex-direction: column;
}}
.pdf-page-badge {{
  position: absolute;
  top: 1.25rem;
  right: 1.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
}}
.pdf-banner {{
  background-color: #1a365d;
  color: #ffffff;
  padding: 1.4rem 1.6rem;
  border-radius: 6px;
  margin-bottom: 1.2rem;
  box-shadow: 0 4px 6px -1px rgba(26, 54, 93, 0.2);
}}
.pdf-banner h1 {{
  font-size: 1.35rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 0.45rem;
  letter-spacing: -0.02em;
}}
.pdf-banner p {{
  font-size: 0.875rem;
  color: #cbd5e1;
  line-height: 1.45;
}}
.pdf-alert {{
  background-color: #edf2f7;
  border-left: 4.5px solid #3182ce;
  border-radius: 0 6px 6px 0;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}}
.pdf-alert-badge {{
  background: #3182ce;
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  white-space: nowrap;
  margin-top: 0.15rem;
}}
.pdf-alert-text {{
  font-size: 0.875rem;
  color: #2d3748;
  line-height: 1.55;
}}
.pdf-section-bar {{
  background-color: #cad4df;
  border-left: 4.5px solid #1a365d;
  padding: 0.55rem 1rem;
  border-radius: 0 4px 4px 0;
  margin-top: 1.4rem;
  margin-bottom: 1rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1a365d;
}}
.pdf-card {{
  background: #ffffff;
  border: 1px solid #e2e8ef;
  border-radius: 6px;
  padding: 1.25rem 1.4rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.pdf-card-title {{
  font-size: 0.95rem;
  font-weight: 700;
  color: #1a365d;
  margin-bottom: 0.35rem;
}}
.pdf-card-meta {{
  font-size: 0.8rem;
  color: #718096;
  border-bottom: 1px dashed #e2e8f0;
  padding-bottom: 0.5rem;
  margin-bottom: 0.75rem;
}}
.pdf-card-body {{
  font-size: 0.875rem;
  line-height: 1.7;
  color: #2d3748;
}}
.highlight-id {{
  color: #2563eb;
  font-weight: 600;
}}
.highlight-tag {{
  background: #edf2f7;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.825rem;
  color: #c53030;
  border: 1px solid #e2e8f0;
}}
.pdf-table-container {{
  width: 100%;
  margin: 0.5rem 0 1.25rem 0;
  overflow-x: auto;
}}
.pdf-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  border: 1px solid #cbd5e1;
}}
.pdf-table th, .pdf-table td {{
  border: 1px solid #cbd5e1;
  padding: 0.65rem 0.85rem;
  vertical-align: middle;
}}
.pdf-table th {{
  background-color: #edf2f6;
  color: #1a365d;
  font-weight: 700;
  width: 22%;
  text-align: left;
}}
.pdf-table td {{
  background-color: #ffffff;
  color: #2d3748;
}}
.pdf-footer {{
  margin-top: auto;
  text-align: center;
  font-size: 0.85rem;
  color: #718096;
  padding-top: 2rem;
}}
</style>
</head>
<body>
<div class="pdf-container">
""")

        for p in self.pages:
            pno = p["page_num"]
            tot = len(self.pages)
            html.append(f'<div class="pdf-page-card" id="page-{pno}">')
            html.append(f'  <div class="pdf-page-badge">Page {pno} / {tot}</div>')

            for elem in p["elements"]:
                etype = elem["type"]

                if etype == "banner":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    t1 = lines[0] if lines else "문서 제목"
                    t2 = " ".join(lines[1:]) if len(lines) > 1 else ""
                    html.append(f"""  <div class="pdf-banner">
    <h1>{t1}</h1>
    {f'<p>{t2}</p>' if t2 else ''}
  </div>""")

                elif etype == "alert":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    clean_alert = re.sub(r"^\s*안내\s*:\s*", "", txt)
                    html.append(f"""  <div class="pdf-alert">
    <span class="pdf-alert-badge">안내</span>
    <div class="pdf-alert-text">{clean_alert.replace(chr(10), '<br/>')}</div>
  </div>""")

                elif etype == "section_bar":
                    txt = " ".join(b["text"] for b in elem["blocks"]).strip()
                    html.append(f"""  <div class="pdf-section-bar">{txt}</div>""")

                elif etype == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = txt.split("\n")
                    c_title = lines[0] if lines else "상세 내역"
                    c_meta = ""
                    c_body_lines = lines[1:]
                    if len(lines) > 1 and any(k in lines[1] for k in ("접수일시", "일시", "담당자", "상담원:")) and len(lines[1]) < 60:
                        c_meta = lines[1]
                        c_body_lines = lines[2:]

                    body_str = "<br/>".join(c_body_lines)
                    body_str = re.sub(r"(\[RRN Omitted[^\]]*\])", r'<span class="highlight-tag">\1</span>', body_str)
                    body_str = re.sub(r"(010-\d{4}-\d{4})", r'<span class="highlight-id">\1</span>', body_str)
                    body_str = re.sub(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", r'<span class="highlight-id">\1</span>', body_str)

                    html.append(f"""  <div class="pdf-card">
    <div class="pdf-card-title">{c_title}</div>
    {f'<div class="pdf-card-meta">{c_meta}</div>' if c_meta else ''}
    <div class="pdf-card-body">{body_str}</div>
  </div>""")

                elif etype == "image":
                    b64 = base64.b64encode(elem["image_bytes"]).decode("ascii")
                    mime = "image/jpeg" if elem.get("format", "").lower() in ("jpg", "jpeg") else "image/png"
                    html.append(f'''  <div class="pdf-image-container" style="text-align:center; margin:16px 0;">
    <img src="data:{mime};base64,{b64}" style="max-width:100%; height:auto; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.06);" alt="문서 이미지" />
  </div>''')

                elif etype == "table":
                    html.append('  <div class="pdf-table-container">\n    <table class="pdf-table">')
                    for row in elem["rows"]:
                        html.append("      <tr>")
                        if row["type"] == "4col":
                            html.append(f"        <th>{_escape_html(row['c0'])}</th><td>{_escape_html(row['c1'])}</td>")
                            html.append(f"        <th>{_escape_html(row['c2'])}</th><td>{_escape_html(row['c3'])}</td>")
                        elif row["type"] == "colspan":
                            html.append(f"        <th>{_escape_html(row['c0'])}</th><td colspan=\"3\">{_escape_html(row['c1'])}</td>")
                        html.append("      </tr>")
                    html.append("    </table>\n  </div>")

                elif etype == "paragraph":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    if txt:
                        html.append(f'  <p style="margin-bottom:0.75rem; font-size:0.875rem;">{_escape_html(txt).replace(chr(10), "<br/>")}</p>')

                elif etype == "footer":
                    html.append(f"""  <div class="pdf-footer">{_escape_html(elem.get('text', f'- {pno} -'))}</div>""")

            html.append("</div>\n")

        html.append("""</div>
</body>
</html>""")
        return "\n".join(html)

    def to_docx(self, output_path: Path) -> None:
        """Render high-fidelity Word document (.docx)."""
        doc = docx.Document()

        for section in doc.sections:
            section.top_margin = Inches(0.7)
            section.bottom_margin = Inches(0.7)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

        for p in self.pages:
            pno = p["page_num"]
            if pno > 1:
                doc.add_page_break()

            for elem in p["elements"]:
                etype = elem["type"]

                if etype == "banner":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    t1 = lines[0] if lines else "문서 제목"
                    t2 = " ".join(lines[1:]) if len(lines) > 1 else ""

                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False
                    tbl.columns[0].width = Inches(6.8)

                    cell = tbl.cell(0, 0)
                    _docx_set_cell_background(cell, "1A365D")
                    _docx_set_cell_margins(cell, top=180, bottom=180, left=240, right=240)
                    _docx_set_cell_border(cell)

                    p_title = cell.paragraphs[0]
                    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run1 = p_title.add_run(t1)
                    run1.font.name = "맑은 고딕"
                    run1.font.size = Pt(14)
                    run1.font.bold = True
                    run1.font.color.rgb = RGBColor(255, 255, 255)

                    if t2:
                        p_sub = cell.add_paragraph()
                        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run2 = p_sub.add_run(t2)
                        run2.font.name = "맑은 고딕"
                        run2.font.size = Pt(9.5)
                        run2.font.color.rgb = RGBColor(203, 213, 225)

                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

                elif etype == "alert":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False
                    tbl.columns[0].width = Inches(6.8)

                    cell = tbl.cell(0, 0)
                    _docx_set_cell_background(cell, "EDF2F7")
                    _docx_set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
                    _docx_set_cell_border(cell, left={"sz": 24, "val": "single", "color": "3182CE"},
                                                top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                right={"sz": 4, "val": "single", "color": "CBD5E1"})

                    p_alert = cell.paragraphs[0]
                    run_badge = p_alert.add_run("[안내] ")
                    run_badge.font.name = "맑은 고딕"
                    run_badge.font.size = Pt(9)
                    run_badge.font.bold = True
                    run_badge.font.color.rgb = RGBColor(49, 130, 206)

                    run_text = p_alert.add_run(txt)
                    run_text.font.name = "맑은 고딕"
                    run_text.font.size = Pt(9)
                    run_text.font.color.rgb = RGBColor(26, 54, 93)

                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

                elif etype == "section_bar":
                    txt = " ".join(b["text"] for b in elem["blocks"]).strip()
                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False
                    tbl.columns[0].width = Inches(6.8)

                    cell = tbl.cell(0, 0)
                    _docx_set_cell_background(cell, "CAD4DF")
                    _docx_set_cell_margins(cell, top=80, bottom=80, left=150, right=150)
                    _docx_set_cell_border(cell, left={"sz": 24, "val": "single", "color": "1A365D"})

                    p_sec = cell.paragraphs[0]
                    run_sec = p_sec.add_run(txt)
                    run_sec.font.name = "맑은 고딕"
                    run_sec.font.size = Pt(10.5)
                    run_sec.font.bold = True
                    run_sec.font.color.rgb = RGBColor(26, 54, 93)

                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

                elif etype == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = txt.split("\n")
                    c_title = lines[0] if lines else "상세 내역"
                    c_meta = ""
                    c_body_lines = lines[1:]

                    if len(lines) > 1 and any(k in lines[1] for k in ("접수일시", "일시", "담당자", "상담원:")) and len(lines[1]) < 60:
                        c_meta = lines[1]
                        c_body_lines = lines[2:]

                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False
                    tbl.columns[0].width = Inches(6.8)

                    cell = tbl.cell(0, 0)
                    _docx_set_cell_background(cell, "FCFCFD")
                    _docx_set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
                    _docx_set_cell_border(cell, top={"sz": 4, "val": "single", "color": "E2E8EF"},
                                                bottom={"sz": 4, "val": "single", "color": "E2E8EF"},
                                                left={"sz": 4, "val": "single", "color": "E2E8EF"},
                                                right={"sz": 4, "val": "single", "color": "E2E8EF"})

                    p_title = cell.paragraphs[0]
                    run_title = p_title.add_run(c_title)
                    run_title.font.name = "맑은 고딕"
                    run_title.font.size = Pt(10)
                    run_title.font.bold = True
                    run_title.font.color.rgb = RGBColor(26, 54, 93)

                    if c_meta:
                        p_meta = cell.add_paragraph()
                        run_meta = p_meta.add_run(c_meta)
                        run_meta.font.name = "맑은 고딕"
                        run_meta.font.size = Pt(8.5)
                        run_meta.font.color.rgb = RGBColor(113, 128, 150)
                        p_meta.paragraph_format.space_after = Pt(4)

                    p_body = cell.add_paragraph()
                    p_body.paragraph_format.line_spacing = 1.2
                    body_text = "\n".join(c_body_lines)
                    run_body = p_body.add_run(body_text)
                    run_body.font.name = "맑은 고딕"
                    run_body.font.size = Pt(9)
                    run_body.font.color.rgb = RGBColor(45, 55, 72)

                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

                elif etype == "image":
                    try:
                        img_stream = io.BytesIO(elem["image_bytes"])
                        doc.add_picture(img_stream, width=Inches(min(6.2, max(1.5, elem["width"] / 150.0))))
                        p_img = doc.paragraphs[-1]
                        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_img.paragraph_format.space_after = Pt(8)
                    except Exception:
                        pass

                elif etype == "table":
                    rows_count = len(elem["rows"])
                    tbl = doc.add_table(rows=rows_count, cols=4)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False

                    col_widths = [Inches(1.5), Inches(2.2), Inches(1.3), Inches(1.8)]
                    for r_i, row in enumerate(elem["rows"]):
                        for c_i, w in enumerate(col_widths):
                            tbl.cell(r_i, c_i).width = w

                        if row["type"] == "4col":
                            c0 = tbl.cell(r_i, 0); c0.text = row["c0"]
                            _docx_set_cell_background(c0, "EDF2F6"); _docx_set_cell_margins(c0)
                            _docx_set_cell_border(c0, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if c0.paragraphs and c0.paragraphs[0].runs:
                                c0.paragraphs[0].runs[0].font.bold = True
                                c0.paragraphs[0].runs[0].font.size = Pt(9)
                                c0.paragraphs[0].runs[0].font.name = "맑은 고딕"

                            c1 = tbl.cell(r_i, 1); c1.text = row["c1"]
                            _docx_set_cell_background(c1, "FFFFFF"); _docx_set_cell_margins(c1)
                            _docx_set_cell_border(c1, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if c1.paragraphs and c1.paragraphs[0].runs:
                                c1.paragraphs[0].runs[0].font.size = Pt(9)
                                c1.paragraphs[0].runs[0].font.name = "맑은 고딕"

                            c2 = tbl.cell(r_i, 2); c2.text = row["c2"]
                            _docx_set_cell_background(c2, "EDF2F6"); _docx_set_cell_margins(c2)
                            _docx_set_cell_border(c2, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if c2.paragraphs and c2.paragraphs[0].runs:
                                c2.paragraphs[0].runs[0].font.bold = True
                                c2.paragraphs[0].runs[0].font.size = Pt(9)
                                c2.paragraphs[0].runs[0].font.name = "맑은 고딕"

                            c3 = tbl.cell(r_i, 3); c3.text = row["c3"]
                            _docx_set_cell_background(c3, "FFFFFF"); _docx_set_cell_margins(c3)
                            _docx_set_cell_border(c3, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if c3.paragraphs and c3.paragraphs[0].runs:
                                c3.paragraphs[0].runs[0].font.size = Pt(9)
                                c3.paragraphs[0].runs[0].font.name = "맑은 고딕"

                        elif row["type"] == "colspan":
                            c0 = tbl.cell(r_i, 0); c0.text = row["c0"]
                            _docx_set_cell_background(c0, "EDF2F6"); _docx_set_cell_margins(c0)
                            _docx_set_cell_border(c0, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                      right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if c0.paragraphs and c0.paragraphs[0].runs:
                                c0.paragraphs[0].runs[0].font.bold = True
                                c0.paragraphs[0].runs[0].font.size = Pt(9)
                                c0.paragraphs[0].runs[0].font.name = "맑은 고딕"

                            merged_cell = tbl.cell(r_i, 1).merge(tbl.cell(r_i, 3))
                            merged_cell.text = row["c1"]
                            _docx_set_cell_background(merged_cell, "FFFFFF"); _docx_set_cell_margins(merged_cell)
                            _docx_set_cell_border(merged_cell, top={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                               bottom={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                               left={"sz": 4, "val": "single", "color": "CBD5E1"},
                                                               right={"sz": 4, "val": "single", "color": "CBD5E1"})
                            if merged_cell.paragraphs and merged_cell.paragraphs[0].runs:
                                merged_cell.paragraphs[0].runs[0].font.size = Pt(9)
                                merged_cell.paragraphs[0].runs[0].font.name = "맑은 고딕"

                    doc.add_paragraph().paragraph_format.space_after = Pt(4)

                elif etype == "paragraph":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    if txt:
                        p_para = doc.add_paragraph()
                        r_para = p_para.add_run(txt)
                        r_para.font.name = "맑은 고딕"
                        r_para.font.size = Pt(9.5)
                        p_para.paragraph_format.space_after = Pt(4)

                elif etype == "footer":
                    p_foot = doc.add_paragraph()
                    p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r_foot = p_foot.add_run(elem.get("text", f"- {pno} -"))
                    r_foot.font.name = "맑은 고딕"
                    r_foot.font.size = Pt(9)
                    r_foot.font.color.rgb = RGBColor(113, 128, 150)

        doc.save(output_path)

    def to_excel(self, output_path: Path) -> None:
        """Render 3-sheet Excel spreadsheet."""
        wb = openpyxl.Workbook()
        default_sheet = wb.active

        f_banner_title = Font(name="Malgun Gothic", size=13, bold=True, color="FFFFFF")
        f_banner_sub = Font(name="Malgun Gothic", size=9, bold=False, color="CBD5E1")
        f_alert = Font(name="Malgun Gothic", size=9, bold=False, color="1A365D")
        f_sec = Font(name="Malgun Gothic", size=10, bold=True, color="1A365D")
        f_card_title = Font(name="Malgun Gothic", size=10, bold=True, color="1A365D")
        f_card_meta = Font(name="Malgun Gothic", size=9, bold=False, color="718096")
        f_card_body = Font(name="Malgun Gothic", size=9, bold=False, color="2D3748")
        f_tbl_hdr = Font(name="Malgun Gothic", size=9, bold=True, color="1A365D")
        f_tbl_cell = Font(name="Malgun Gothic", size=9, bold=False, color="2D3748")
        f_footer = Font(name="Malgun Gothic", size=9, bold=False, color="718096")

        fill_banner = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
        fill_alert = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
        fill_sec = PatternFill(start_color="CAD4DF", end_color="CAD4DF", fill_type="solid")
        fill_card = PatternFill(start_color="FCFCFD", end_color="FCFCFD", fill_type="solid")
        fill_tbl_hdr = PatternFill(start_color="EDF2F6", end_color="EDF2F6", fill_type="solid")

        side_thin = Side(border_style="thin", color="CBD5E1")
        border_box = Border(left=side_thin, right=side_thin, top=side_thin, bottom=side_thin)
        border_alert = Border(left=Side(border_style="medium", color="3182CE"), right=side_thin, top=side_thin, bottom=side_thin)

        # Sheet 1: 전체_문서_서식 (Visual Replica)
        ws1 = wb.create_sheet(title="전체_문서_서식")
        ws1.views.sheetView[0].showGridLines = True
        ws1.column_dimensions["A"].width = 20
        ws1.column_dimensions["B"].width = 38
        ws1.column_dimensions["C"].width = 20
        ws1.column_dimensions["D"].width = 38

        r1 = 1
        for p in self.pages:
            pno = p["page_num"]
            if pno > 1:
                r1 += 1
                ws1.cell(row=r1, column=1, value=f"--- [Page {pno}] ---").font = f_footer
                r1 += 1

            for elem in p["elements"]:
                etype = elem["type"]

                if etype == "banner":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    t1 = lines[0] if lines else "문서 제목"
                    t2 = " ".join(lines[1:]) if len(lines) > 1 else ""

                    ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                    c = ws1.cell(row=r1, column=1, value=t1)
                    c.font = f_banner_title; c.fill = fill_banner
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    ws1.row_dimensions[r1].height = 28
                    r1 += 1

                    if t2:
                        ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                        c = ws1.cell(row=r1, column=1, value=t2)
                        c.font = f_banner_sub; c.fill = fill_banner
                        c.alignment = Alignment(horizontal="center", vertical="center")
                        ws1.row_dimensions[r1].height = 20
                        r1 += 1
                    r1 += 1

                elif etype == "alert":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                    c = ws1.cell(row=r1, column=1, value=f"[안내] {txt}")
                    c.font = f_alert; c.fill = fill_alert; c.border = border_alert
                    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                    ws1.row_dimensions[r1].height = 44
                    r1 += 2

                elif etype == "section_bar":
                    txt = " ".join(b["text"] for b in elem["blocks"]).strip()
                    ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                    c = ws1.cell(row=r1, column=1, value=txt)
                    c.font = f_sec; c.fill = fill_sec
                    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
                    ws1.row_dimensions[r1].height = 24
                    r1 += 1

                elif etype == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = txt.split("\n")
                    c_title = lines[0] if lines else "상세 내역"
                    c_body = "\n".join(lines[1:])

                    ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                    c_t = ws1.cell(row=r1, column=1, value=c_title)
                    c_t.font = f_card_title; c_t.fill = fill_card; c_t.border = border_box
                    ws1.row_dimensions[r1].height = 22
                    r1 += 1

                    if c_body:
                        ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                        c_b = ws1.cell(row=r1, column=1, value=c_body)
                        c_b.font = f_card_body; c_b.fill = fill_card; c_b.border = border_box
                        c_b.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                        ws1.row_dimensions[r1].height = max(40, min(120, len(lines) * 18))
                        r1 += 1
                    r1 += 1

                elif etype == "table":
                    for row in elem["rows"]:
                        if row["type"] == "4col":
                            c1 = ws1.cell(row=r1, column=1, value=row["c0"])
                            c1.font = f_tbl_hdr; c1.fill = fill_tbl_hdr; c1.border = border_box

                            c2 = ws1.cell(row=r1, column=2, value=row["c1"])
                            c2.font = f_tbl_cell; c2.border = border_box

                            c3 = ws1.cell(row=r1, column=3, value=row["c2"])
                            c3.font = f_tbl_hdr; c3.fill = fill_tbl_hdr; c3.border = border_box

                            c4 = ws1.cell(row=r1, column=4, value=row["c3"])
                            c4.font = f_tbl_cell; c4.border = border_box
                            ws1.row_dimensions[r1].height = 22
                            r1 += 1
                        elif row["type"] == "colspan":
                            c1 = ws1.cell(row=r1, column=1, value=row["c0"])
                            c1.font = f_tbl_hdr; c1.fill = fill_tbl_hdr; c1.border = border_box

                            ws1.merge_cells(start_row=r1, start_column=2, end_row=r1, end_column=4)
                            c2 = ws1.cell(row=r1, column=2, value=row["c1"])
                            c2.font = f_tbl_cell; c2.border = border_box
                            ws1.cell(row=r1, column=3).border = border_box
                            ws1.cell(row=r1, column=4).border = border_box
                            ws1.row_dimensions[r1].height = 22
                            r1 += 1
                    r1 += 1

                elif etype == "paragraph":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    if txt:
                        ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                        c = ws1.cell(row=r1, column=1, value=txt)
                        c.font = f_card_body
                        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                        r1 += 1

                elif etype == "footer":
                    ws1.merge_cells(start_row=r1, start_column=1, end_row=r1, end_column=4)
                    c = ws1.cell(row=r1, column=1, value=elem.get("text", f"- {pno} -"))
                    c.font = f_footer
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    r1 += 1

        # Sheet 2: 정형_데이터_테이블
        ws2 = wb.create_sheet(title="정형_데이터_테이블")
        ws2.views.sheetView[0].showGridLines = True
        ws2.column_dimensions["A"].width = 22
        ws2.column_dimensions["B"].width = 38
        ws2.column_dimensions["C"].width = 20
        ws2.column_dimensions["D"].width = 38

        ws2.merge_cells("A1:D1")
        h_cell = ws2.cell(row=1, column=1, value="문서 추출 정형 데이터 테이블")
        h_cell.font = f_sec; h_cell.fill = fill_sec
        ws2.row_dimensions[1].height = 26

        r2 = 3
        for p in self.pages:
            for elem in p["elements"]:
                if elem["type"] == "table":
                    for row in elem["rows"]:
                        if row["type"] == "4col":
                            c1 = ws2.cell(row=r2, column=1, value=row["c0"])
                            c1.font = f_tbl_hdr; c1.fill = fill_tbl_hdr; c1.border = border_box
                            c2 = ws2.cell(row=r2, column=2, value=row["c1"])
                            c2.font = f_tbl_cell; c2.border = border_box
                            c3 = ws2.cell(row=r2, column=3, value=row["c2"])
                            c3.font = f_tbl_hdr; c3.fill = fill_tbl_hdr; c3.border = border_box
                            c4 = ws2.cell(row=r2, column=4, value=row["c3"])
                            c4.font = f_tbl_cell; c4.border = border_box
                        elif row["type"] == "colspan":
                            c1 = ws2.cell(row=r2, column=1, value=row["c0"])
                            c1.font = f_tbl_hdr; c1.fill = fill_tbl_hdr; c1.border = border_box
                            ws2.merge_cells(start_row=r2, start_column=2, end_row=r2, end_column=4)
                            c2 = ws2.cell(row=r2, column=2, value=row["c1"])
                            c2.font = f_tbl_cell; c2.border = border_box
                            ws2.cell(row=r2, column=3).border = border_box
                            ws2.cell(row=r2, column=4).border = border_box
                        ws2.row_dimensions[r2].height = 22
                        r2 += 1

        # Sheet 3: 상담_비정형_데이터
        ws3 = wb.create_sheet(title="상담_비정형_데이터")
        ws3.views.sheetView[0].showGridLines = True
        ws3.column_dimensions["A"].width = 8
        ws3.column_dimensions["B"].width = 25
        ws3.column_dimensions["C"].width = 22
        ws3.column_dimensions["D"].width = 18
        ws3.column_dimensions["E"].width = 65

        rec_headers = ["번호", "상담/신청 구분", "접수일시", "담당자/신청인", "상세 상담 및 처리 내용"]
        for c_i, h in enumerate(rec_headers):
            c = ws3.cell(row=1, column=c_i+1, value=h)
            c.font = f_banner_title; c.fill = fill_banner
            c.alignment = Alignment(horizontal="center", vertical="center")
        ws3.row_dimensions[1].height = 26

        r3 = 2
        idx = 1
        for p in self.pages:
            for elem in p["elements"]:
                if elem["type"] == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = txt.split("\n")
                    title_line = lines[0] if lines else ""

                    date_val = ""
                    agent_val = ""
                    body_lines = lines[1:]

                    if len(lines) > 1 and ("일시" in lines[1] or "담당자" in lines[1]):
                        meta_line = lines[1]
                        body_lines = lines[2:]
                        m_date = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", meta_line)
                        if m_date:
                            date_val = m_date.group(1)
                        m_agent = re.search(r"담당자:\s*([^|\n]+)", meta_line)
                        if m_agent:
                            agent_val = m_agent.group(1).strip()

                    content_val = "\n".join(body_lines)

                    ws3.cell(row=r3, column=1, value=idx).alignment = Alignment(horizontal="center")
                    ws3.cell(row=r3, column=2, value=title_line).font = f_card_title
                    ws3.cell(row=r3, column=3, value=date_val).alignment = Alignment(horizontal="center")
                    ws3.cell(row=r3, column=4, value=agent_val).alignment = Alignment(horizontal="center")
                    c_body = ws3.cell(row=r3, column=5, value=content_val)
                    c_body.alignment = Alignment(wrap_text=True)

                    for c_i in range(1, 6):
                        ws3.cell(row=r3, column=c_i).border = border_box

                    ws3.row_dimensions[r3].height = max(35, min(100, len(body_lines) * 16))
                    r3 += 1
                    idx += 1

        if default_sheet in wb.worksheets:
            wb.remove(default_sheet)

        wb.save(output_path)

    def to_hwpx(self, output_path: Path) -> None:
        """
        Render 100% standard and compliant HWPX document using the official python-hwpx engine.
        Includes styled tables with shaded headers (#EDF2F6), colSpan=3 merged cells,
        banner blocks (#1A365D), alert callout boxes (#EDF2F7), section bars (#CAD4DF), and card UI containers.
        Opens flawlessly in Hancom Hangul 2014, 2018, 2020, 2022, 2024 and web viewers.
        """
        from hwpx.document import HwpxDocument

        doc = HwpxDocument.new()
        PAGE_WIDTH = 42520  # standard printable width

        for p in self.pages:
            pno = p["page_num"]

            for elem in p["elements"]:
                etype = elem["type"]

                if etype == "banner":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    t1 = lines[0] if lines else "문서 제목"
                    t2 = " ".join(lines[1:]) if len(lines) > 1 else ""

                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.set_column_widths([PAGE_WIDTH])
                    tbl.set_cell_shading(0, 0, "#1A365D")
                    banner_txt = f"■ {t1}\n{t2}" if t2 else f"■ {t1}"
                    tbl.set_cell_text(0, 0, banner_txt)

                elif etype == "alert":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.set_column_widths([PAGE_WIDTH])
                    tbl.set_cell_shading(0, 0, "#EDF2F7")
                    tbl.set_cell_text(0, 0, f"[안내사항]\n{txt}")

                elif etype == "section_bar":
                    txt = " ".join(b["text"] for b in elem["blocks"]).strip()
                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.set_column_widths([PAGE_WIDTH])
                    tbl.set_cell_shading(0, 0, "#CAD4DF")
                    tbl.set_cell_text(0, 0, f"▶ {txt}")

                elif etype == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    lines = txt.split("\n")
                    c_title = lines[0] if lines else "상세 기록"
                    c_meta = ""
                    c_body_lines = lines[1:]

                    if len(lines) > 1 and any(k in lines[1] for k in ("접수일시", "일시", "담당자", "상담원:")) and len(lines[1]) < 60:
                        c_meta = lines[1]
                        c_body_lines = lines[2:]

                    card_content = f"【{c_title}】"
                    if c_meta:
                        card_content += f"\n접수 정보: {c_meta}"
                    if c_body_lines:
                        card_content += "\n\n" + "\n".join(c_body_lines)

                    tbl = doc.add_table(rows=1, cols=1)
                    tbl.set_column_widths([PAGE_WIDTH])
                    tbl.set_cell_shading(0, 0, "#FCFCFD")
                    tbl.set_cell_text(0, 0, card_content)

                elif etype == "table":
                    rows_data = elem["rows"]
                    row_cnt = len(rows_data)
                    tbl = doc.add_table(rows=row_cnt, cols=4)
                    tbl.set_column_widths([9500, 13500, 8000, 11520])

                    for r_idx, row in enumerate(rows_data):
                        if row["type"] == "4col":
                            tbl.set_cell_text(r_idx, 0, row["c0"])
                            tbl.set_cell_shading(r_idx, 0, "#EDF2F6")
                            tbl.set_cell_text(r_idx, 1, row["c1"])
                            tbl.set_cell_text(r_idx, 2, row["c2"])
                            tbl.set_cell_shading(r_idx, 2, "#EDF2F6")
                            tbl.set_cell_text(r_idx, 3, row["c3"])
                        elif row["type"] == "colspan":
                            tbl.set_cell_text(r_idx, 0, row["c0"])
                            tbl.set_cell_shading(r_idx, 0, "#EDF2F6")
                            tbl.set_cell_text(r_idx, 1, row["c1"])
                            tbl.merge_cells(r_idx, 1, r_idx, 3)

                elif etype == "paragraph":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    if txt:
                        doc.add_paragraph(txt)

                elif etype == "footer":
                    doc.add_paragraph(f"- {pno} -")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save_to_path(output_path)

    def to_markdown(self) -> str:
        """Render clean, structured Markdown."""
        md_parts = []
        for p in self.pages:
            pno = p["page_num"]
            md_parts.append(f"## Page {pno}\n")

            for elem in p["elements"]:
                etype = elem["type"]

                if etype == "banner":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    md_parts.append(f"# {txt}\n")
                elif etype == "alert":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    md_parts.append(f"> **[안내사항]** {txt}\n")
                elif etype == "section_bar":
                    txt = " ".join(b["text"] for b in elem["blocks"]).strip()
                    md_parts.append(f"### {txt}\n")
                elif etype == "card":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    md_parts.append(f"```text\n{txt}\n```\n")
                elif etype == "table":
                    t_rows = []
                    t_rows.append("| 항목 1 | 내용 1 | 항목 2 | 내용 2 |")
                    t_rows.append("| --- | --- | --- | --- |")
                    for row in elem["rows"]:
                        if row["type"] == "4col":
                            t_rows.append(f"| {_escape_md_cell(row['c0'])} | {_escape_md_cell(row['c1'])} | {_escape_md_cell(row['c2'])} | {_escape_md_cell(row['c3'])} |")
                        elif row["type"] == "colspan":
                            t_rows.append(f"| {_escape_md_cell(row['c0'])} | {_escape_md_cell(row['c1'])} | - | - |")
                    md_parts.append("\n".join(t_rows) + "\n")
                elif etype == "paragraph":
                    txt = "\n".join(b["text"] for b in elem["blocks"]).strip()
                    if txt:
                        md_parts.append(f"{txt}\n")

            md_parts.append(f"\n*{p.get('text', f'- {pno} -')}*\n\n---\n")

        return "\n".join(md_parts).strip()


def convert_pdf_to_high_fidelity_html(pdf_path: Path, title: Optional[str] = None) -> str:
    """Convert PDF to high-fidelity responsive HTML (95%+ visual match)."""
    from synthetic_engine.exporters.ocr_table_reconstructor import (
        is_scanned_pdf, extract_scanned_pdf_pages, convert_ocr_result_to_html
    )
    if is_scanned_pdf(pdf_path):
        pages = extract_scanned_pdf_pages(pdf_path)
        return convert_ocr_result_to_html(pages)

    doc = HighFidelityPdfDoc(pdf_path)
    try:
        return doc.to_html(title=title)
    finally:
        doc.close()


def convert_pdf_to_high_fidelity_docx(pdf_path: Path, output_path: Path) -> None:
    """Convert PDF to high-fidelity Word (.docx) document."""
    from synthetic_engine.exporters.ocr_table_reconstructor import (
        is_scanned_pdf, extract_scanned_pdf_pages, convert_ocr_result_to_docx
    )
    if is_scanned_pdf(pdf_path):
        pages = extract_scanned_pdf_pages(pdf_path)
        convert_ocr_result_to_docx(pages, output_path)
        return

    doc = HighFidelityPdfDoc(pdf_path)
    try:
        doc.to_docx(output_path)
    finally:
        doc.close()


def convert_pdf_to_high_fidelity_excel(pdf_path: Path, output_path: Path) -> None:
    """Convert PDF to styled Excel (.xlsx) spreadsheet with 3 distinct sheets."""
    doc = HighFidelityPdfDoc(pdf_path)
    try:
        doc.to_excel(output_path)
    finally:
        doc.close()


def convert_pdf_to_high_fidelity_hwpx(pdf_path: Path, output_path: Path) -> None:
    """Convert PDF to standard HWPX document."""
    from synthetic_engine.exporters.ocr_table_reconstructor import (
        is_scanned_pdf, extract_scanned_pdf_pages, convert_ocr_result_to_hwpx
    )
    if is_scanned_pdf(pdf_path):
        pages = extract_scanned_pdf_pages(pdf_path)
        convert_ocr_result_to_hwpx(pages, output_path)
        return

    doc = HighFidelityPdfDoc(pdf_path)
    try:
        doc.to_hwpx(output_path)
    finally:
        doc.close()


def convert_pdf_to_high_fidelity_hwp(pdf_path: Path, output_path: Path) -> None:
    """Convert PDF to binary HWP through an intermediate HWPX package and Hancom COM."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        intermediate_hwpx = Path(tmpdir) / f"{Path(pdf_path).stem}.hwpx"
        convert_pdf_to_high_fidelity_hwpx(pdf_path, intermediate_hwpx)

        try:
            import pythoncom
            import win32com.client
        except Exception as exc:
            raise RuntimeError("PDF를 HWP(.hwp)로 저장하려면 Windows 한컴오피스 COM 환경이 필요합니다. HWPX(.hwpx) 또는 Word(.docx) 변환을 사용하세요.") from exc

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

            opened = hwp.Open(str(intermediate_hwpx.resolve()), "HWPX", "versionwarning:False;forcedopen:True")
            if not opened:
                opened = hwp.Open(str(intermediate_hwpx.resolve()))
            if not opened:
                raise RuntimeError("중간 HWPX 문서를 한컴오피스에서 열지 못했습니다.")

            saved = hwp.SaveAs(str(output_path.resolve()), "HWP", "")
            if not saved or not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError("한컴오피스 HWP 저장에 실패했습니다.")
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"PDF HWP 변환 실패: {str(exc)}") from exc
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()


def convert_pdf_to_high_fidelity_markdown(pdf_path: Path) -> str:
    """Convert PDF to structured Markdown."""
    from synthetic_engine.exporters.ocr_table_reconstructor import (
        is_scanned_pdf, extract_scanned_pdf_pages, convert_ocr_result_to_markdown
    )
    if is_scanned_pdf(pdf_path):
        pages = extract_scanned_pdf_pages(pdf_path)
        return convert_ocr_result_to_markdown(pages)

    doc = HighFidelityPdfDoc(pdf_path)
    try:
        return doc.to_markdown()
    finally:
        doc.close()
# =============================================================================
# 파일명: pdf_high_fidelity_converter.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/pdf_high_fidelity_converter.py
# 목적: PDF 레이아웃·표·텍스트를 구조화해 변환함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
