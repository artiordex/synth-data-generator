# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import re
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from bs4 import BeautifulSoup, Tag
import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


def _find_pyhwp_bin(tool_name: str) -> List[str]:
    """Find absolute path to pyhwp tool or run as python module."""
    py_dir = Path(sys.executable).parent
    bin_path = py_dir / f"{tool_name}.exe"
    if bin_path.exists():
        return [str(bin_path)]
    bin_path_noext = py_dir / tool_name
    if bin_path_noext.exists():
        return [str(bin_path_noext)]
    which_path = shutil.which(tool_name)
    if which_path:
        return [which_path]
    if tool_name == "hwp5html":
        return [sys.executable, "-m", "hwp5.hwp5html"]
    elif tool_name == "hwp5txt":
        return [sys.executable, "-m", "hwp5.hwp5txt"]
    return [tool_name]


# ==============================================================================
# Helper Styling & OOXML Functions
# ==============================================================================

def parse_css_rules(css_text: str) -> Dict[str, Dict[str, str]]:
    """Parse CSS string into a dictionary mapping selectors to property dicts."""
    styles: Dict[str, Dict[str, str]] = {}
    for block in re.finditer(r'([^{]+)\{([^}]+)\}', css_text):
        selectors = [s.strip() for s in block.group(1).split(',')]
        body = block.group(2).strip()
        rules: Dict[str, str] = {}
        for rule in body.split(';'):
            if ':' in rule:
                k, v = rule.split(':', 1)
                rules[k.strip().lower()] = v.strip()
        for sel in selectors:
            if sel not in styles:
                styles[sel] = {}
            styles[sel].update(rules)
    return styles


def parse_length_to_mm(val_str: Optional[str]) -> Optional[float]:
    """Convert CSS length string (mm, cm, in, pt, px) to millimeters."""
    if not val_str:
        return None
    val_str = val_str.strip().lower()
    m = re.match(r'^([\d\.]+)\s*(mm|pt|cm|in|px)?$', val_str)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or 'pt'
    if unit == 'mm':
        return num
    elif unit == 'cm':
        return num * 10.0
    elif unit == 'in':
        return num * 25.4
    elif unit == 'pt':
        return num * 25.4 / 72.0
    elif unit == 'px':
        return num * 25.4 / 96.0
    return num


def parse_length_to_pt(val_str: Optional[str]) -> Optional[float]:
    """Convert CSS length string to points (pt)."""
    mm = parse_length_to_mm(val_str)
    if mm is None:
        return None
    return mm * 72.0 / 25.4


def hex_to_rgb(hex_str: Optional[str]) -> Optional[RGBColor]:
    """Convert hex color string (#RRGGBB or #RGB) to docx RGBColor."""
    if not hex_str:
        return None
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    if len(hex_str) == 6:
        try:
            return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        except ValueError:
            return None
    return None


def set_cell_background(cell: Any, fill_hex: str) -> None:
    """Apply background shading color to a Word table cell."""
    fill_clean = fill_hex.strip().lstrip('#').upper()
    if len(fill_clean) == 3:
        fill_clean = ''.join(c * 2 for c in fill_clean)
    if len(fill_clean) == 6:
        shading_xml = f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill_clean}"/>'
        cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))


def set_cell_margins(cell: Any, top: int = 100, bottom: int = 100, left: int = 140, right: int = 140) -> None:
    """Set internal cell margins (padding) in dxa units."""
    tcMar_xml = f'''
    <w:tcMar {nsdecls("w")}>
        <w:top w:w="{top}" w:type="dxa"/>
        <w:bottom w:w="{bottom}" w:type="dxa"/>
        <w:left w:w="{left}" w:type="dxa"/>
        <w:right w:w="{right}" w:type="dxa"/>
    </w:tcMar>
    '''
    cell._tc.get_or_add_tcPr().append(parse_xml(tcMar_xml))


