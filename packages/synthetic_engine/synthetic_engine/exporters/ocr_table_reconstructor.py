# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_table_reconstructor.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_table_reconstructor.py
# 목적: 스캔본·디지털 PDF의 OCR, 표(Table) 격자 복원, Deskewing 및 이미지(Figure) 보존 엔진
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

import base64
import io
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pymupdf
from PIL import Image

_OCR_READER = None


def get_ocr_reader():
    """Lazy singleton EasyOCR Reader (Korean + English) with RapidOCR fallback."""
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
            _OCR_READER = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
        except Exception:
            try:
                from rapidocr_onnxruntime import RapidOCR
                _OCR_READER = RapidOCR()
            except Exception:
                _OCR_READER = None
    return _OCR_READER


@dataclass
class OCRWord:
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2.0, (self.bbox[1] + self.bbox[3]) / 2.0)


@dataclass
class OCRTableCell:
    row: int
    col: int
    rowspan: int
    colspan: int
    bbox: Tuple[int, int, int, int]
    words: List[OCRWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        sorted_words = sorted(self.words, key=lambda w: (w.bbox[1] // 10, w.bbox[0]))
        return " ".join(w.text for w in sorted_words).strip()


@dataclass
class OCRTable:
    bbox: Tuple[int, int, int, int]
    cells: List[OCRTableCell] = field(default_factory=list)
    rows_count: int = 0
    cols_count: int = 0

    def to_grid(self) -> List[List[str]]:
        grid = [["" for _ in range(self.cols_count)] for _ in range(self.rows_count)]
        for cell in self.cells:
            if cell.row < self.rows_count and cell.col < self.cols_count:
                grid[cell.row][cell.col] = cell.text
        return grid


@dataclass
class OCRTextBlock:
    text: str
    bbox: Tuple[int, int, int, int]
    is_heading: bool = False
    font_scale: float = 1.0


@dataclass
class OCRFigureBlock:
    """도표, 사진, 다이어그램, 직인/서명 등 문서 내 이미지 요소."""
    bbox: Tuple[int, int, int, int]
    image_bytes: bytes
    format: str = "png"
    width: int = 0
    height: int = 0

    @property
    def base64_src(self) -> str:
        b64 = base64.b64encode(self.image_bytes).decode("ascii")
        mime = "image/jpeg" if self.format.lower() in ("jpg", "jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"


@dataclass
class OCRPageResult:
    page_num: int
    width: int
    height: int
    tables: List[OCRTable] = field(default_factory=list)
    text_blocks: List[OCRTextBlock] = field(default_factory=list)
    figures: List[OCRFigureBlock] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = []
        for b in self.text_blocks:
            parts.append(b.text)
        for t in self.tables:
            grid = t.to_grid()
            for row in grid:
                parts.append(" | ".join(row))
        return "\n".join(parts)


def deskew_image(img_bgr: np.ndarray, max_angle: float = 15.0) -> Tuple[np.ndarray, float]:
    """스캔 시 발생한 미세 기울기(0.5~15도)를 자동 감지하여 수평 보정함 (Deskewing)."""
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return img_bgr, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > max_angle or abs(angle) < 0.3:
            return img_bgr, 0.0

        h, w = img_bgr.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img_bgr, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated, angle
    except Exception:
        return img_bgr, 0.0


def is_scanned_pdf(pdf_path: Path, max_pages_to_check: int = 3) -> bool:
    """PDF 내 디지털 텍스트가 극소량이거나 전무한 스캔본 문서인지 판별함."""
    try:
        with pymupdf.open(pdf_path) as doc:
            if len(doc) == 0:
                return False
            total_chars = 0
            pages_checked = min(len(doc), max_pages_to_check)
            for i in range(pages_checked):
                text = doc[i].get_text().strip()
                total_chars += len(text)
            avg_chars = total_chars / pages_checked
            return avg_chars < 30
    except Exception:
        return False


def detect_table_grid_cells(
    img_gray: np.ndarray,
    min_cell_w: int = 30,
    min_cell_h: int = 15,
    min_table_area: int = 8000,
) -> List[OCRTable]:
    """OpenCV 모폴로지 선 탐지로 표 윤곽선 및 개별 셀 그리드를 정밀 분할함."""
    h, w = img_gray.shape[:2]

    thresh = cv2.adaptiveThreshold(
        ~img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2
    )

    h_scale = max(20, w // 40)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_scale, 1))
    h_lines = cv2.erode(thresh, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_lines, h_kernel, iterations=1)

    v_scale = max(15, h // 40)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_scale))
    v_lines = cv2.erode(thresh, v_kernel, iterations=1)
    v_lines = cv2.dilate(v_lines, v_kernel, iterations=1)

    table_structure = cv2.add(h_lines, v_lines)

    table_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    table_structure_dilated = cv2.dilate(table_structure, table_kernel, iterations=2)
    contours, _ = cv2.findContours(
        table_structure_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    tables: List[OCRTable] = []

    for cnt in contours:
        tx, ty, tw, th = cv2.boundingRect(cnt)
        if tw * th < min_table_area or tw < w * 0.2:
            continue

        table_roi = table_structure[ty:ty + th, tx:tx + tw]
        cell_contours, _ = cv2.findContours(
            table_roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        detected_cell_boxes: List[Tuple[int, int, int, int]] = []
        for c_cnt in cell_contours:
            cx, cy, cw, ch = cv2.boundingRect(c_cnt)
            if (cw >= min_cell_w and ch >= min_cell_h and
                cw < tw * 0.98 and ch < th * 0.98 and (cw * ch) > 400):
                detected_cell_boxes.append((tx + cx, ty + cy, tx + cx + cw, ty + cy + ch))

        if len(detected_cell_boxes) < 4:
            continue

        detected_cell_boxes = sorted(detected_cell_boxes, key=lambda b: (b[1], b[0]))

        y_centers = [(b[1] + b[3]) / 2.0 for b in detected_cell_boxes]
        row_bands: List[float] = []
        for yc in sorted(y_centers):
            if not any(abs(yc - rb) < 15 for rb in row_bands):
                row_bands.append(yc)
        row_bands.sort()

        x_centers = [(b[0] + b[2]) / 2.0 for b in detected_cell_boxes]
        col_bands: List[float] = []
        for xc in sorted(x_centers):
            if not any(abs(xc - cb) < 20 for cb in col_bands):
                col_bands.append(xc)
        col_bands.sort()

        num_rows = max(1, len(row_bands))
        num_cols = max(1, len(col_bands))

        ocr_cells: List[OCRTableCell] = []
        for box in detected_cell_boxes:
            bc_x = (box[0] + box[2]) / 2.0
            bc_y = (box[1] + box[3]) / 2.0

            best_r = min(range(num_rows), key=lambda r: abs(bc_y - row_bands[r]))
            best_c = min(range(num_cols), key=lambda c: abs(bc_x - col_bands[c]))

            c_w = box[2] - box[0]
            c_h = box[3] - box[1]
            c_span = max(1, round(c_w / max(30, (tw / num_cols))))
            r_span = max(1, round(c_h / max(20, (th / num_rows))))

            ocr_cells.append(OCRTableCell(
                row=best_r,
                col=best_c,
                rowspan=r_span,
                colspan=c_span,
                bbox=box,
            ))

        tables.append(OCRTable(
            bbox=(tx, ty, tx + tw, ty + th),
            cells=ocr_cells,
            rows_count=num_rows,
            cols_count=num_cols,
        ))

    tables.sort(key=lambda t: t.bbox[1])
    return tables


def detect_image_figures(
    img_bgr: np.ndarray,
    tables: List[OCRTable],
    words: List[OCRWord],
    min_area: int = 12000,
) -> List[OCRFigureBlock]:
    """스캔본 문서에서 텍스트와 표를 제외한 사진, 도표, 차트, 직인 영역을 검출하고 고화질 크롭함."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr

    # Create mask to exclude table regions and text words
    mask = np.ones((h, w), dtype=np.uint8) * 255
    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        mask[max(0, ty0 - 10):min(h, ty1 + 10), max(0, tx0 - 10):min(w, tx1 + 10)] = 0
    for wd in words:
        wx0, wy0, wx1, wy1 = wd.bbox
        mask[max(0, wy0 - 5):min(h, wy1 + 5), max(0, wx0 - 5):min(w, wx1 + 5)] = 0

    # Find high-contrast / non-blank contours in remaining areas
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges_masked = cv2.bitwise_and(edges, edges, mask=mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    dilated = cv2.dilate(edges_masked, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    figures: List[OCRFigureBlock] = []

    for cnt in contours:
        fx, fy, fw, fh = cv2.boundingRect(cnt)
        if fw * fh < min_area or fw < 80 or fh < 80:
            continue
        # Avoid capturing entire page
        if fw > w * 0.95 and fh > h * 0.95:
            continue

        crop = img_bgr[fy:fy + fh, fx:fx + fw]
        # Check standard deviation of color (uniform white/black space vs actual image)
        if np.std(crop) < 15:
            continue

        # Encode cropped figure to PNG bytes
        success, buf = cv2.imencode(".png", crop)
        if success:
            figures.append(OCRFigureBlock(
                bbox=(fx, fy, fx + fw, fy + fh),
                image_bytes=buf.tobytes(),
                format="png",
                width=fw,
                height=fh
            ))

    figures.sort(key=lambda f: f.bbox[1])
    return figures


def extract_pdf_embedded_images(page: pymupdf.Page, doc: pymupdf.Document) -> List[OCRFigureBlock]:
    """디지털 PDF 내 원본 임베디드 이미지(xrefs)를 추출하고 페이지 내 좌표를 매핑함."""
    figures: List[OCRFigureBlock] = []
    image_list = page.get_images(full=True)

    for img_info in image_list:
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            w, h = base_image["width"], base_image["height"]

            # Try to get image bbox on page
            rects = page.get_image_rects(xref)
            if rects:
                r = rects[0]
                bbox = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
            else:
                bbox = (0, 0, w, h)

            figures.append(OCRFigureBlock(
                bbox=bbox,
                image_bytes=image_bytes,
                format=image_ext,
                width=w,
                height=h
            ))
        except Exception:
            continue

    figures.sort(key=lambda f: f.bbox[1])
    return figures


def _run_ocr_on_image(img_np: np.ndarray) -> List[OCRWord]:
    """Run EasyOCR (Korean + English) with RapidOCR fallback to extract words with bounding boxes."""
    words: List[OCRWord] = []
    reader = get_ocr_reader()
    if reader is None:
        return words

    # 1. Try EasyOCR
    if hasattr(reader, 'readtext'):
        try:
            results = reader.readtext(img_np)
            for item in results:
                bbox_pts, text, conf = item
                if not text or not str(text).strip():
                    continue
                xs = [p[0] for p in bbox_pts]
                ys = [p[1] for p in bbox_pts]
                words.append(OCRWord(
                    text=str(text).strip(),
                    bbox=(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
                    confidence=float(conf)
                ))
            return words
        except Exception:
            pass

    # 2. Try RapidOCR
    if callable(reader):
        try:
            ocr_result, _ = reader(img_np)
            if ocr_result:
                for item in ocr_result:
                    pts, text, conf = item
                    if not text or not str(text).strip():
                        continue
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    words.append(OCRWord(
                        text=str(text).strip(),
                        bbox=(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
                        confidence=float(conf)
                    ))
        except Exception:
            pass

    return words


def process_scanned_page(
    page_img_np: np.ndarray, page_num: int
) -> OCRPageResult:
    """단일 페이지 이미지에 대해 기울기 보정, 표 검출, 사진/도표 추출 및 OCR 바인딩을 수행함."""
    # 1. Deskew (기울기 자동 보정)
    deskewed_img, _ = deskew_image(page_img_np)

    h, w = deskewed_img.shape[:2]
    if len(deskewed_img.shape) == 3:
        gray = cv2.cvtColor(deskewed_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = deskewed_img

    # 2. 표 검출
    tables = detect_table_grid_cells(gray)

    # 3. 텍스트 OCR
    all_words = _run_ocr_on_image(deskewed_img)

    # 4. 사진/도표(Figure) 검출
    figures = detect_image_figures(deskewed_img, tables, all_words)

    # 5. 셀 텍스트 바인딩
    unassigned_words: List[OCRWord] = []

    for word in all_words:
        wx, wy = word.center
        matched_cell = False

        for table in tables:
            tx0, ty0, tx1, ty1 = table.bbox
            if tx0 <= wx <= tx1 and ty0 <= wy <= ty1:
                for cell in table.cells:
                    cx0, cy0, cx1, cy1 = cell.bbox
                    if cx0 <= wx <= cx1 and cy0 <= wy <= cy1:
                        cell.words.append(word)
                        matched_cell = True
                        break
                if matched_cell:
                    break

        if not matched_cell:
            unassigned_words.append(word)

    unassigned_words.sort(key=lambda w: (w.bbox[1] // 18, w.bbox[0]))

    text_blocks: List[OCRTextBlock] = []
    current_line: List[OCRWord] = []
    current_y = -100

    for word in unassigned_words:
        wy = word.bbox[1]
        if current_y < 0 or abs(wy - current_y) < 14:
            current_line.append(word)
            current_y = wy
        else:
            if current_line:
                line_text = " ".join(w.text for w in sorted(current_line, key=lambda w: w.bbox[0]))
                bx0 = min(w.bbox[0] for w in current_line)
                by0 = min(w.bbox[1] for w in current_line)
                bx1 = max(w.bbox[2] for w in current_line)
                by1 = max(w.bbox[3] for w in current_line)
                line_h = by1 - by0
                is_head = line_h > 24 or (len(line_text) < 30 and (line_text.startswith("#") or line_text.endswith(":")))
                text_blocks.append(OCRTextBlock(
                    text=line_text,
                    bbox=(bx0, by0, bx1, by1),
                    is_heading=is_head,
                    font_scale=line_h / 16.0
                ))
            current_line = [word]
            current_y = wy

    if current_line:
        line_text = " ".join(w.text for w in sorted(current_line, key=lambda w: w.bbox[0]))
        bx0 = min(w.bbox[0] for w in current_line)
        by0 = min(w.bbox[1] for w in current_line)
        bx1 = max(w.bbox[2] for w in current_line)
        by1 = max(w.bbox[3] for w in current_line)
        text_blocks.append(OCRTextBlock(
            text=line_text,
            bbox=(bx0, by0, bx1, by1),
            is_heading=False,
            font_scale=1.0
        ))

    return OCRPageResult(
        page_num=page_num,
        width=w,
        height=h,
        tables=tables,
        text_blocks=text_blocks,
        figures=figures,
    )


def extract_scanned_pdf_pages(pdf_path: Path, dpi: int = 200) -> List[OCRPageResult]:
    """스캔본 PDF의 모든 페이지를 고화질 이미지로 렌더링하고 표, 사진, 본문을 복원함."""
    results: List[OCRPageResult] = []
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)

    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 3:
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)
            else:
                img_bgr = img_data

            page_res = process_scanned_page(img_bgr, page_num=i + 1)
            results.append(page_res)

    return results


def convert_ocr_result_to_html(pages: List[OCRPageResult]) -> str:
    """OCR 복원 결과를 시맨틱 HTML 문서, 반응형 표 및 인라인 이미지로 렌더링함."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"ko\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<style>",
        "body { font-family: \"Pretendard Variable\", Pretendard, \"Noto Sans KR\", sans-serif; padding: 24px; color: #1e293b; line-height: 1.6; max-width: 900px; margin: 0 auto; }",
        ".page-container { margin-bottom: 40px; padding: 28px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }",
        ".page-badge { font-size: 11px; font-weight: 800; color: #0284c7; background: #e0f2fe; padding: 2px 8px; border-radius: 6px; display: inline-block; margin-bottom: 16px; font-family: Consolas, monospace; }",
        "h2 { font-size: 19px; font-weight: 800; color: #0f172a; margin: 16px 0 8px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }",
        "p { font-size: 14px; margin: 6px 0; }",
        "table.ocr-table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 13px; }",
        "table.ocr-table th, table.ocr-table td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; vertical-align: middle; }",
        "table.ocr-table tr:first-child td, table.ocr-table th { background: #f8fafc; font-weight: 700; color: #334155; }",
        "table.ocr-table tr:hover { background: #f1f5f9; }",
        ".ocr-figure-container { margin: 20px 0; text-align: center; }",
        ".ocr-figure-container img { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for page in pages:
        html_parts.append("<div class=\"page-container\">")
        html_parts.append(f"<span class=\"page-badge\">PAGE {page.page_num} (OCR & FIGURE RECONSTRUCTED)</span>")

        elements: List[Tuple[int, str, Any]] = []
        for tb in page.text_blocks:
            elements.append((tb.bbox[1], "text", tb))
        for table in page.tables:
            elements.append((table.bbox[1], "table", table))
        for fig in page.figures:
            elements.append((fig.bbox[1], "figure", fig))

        elements.sort(key=lambda x: x[0])

        for _, elem_type, elem in elements:
            if elem_type == "text":
                tb: OCRTextBlock = elem
                if tb.is_heading:
                    html_parts.append(f"<h2>{tb.text}</h2>")
                else:
                    html_parts.append(f"<p>{tb.text}</p>")
            elif elem_type == "table":
                t: OCRTable = elem
                grid = t.to_grid()
                if not grid or not any(any(c.strip() for c in row) for row in grid):
                    continue
                html_parts.append("<table class=\"ocr-table\"><tbody>")
                for r_idx, row in enumerate(grid):
                    html_parts.append("<tr>")
                    tag = "th" if r_idx == 0 else "td"
                    for cell_text in row:
                        val = cell_text.strip() if cell_text.strip() else "&nbsp;"
                        html_parts.append(f"<{tag}>{val}</{tag}>")
                    html_parts.append("</tr>")
                html_parts.append("</tbody></table>")
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                html_parts.append(f'<div class=\"ocr-figure-container\"><img src=\"{fig.base64_src}\" alt=\"문서 추출 이미지\" /></div>')

        html_parts.append("</div>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def convert_ocr_result_to_markdown(pages: List[OCRPageResult]) -> str:
    """OCR 복원 결과를 GFM 마크다운, 표 및 이미지 링크로 변환함."""
    md_lines: List[str] = []

    for page in pages:
        md_lines.append(f"## Page {page.page_num}\n")
        elements: List[Tuple[int, str, Any]] = []
        for tb in page.text_blocks:
            elements.append((tb.bbox[1], "text", tb))
        for table in page.tables:
            elements.append((table.bbox[1], "table", table))
        for fig in page.figures:
            elements.append((fig.bbox[1], "figure", fig))

        elements.sort(key=lambda x: x[0])

        for _, elem_type, elem in elements:
            if elem_type == "text":
                tb: OCRTextBlock = elem
                if tb.is_heading:
                    md_lines.append(f"### {tb.text}\n")
                else:
                    md_lines.append(f"{tb.text}\n")
            elif elem_type == "table":
                t: OCRTable = elem
                grid = t.to_grid()
                if not grid or not any(any(c.strip() for c in row) for row in grid):
                    continue
                cols = t.cols_count
                header = grid[0]
                md_lines.append("| " + " | ".join(c.strip() or "-" for c in header) + " |")
                md_lines.append("| " + " | ".join(["---"] * cols) + " |")
                for row in grid[1:]:
                    md_lines.append("| " + " | ".join(c.strip() or " " for c in row) + " |")
                md_lines.append("")
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                md_lines.append(f"![문서 추출 이미지]({fig.base64_src})\n")

        md_lines.append("---\n")

    return "\n".join(md_lines)


def convert_ocr_result_to_hwpx(pages: List[OCRPageResult], output_path: Path) -> None:
    """OCR 복원 결과를 한글 HWPX 문서 패키지, 표 객체 및 이미지로 변환함."""
    from hwpx.document import HwpxDocument

    doc = HwpxDocument.new()

    for page_idx, page in enumerate(pages):
        if page_idx > 0:
            doc.add_paragraph("")

        doc.add_paragraph(f"[페이지 {page.page_num}]")

        elements: List[Tuple[int, str, Any]] = []
        for tb in page.text_blocks:
            elements.append((tb.bbox[1], "text", tb))
        for table in page.tables:
            elements.append((table.bbox[1], "table", table))
        for fig in page.figures:
            elements.append((fig.bbox[1], "figure", fig))

        elements.sort(key=lambda x: x[0])

        for _, elem_type, elem in elements:
            if elem_type == "text":
                tb: OCRTextBlock = elem
                doc.add_paragraph(tb.text)
            elif elem_type == "table":
                t: OCRTable = elem
                grid = t.to_grid()
                if not grid:
                    continue
                num_rows = len(grid)
                num_cols = max(len(r) for r in grid)
                try:
                    tbl = doc.add_table(num_rows, num_cols)
                    for r in range(num_rows):
                        for c in range(min(num_cols, len(grid[r]))):
                            tbl.cell(r, c).text = grid[r][c]
                except Exception:
                    for r in grid:
                        doc.add_paragraph(" | ".join(r))
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                doc.add_paragraph(f"[그림: {fig.width}x{fig.height}px]")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(output_path)


def convert_ocr_result_to_docx(pages: List[OCRPageResult], output_path: Path) -> None:
    """OCR 복원 결과를 워드 DOCX 문서, 표 및 실제 삽입 이미지로 변환함."""
    import docx
    from docx.shared import Pt, Inches, RGBColor

    doc = docx.Document()

    for page_idx, page in enumerate(pages):
        if page_idx > 0:
            doc.add_page_break()

        elements: List[Tuple[int, str, Any]] = []
        for tb in page.text_blocks:
            elements.append((tb.bbox[1], "text", tb))
        for table in page.tables:
            elements.append((table.bbox[1], "table", table))
        for fig in page.figures:
            elements.append((fig.bbox[1], "figure", fig))

        elements.sort(key=lambda x: x[0])

        for _, elem_type, elem in elements:
            if elem_type == "text":
                tb: OCRTextBlock = elem
                if tb.is_heading:
                    doc.add_heading(tb.text, level=2)
                else:
                    doc.add_paragraph(tb.text)
            elif elem_type == "table":
                t: OCRTable = elem
                grid = t.to_grid()
                if not grid:
                    continue
                num_rows = len(grid)
                num_cols = max(len(r) for r in grid)
                tbl = doc.add_table(rows=num_rows, cols=num_cols)
                tbl.style = "Table Grid"
                for r in range(num_rows):
                    for c in range(min(num_cols, len(grid[r]))):
                        tbl.cell(r, c).text = grid[r][c]
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                try:
                    img_stream = io.BytesIO(fig.image_bytes)
                    img_w_in = min(5.5, max(1.5, fig.width / 150.0))
                    doc.add_picture(img_stream, width=Inches(img_w_in))
                except Exception:
                    doc.add_paragraph("[삽입 이미지]")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