def set_table_borders(table: Any, color: str = "CBD5E1", sz: str = "4", val: str = "single") -> None:
    """Set clean borders for entire table."""
    tblPr = table._tbl.tblPr
    borders_xml = f'''
    <w:tblBorders {nsdecls("w")}>
        <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
    </w:tblBorders>
    '''
    tblPr.append(parse_xml(borders_xml))


def set_row_cant_split(row: Any) -> None:
    """Prevent table row from splitting across page breaks."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))


def set_row_as_header(row: Any) -> None:
    """Set table row to repeat on every page header."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))


# ==============================================================================
# HWP (via hwp5html) to DOCX Converter
# ==============================================================================

class HwpHtmlToDocxBuilder:
    """Constructs a high-fidelity Word (.docx) document from hwp5html output."""

    def __init__(self, html_path: Path, css_path: Optional[Path], media_dir: Optional[Path]):
        self.html_path = html_path
        self.css_path = css_path
        self.media_dir = media_dir
        self.css_rules: Dict[str, Dict[str, str]] = {}
        if css_path and css_path.exists():
            try:
                self.css_rules = parse_css_rules(css_path.read_text(encoding='utf-8', errors='ignore'))
            except Exception:
                self.css_rules = {}

        self.doc = docx.Document()
        self._configure_default_styles()

    def _configure_default_styles(self) -> None:
        """Set Korean standard default styles in document."""
        normal_style = self.doc.styles['Normal']
        normal_style.font.name = '맑은 고딕'
        normal_style.font.size = Pt(10)
        normal_style.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)  # #1F2937
        normal_style.paragraph_format.line_spacing = 1.2
        normal_style.paragraph_format.space_after = Pt(2)
        normal_style.paragraph_format.space_before = Pt(0)

    def _get_classes_props(self, el: Tag) -> Dict[str, str]:
        """Aggregate CSS properties for element classes."""
        props: Dict[str, str] = {}
        classes = el.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()

        for c in classes:
            sel = f".{c}"
            if sel in self.css_rules:
                props.update(self.css_rules[sel])

        # Inline style override
        inline_style = el.get('style', '')
        if inline_style:
            for rule in inline_style.split(';'):
                if ':' in rule:
                    k, v = rule.split(':', 1)
                    props[k.strip().lower()] = v.strip()

        return props

    def build(self, output_docx_path: Path) -> Path:
        """Parse XHTML DOM and build Word Document."""
        raw_html = self.html_path.read_text(encoding='utf-8', errors='ignore')
        # Clean XHTML DTD for robust parsing
        clean_html = re.sub(r'<\?xml[^>]*\?>', '', raw_html)
        clean_html = re.sub(r'<!DOCTYPE[^>]*>', '', clean_html)

        soup = BeautifulSoup(clean_html, 'html.parser')

        # 1. Detect Page Size & Orientation from Section
        section = self.doc.sections[0]
        section_div = soup.find(class_=re.compile(r'Section-\d+'))
        is_landscape = False
        if section_div:
            sec_props = self._get_classes_props(section_div)
            width_mm = parse_length_to_mm(sec_props.get('width'))
            if width_mm and width_mm > 250:
                is_landscape = True

        # Check inline styles in soup
        for st in soup.find_all('style'):
            st_text = st.get_text()
            if '297mm' in st_text or 'width: 297mm' in st_text:
                is_landscape = True

        if is_landscape:
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = Mm(297)
            section.page_height = Mm(210)
            section.left_margin = Mm(18)
            section.right_margin = Mm(18)
            section.top_margin = Mm(18)
            section.bottom_margin = Mm(18)
        else:
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width = Mm(210)
            section.page_height = Mm(297)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(20)
            section.bottom_margin = Mm(20)

        # 2. Process Body Elements
        body = soup.find('body') or soup
        self._process_container(body)

        # Remove trailing empty paragraphs if any
        output_docx_path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(output_docx_path.resolve()))
        return output_docx_path

    def _process_container(self, container: Tag) -> None:
        """Process children elements of container recursively."""
        for child in container.children:
            if not isinstance(child, Tag):
                continue

            # Skip header/footer wrappers if purely positional
            if 'HeaderPageFooter' in child.get('class', []) or 'Page' in child.get('class', []):
                self._process_container(child)
                continue

            tag_name = child.name.lower()
            if tag_name == 'table':
                self._render_table(child)
            elif tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                self._render_heading(child)
            elif tag_name == 'p':
                tbls = child.find_all('table')
                if tbls:
                    for t in tbls:
                        self._render_table(t)
                else:
                    self._render_paragraph(child)
            elif tag_name == 'div':
                if child.find('table'):
                    self._process_container(child)
                else:
                    self._render_paragraph(child)
            elif tag_name in ('ul', 'ol'):
                self._render_list(child)
            elif tag_name == 'img':
                self._render_image(child)
            else:
                if child.find('table'):
                    self._process_container(child)
                elif child.find('img'):
                    self._render_image(child.find('img'))

    def _render_heading(self, el: Tag) -> None:
        """Render heading element."""
        text = el.get_text(strip=True)
        if not text:
            return
        level_map = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4, 'h5': 5, 'h6': 6}
        level = level_map.get(el.name.lower(), 1)
        p = self.doc.add_heading(level=level)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True

        run = p.add_run(text)
        run.font.name = '맑은 고딕'
        run.bold = True
        if level == 1:
            run.font.size = Pt(16)
            run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        elif level == 2:
            run.font.size = Pt(13)
            run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
        else:
            run.font.size = Pt(11.5)
            run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    def _render_paragraph(self, el: Tag, target_cell: Optional[Any] = None) -> None:
        """Render a single paragraph preserving runs, fonts, colors, bold and alignment."""
        text = el.get_text().strip()
        if not text:
            return

        props = self._get_classes_props(el)
        p = target_cell.add_paragraph() if target_cell else self.doc.add_paragraph()

        # Alignment
        align_str = props.get('text-align', '').lower()
        if align_str == 'center':
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align_str == 'right':
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align_str == 'justify':
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Spacing
        if target_cell:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.15
        else:
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.25

        # Check if entire paragraph has list bullet
        is_bullet = 'Bullet-' in str(el.get('class', '')) or text.startswith(('①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '•', '- ', '※', '■', '▶'))
        if is_bullet:
            p.paragraph_format.left_indent = Pt(6)

        # Parse text runs inside paragraph
        spans = el.find_all(['span', 'b', 'strong', 'i', 'em', 'u', 'img'])
        if spans:
            for s in spans:
                if s.name == 'img':
                    self._render_inline_image(s, p)
                    continue

                s_text = s.get_text().replace('\r', '').replace('\n', ' ')
                if not s_text:
                    continue

                s_props = self._get_classes_props(s)
                run = p.add_run(s_text)
                run.font.name = '맑은 고딕'

                # Font Size
                fs = s_props.get('font-size') or props.get('font-size')
                if fs:
                    pt = parse_length_to_pt(fs)
                    if pt:
                        run.font.size = Pt(min(max(pt, 7.5), 24))
                else:
                    run.font.size = Pt(9.5 if target_cell else 10)

                # Font Color
                color_hex = s_props.get('color') or props.get('color')
                if color_hex and color_hex.startswith('#'):
                    rgb = hex_to_rgb(color_hex)
                    if rgb:
                        run.font.color.rgb = rgb

                # Font Weight / Style
                if s.name in ('b', 'strong') or s_props.get('font-weight') in ('bold', '700', '800', '900'):
                    run.bold = True
                if s.name in ('i', 'em') or s_props.get('font-style') == 'italic':
                    run.italic = True
                if s.name == 'u' or 'underline' in s_props.get('text-decoration', ''):
                    run.underline = True
        else:
            run = p.add_run(text.replace('\r', '').replace('\n', ' '))
            run.font.name = '맑은 고딕'
            run.font.size = Pt(9.5 if target_cell else 10)

    def _render_list(self, el: Tag) -> None:
        """Render unordered or ordered list."""
        for li in el.find_all('li', recursive=False):
            txt = li.get_text(strip=True)
            if not txt:
                continue
            p = self.doc.add_paragraph(style='List Bullet' if el.name == 'ul' else 'List Number')
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(txt)
            run.font.name = '맑은 고딕'
            run.font.size = Pt(10)

    def _render_image(self, el: Tag) -> None:
        """Render standalone image."""
        src = el.get('src', '')
        if not src:
            return
        img_path = self._resolve_media_path(src)
        if img_path and img_path.exists():
            try:
                p = self.doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(str(img_path), width=Inches(5.5))
            except Exception:
                pass

    def _render_inline_image(self, el: Tag, paragraph: Any) -> None:
        """Render inline image inside a paragraph or cell."""
        src = el.get('src', '')
        if not src:
            return
        img_path = self._resolve_media_path(src)
        if img_path and img_path.exists():
            try:
                paragraph.add_run().add_picture(str(img_path), width=Inches(2.0))
            except Exception:
                pass

    def _resolve_media_path(self, src: str) -> Optional[Path]:
        """Resolve image src path relative to html or media_dir."""
        src_clean = src.replace('\\', '/')
        if self.media_dir:
            cand = self.media_dir / Path(src_clean).name
            if cand.exists():
                return cand
        cand2 = self.html_path.parent / src_clean
        if cand2.exists():
            return cand2
        return None

    def _render_table(self, table_el: Tag) -> None:
        """Render a table preserving grid widths, colSpan, rowSpan, shading, and padding."""
        trs = table_el.find_all('tr', recursive=False)
        if not trs:
            # Check if inside tbody
            tbody = table_el.find('tbody')
            if tbody:
                trs = tbody.find_all('tr', recursive=False)

        if not trs:
            return

        # 1. Compute table dimensions and column widths
        col_widths_mm: List[float] = []
        raw_rows_data: List[List[Dict[str, Any]]] = []

        for tr in trs:
            row_data: List[Dict[str, Any]] = []
            cells = tr.find_all(['td', 'th'], recursive=False)
            for c in cells:
                colspan = int(c.get('colspan', 1) or 1)
                rowspan = int(c.get('rowspan', 1) or 1)
                c_props = self._get_classes_props(c)
                w_mm = parse_length_to_mm(c_props.get('width'))

                # Background Color
                bg_color = c_props.get('background-color') or c_props.get('background')
                if bg_color and 'none' in bg_color.lower():
                    bg_color = None

                row_data.append({
                    'tag': c,
                    'colspan': colspan,
                    'rowspan': rowspan,
                    'width_mm': w_mm,
                    'bg_color': bg_color,
                    'is_th': c.name.lower() == 'th'
                })
            raw_rows_data.append(row_data)

        # Calculate max columns
        max_cols = 0
        for r in raw_rows_data:
            tot = sum(c['colspan'] for c in r)
            if tot > max_cols:
                max_cols = tot

        if max_cols == 0:
            return

        # Estimate column widths in mm
        col_widths = [0.0] * max_cols
        for r in raw_rows_data:
            col_idx = 0
            for c in r:
                if c['colspan'] == 1 and c['width_mm'] and c['width_mm'] > 0:
                    if col_widths[col_idx] == 0:
                        col_widths[col_idx] = c['width_mm']
                col_idx += c['colspan']

        # Fill default width for unmeasured columns
        available_width_mm = 250.0 if self.doc.sections[0].orientation == WD_ORIENT.LANDSCAPE else 170.0
        known_width = sum(col_widths)
        unknown_cols = [i for i, w in enumerate(col_widths) if w <= 0]
        if unknown_cols:
            rem = max(available_width_mm - known_width, 10.0 * len(unknown_cols))
            fill_w = rem / len(unknown_cols)
            for uc in unknown_cols:
                col_widths[uc] = fill_w

        # 2. Create docx Table
        num_rows = len(raw_rows_data)
        tbl = self.doc.add_table(rows=num_rows, cols=max_cols)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        set_table_borders(tbl, color="CBD5E1", sz="4", val="single")

        # Set column widths on table grid
        for c_idx, w_mm in enumerate(col_widths):
            for r_idx in range(num_rows):
                tbl.cell(r_idx, c_idx).width = Mm(w_mm)

        # Set CantSplit on all rows and tblHeader on row 0
        for r_idx, row in enumerate(tbl.rows):
            set_row_cant_split(row)
            if r_idx == 0:
                set_row_as_header(row)

        # 3. Grid cell occupation tracker for rowspans and colspans
        grid_occupied: List[List[bool]] = [[False] * max_cols for _ in range(num_rows)]

        for r_idx, r_items in enumerate(raw_rows_data):
            c_idx = 0
            for item in r_items:
                # Find next unoccupied column in this row
                while c_idx < max_cols and grid_occupied[r_idx][c_idx]:
                    c_idx += 1

                if c_idx >= max_cols:
                    break

                colspan = item['colspan']
                rowspan = item['rowspan']

                start_r = r_idx
                end_r = min(r_idx + rowspan - 1, num_rows - 1)
                start_c = c_idx
                end_c = min(c_idx + colspan - 1, max_cols - 1)

                # Mark grid cells occupied
                for r_k in range(start_r, end_r + 1):
                    for c_k in range(start_c, end_c + 1):
                        grid_occupied[r_k][c_k] = True

                # Merge cells if span > 1
                origin_cell = tbl.cell(start_r, start_c)
                if end_r > start_r or end_c > start_c:
                    origin_cell = origin_cell.merge(tbl.cell(end_r, end_c))

                # Apply cell styling
                set_cell_margins(origin_cell, top=100, bottom=100, left=140, right=140)
                origin_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                # Background shading
                bg_hex = item['bg_color']
                if not bg_hex and (r_idx == 0 or item['is_th']):
                    bg_hex = "#EDF2F7"  # Default soft header shading

                if bg_hex and bg_hex.startswith('#'):
                    set_cell_background(origin_cell, bg_hex)

                # Render Cell Content
                cell_tag = item['tag']
                # Clear default empty paragraph in newly created cell
                origin_cell.paragraphs[0].text = ""

                # Populate paragraphs inside cell
                cell_p_elements = cell_tag.find_all(['p', 'div', 'ul', 'ol'], recursive=False)
                if cell_p_elements:
                    for p_i, p_el in enumerate(cell_p_elements):
                        if p_i == 0:
                            # Reuse first paragraph
                            self._fill_existing_paragraph(p_el, origin_cell.paragraphs[0], is_header=(r_idx == 0 or item['is_th']))
                        else:
                            self._render_paragraph(p_el, target_cell=origin_cell)
                else:
                    # Direct text in cell without <p>
                    direct_text = cell_tag.get_text().strip()
                    p0 = origin_cell.paragraphs[0]
                    p0.paragraph_format.space_before = Pt(0)
                    p0.paragraph_format.space_after = Pt(0)
                    p0.paragraph_format.line_spacing = 1.15
                    if r_idx == 0 or item['is_th']:
                        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p0.add_run(direct_text)
                    run.font.name = '맑은 고딕'
                    run.font.size = Pt(9.5)
                    if r_idx == 0 or item['is_th']:
                        run.bold = True

                c_idx = end_c + 1

        # Add spacing after table
        space_p = self.doc.add_paragraph()
        space_p.paragraph_format.space_before = Pt(4)
        space_p.paragraph_format.space_after = Pt(4)

    def _fill_existing_paragraph(self, el: Tag, p: Any, is_header: bool = False) -> None:
        """Fill an existing cell paragraph with text runs and styling."""
        props = self._get_classes_props(el)
        align_str = props.get('text-align', '').lower()
        if align_str == 'center' or is_header:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align_str == 'right':
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align_str == 'justify':
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1.5)
        p.paragraph_format.line_spacing = 1.15

        spans = el.find_all(['span', 'b', 'strong', 'i', 'em', 'u', 'img'])
        if spans:
            for s in spans:
                if s.name == 'img':
                    self._render_inline_image(s, p)
                    continue

                s_text = s.get_text().replace('\r', '').replace('\n', ' ')
                if not s_text:
                    continue
                s_props = self._get_classes_props(s)
                run = p.add_run(s_text)
                run.font.name = '맑은 고딕'

                # Font size
                fs = s_props.get('font-size') or props.get('font-size')
                if fs:
                    pt = parse_length_to_pt(fs)
                    if pt:
                        run.font.size = Pt(min(max(pt, 7.5), 18))
                else:
                    run.font.size = Pt(9.5)

                # Color
                color_hex = s_props.get('color') or props.get('color')
                if color_hex and color_hex.startswith('#'):
                    rgb = hex_to_rgb(color_hex)
                    if rgb:
                        run.font.color.rgb = rgb

                # Weight
                if is_header or s.name in ('b', 'strong') or s_props.get('font-weight') in ('bold', '700', '800', '900'):
                    run.bold = True
                if s.name in ('i', 'em') or s_props.get('font-style') == 'italic':
                    run.italic = True
                if s.name == 'u' or 'underline' in s_props.get('text-decoration', ''):
                    run.underline = True
        else:
            run = p.add_run(el.get_text().replace('\r', '').replace('\n', ' '))
            run.font.name = '맑은 고딕'
            run.font.size = Pt(9.5)
            if is_header:
                run.bold = True


# ==============================================================================
# Unified Public Converter Functions
# ==============================================================================

def convert_hwp_to_high_fidelity_docx(input_path: Path, output_path: Path) -> Path:
    """Convert binary HWP file to high-fidelity Word (.docx) preserving all tables and styling."""
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "html_out"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = _find_pyhwp_bin("hwp5html") + ["--output", str(out_dir), str(input_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except Exception as exc:
            res = None

        xhtml_file = out_dir / "index.xhtml"
        if not xhtml_file.exists():
            xhtml_file = out_dir / "index.html"

        css_file = out_dir / "styles.css"
        bindata_dir = out_dir / "bindata"

        if xhtml_file.exists():
            builder = HwpHtmlToDocxBuilder(
                html_path=xhtml_file,
                css_path=css_file if css_file.exists() else None,
                media_dir=bindata_dir if bindata_dir.exists() else None
            )
            return builder.build(output_path)

        # Fallback via text
        try:
            res_txt = subprocess.run(_find_pyhwp_bin("hwp5txt") + [str(input_path)], capture_output=True, timeout=30)
            txt = res_txt.stdout.decode("utf-8", errors="ignore")
            doc = docx.Document()
            for p in txt.split("\n\n"):
                if p.strip():
                    doc.add_paragraph(p.strip())
            doc.save(str(output_path))
            return output_path
        except Exception as exc:
            raise RuntimeError(f"HWP 워드 변환 실패: {str(exc)}")


def convert_hwpx_to_high_fidelity_docx(input_path: Path, output_path: Path) -> Path:
    """Convert modern OWPML HWPX file to high-fidelity Word (.docx)."""
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = docx.Document()
    hp_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}

    with zipfile.ZipFile(input_path, "r") as zf:
        section_names = sorted([n for n in zf.namelist() if "section" in n.lower() and n.endswith(".xml")])
        if not section_names:
            if "Preview/PrvText.txt" in zf.namelist():
                txt = zf.read("Preview/PrvText.txt").decode("utf-16", errors="ignore")
                for p in txt.split("\n"):
                    if p.strip():
                        doc.add_paragraph(p.strip())
                doc.save(str(output_path))
                return output_path

        for s_name in section_names:
            xml_bytes = zf.read(s_name)
            root = ET.fromstring(xml_bytes)
            sec = root.find(".//hp:sec", hp_ns) or root

            for p_el in sec.findall("./hp:p", hp_ns):
                # 1. Paragraph direct text
                p_text_parts = []
                for run in p_el.findall("./hp:run", hp_ns):
                    for t in run.findall("./hp:t", hp_ns):
                        if t.text:
                            p_text_parts.append(t.text)

                p_str = "".join(p_text_parts).strip()
                if p_str:
                    p = doc.add_paragraph()
                    run = p.add_run(p_str)
                    run.font.name = '맑은 고딕'
                    run.font.size = Pt(10)

                # 2. Tables in paragraph
                for tbl_el in p_el.findall(".//hp:tbl", hp_ns):
                    trs = tbl_el.findall("./hp:tr", hp_ns)
                    if not trs:
                        continue

                    # Extract table data
                    rows_data = []
                    max_cols = 0
                    for tr in trs:
                        row_cells = []
                        for tc in tr.findall("./hp:tc", hp_ns):
                            cell_addr = tc.find("./hp:cellAddr", hp_ns)
                            colspan = int(cell_addr.attrib.get("colSpan", "1")) if cell_addr is not None else 1
                            rowspan = int(cell_addr.attrib.get("rowSpan", "1")) if cell_addr is not None else 1
                            texts = [t.text for t in tc.findall(".//hp:t", hp_ns) if t.text]
                            row_cells.append({
                                'text': " ".join(texts).strip(),
                                'colspan': colspan,
                                'rowspan': rowspan
                            })
                        tot = sum(c['colspan'] for c in row_cells)
                        max_cols = max(max_cols, tot)
                        rows_data.append(row_cells)

                    if max_cols == 0:
                        continue

                    num_rows = len(rows_data)
                    tbl = doc.add_table(rows=num_rows, cols=max_cols)
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    set_table_borders(tbl, color="CBD5E1", sz="4", val="single")

                    for r_idx, row in enumerate(tbl.rows):
                        set_row_cant_split(row)
                        if r_idx == 0:
                            set_row_as_header(row)

                    occupied = [[False] * max_cols for _ in range(num_rows)]
                    for r_idx, r_cells in enumerate(rows_data):
                        c_idx = 0
                        for c_item in r_cells:
                            while c_idx < max_cols and occupied[r_idx][c_idx]:
                                c_idx += 1
                            if c_idx >= max_cols:
                                break

                            cs = c_item['colspan']
                            rs = c_item['rowspan']
                            end_r = min(r_idx + rs - 1, num_rows - 1)
                            end_c = min(c_idx + cs - 1, max_cols - 1)

                            for r_k in range(r_idx, end_r + 1):
                                for c_k in range(c_idx, end_c + 1):
                                    occupied[r_k][c_k] = True

                            target_cell = tbl.cell(r_idx, c_idx)
                            if end_r > r_idx or end_c > c_idx:
                                target_cell = target_cell.merge(tbl.cell(end_r, end_c))

                            set_cell_margins(target_cell, top=100, bottom=100, left=140, right=140)
                            if r_idx == 0:
                                set_cell_background(target_cell, "#EDF2F7")

                            target_cell.paragraphs[0].text = ""
                            p0 = target_cell.paragraphs[0]
                            p0.paragraph_format.space_before = Pt(0)
                            p0.paragraph_format.space_after = Pt(0)
                            if r_idx == 0:
                                p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            run = p0.add_run(c_item['text'])
                            run.font.name = '맑은 고딕'
                            run.font.size = Pt(9.5)
                            if r_idx == 0:
                                run.bold = True

                            c_idx = end_c + 1

    doc.save(str(output_path))
    return output_path


def convert_any_hwp_to_docx(input_path: Path, output_path: Path) -> Path:
    """Auto-detect format (HWP binary vs HWPX package) and convert to DOCX with maximum fidelity."""
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()

    # Check if ZIP format (HWPX)
    if zipfile.is_zipfile(input_path):
        return convert_hwpx_to_high_fidelity_docx(input_path, output_path)
    else:
        return convert_hwp_to_high_fidelity_docx(input_path, output_path)

# =============================================================================
# 파일명: hwp_high_fidelity_docx_converter.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/hwp_high_fidelity_docx_converter.py
# 목적: HWP 문서를 DOCX 구조로 고충실도 변환함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
