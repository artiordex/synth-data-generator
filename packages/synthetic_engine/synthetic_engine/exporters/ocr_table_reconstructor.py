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
import html
import io
import math
import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pymupdf
from ocr.text.korean_quality import korean_quality_score, special_character_ratio
from ocr.structure.reconstruction_models import ReconstructionOCRWord as OCRWord
from PIL import Image
from synthetic_engine.exporters.ocr_image_preprocessing import (
    _estimate_text_line_height,
    _ocr_upscale_factor,
    deskew_image,
    preprocess_ocr_image,
    remove_table_lines_for_handwriting,
)
from synthetic_engine.exporters.ocr_table_geometry import (
    GridCell,
    bbox_center as _bbox_center,
    detect_borderless_table_cells,
    detect_ruled_table_grids,
    detect_ruled_table_grids_v2,
    intersection_area as _intersection_area,
    point_in_bbox as _point_in_bbox,
    resolve_span_conflicts,
    snap_grid_boundaries,
    word_inside_any_table as _word_inside_any_table,
)
from synthetic_engine.exporters.ocr_recognition_bridge import recognize_page_words

_OCR_READERS: Dict[str, Any] = {}
_OCR_BACKEND = None
_KOREAN_SPACER = None


# multilingual readers 정보를 조회하여 반환함
def get_multilingual_readers() -> Dict[str, Any]:
    """Return the configured local backend through the legacy reader API.

    Engine construction belongs to ``packages/ocr``.  Keeping one owner avoids
    duplicate model downloads, private reader access, and configuration drift.
    """
    global _OCR_READERS
    if "local_backend" not in _OCR_READERS:
        _OCR_READERS["local_backend"] = get_ocr_backend()
    return _OCR_READERS


# OCR 인식 reader 정보를 조회하여 반환함
def get_ocr_reader():
    """Return the common OCR backend for legacy callers."""
    return get_multilingual_readers()["local_backend"]


# OCR 인식 backend 정보를 조회하여 반환함
def get_ocr_backend():
    """Return the configured fully local OCR backend as a lazy singleton."""
    global _OCR_BACKEND
    if _OCR_BACKEND is None:
        from ocr.engine import build_local_ocr_backend

        _OCR_BACKEND = build_local_ocr_backend(Path.cwd())
    return _OCR_BACKEND


# vertical overlap ratio 작업을 수행함
def _vertical_overlap_ratio(left: OCRWord, right: OCRWord) -> float:
    """Return overlap relative to the shorter word height."""
    overlap = max(0, min(left.bbox[3], right.bbox[3]) - max(left.bbox[1], right.bbox[1]))
    left_height = max(1, left.bbox[3] - left.bbox[1])
    right_height = max(1, right.bbox[3] - right.bbox[1])
    return overlap / min(left_height, right_height)


# cluster words into lines 작업을 수행함
def _cluster_words_into_lines(words: List[OCRWord]) -> List[List[OCRWord]]:
    """Cluster words using strict 50% vertical overlap, then order the lines.

    A line is compatible with a new word only when the word overlaps one of
    the line's existing words by at least half of the shorter word's height.
    This keeps adjacent lines independent even when OCR reports slightly
    different top coordinates or font sizes.
    """
    lines: List[List[OCRWord]] = []
    for word in sorted(words, key=lambda item: (item.center[1], item.bbox[0])):
        candidates = []
        for index, line in enumerate(lines):
            overlap = max(_vertical_overlap_ratio(word, member) for member in line)
            if overlap >= 0.5:
                line_center = sum(member.center[1] for member in line) / len(line)
                candidates.append((overlap, -abs(word.center[1] - line_center), index))
        if candidates:
            lines[max(candidates)[2]].append(word)
        else:
            lines.append([word])

    return sorted(
        (sorted(line, key=lambda item: (item.bbox[0], item.bbox[1])) for line in lines),
        key=lambda line: (sum(item.center[1] for item in line) / len(line), line[0].bbox[0]),
    )


# 병합 adjacent word fragments 작업을 수행함
def _merge_adjacent_word_fragments(line: List[OCRWord]) -> List[OCRWord]:
    """Join alphanumeric fragments only when their geometry shows no word gap."""
    if len(line) < 2:
        return line
    char_widths = [
        (word.bbox[2] - word.bbox[0]) / max(1, len(re.sub(r"\s+", "", word.text)))
        for word in line if word.text.strip()
    ]
    average_char_width = float(np.median(char_widths)) if char_widths else 0.0
    merged: List[OCRWord] = []
    for word in line:
        if not merged:
            merged.append(word)
            continue
        previous = merged[-1]
        gap = word.bbox[0] - previous.bbox[2]
        left_text = previous.text.strip()
        right_text = word.text.strip()
        alphanumeric = bool(re.fullmatch(r"[A-Za-z0-9]+", left_text + right_text))
        attached = (
            alphanumeric
            and average_char_width > 0
            and gap >= -0.25 * average_char_width
            and gap <= 0.45 * average_char_width
        )
        if attached:
            merged[-1] = OCRWord(
                text=left_text + right_text,
                bbox=(
                    min(previous.bbox[0], word.bbox[0]),
                    min(previous.bbox[1], word.bbox[1]),
                    max(previous.bbox[2], word.bbox[2]),
                    max(previous.bbox[3], word.bbox[3]),
                ),
                confidence=min(previous.confidence, word.confidence),
            )
        else:
            merged.append(word)
    return merged


# english tokens 데이터를 표준 형식으로 정규화함
def _normalize_english_tokens(text: str) -> str:
    """Apply Unicode normalization without guessing missing English spaces."""
    return unicodedata.normalize("NFC", str(text))


# korean 텍스트 데이터를 표준 형식으로 정규화함
def _normalize_korean_text(text: str) -> str:
    """Normalize Korean spacing only when no non-space character changes."""
    return _restore_korean_spacing(unicodedata.normalize("NFC", str(text)))


# japanese 텍스트 데이터를 표준 형식으로 정규화함
def _normalize_japanese_text(text: str) -> str:
    """Preserve Japanese OCR content; correction belongs to measured models."""
    return unicodedata.normalize("NFC", str(text))


# chinese 텍스트 데이터를 표준 형식으로 정규화함
def _normalize_chinese_text(text: str) -> str:
    """Preserve Chinese OCR content; never translate or replace whole lines."""
    return unicodedata.normalize("NFC", str(text))


# multilingual line 데이터를 표준 형식으로 정규화함
def _normalize_multilingual_line(text: str) -> str:
    """문자열의 주요 언어 스크립트를 판별하여 적합한 정규화를 적용함."""
    trimmed = text.strip()
    if not trimmed:
        return ""
    if re.search(r"[가-힣]", trimmed):
        return _normalize_korean_text(trimmed)
    if re.search(r"[ぁ-ゟァ-ヿ]", trimmed):
        return _normalize_japanese_text(trimmed)
    if re.search(r"[一-鿿]", trimmed):
        return _normalize_chinese_text(trimmed)
    return _normalize_english_tokens(trimmed)


# line 텍스트 작업을 수행함
def _line_text(line: List[OCRWord]) -> str:
    value = " ".join(
        word.text.strip()
        for word in _merge_adjacent_word_fragments(line)
        if word.text.strip()
    ).strip()
    return _normalize_multilingual_line(value)


@dataclass
class OCRTableCell:
    row: int
    col: int
    rowspan: int
    colspan: int
    bbox: Tuple[int, int, int, int]
    words: List[OCRWord] = field(default_factory=list)
    bg_color_hex: str = "#ffffff"
    border_styles: Dict[str, str] = field(default_factory=dict)
    text_align: str = "left"
    is_border_detected: bool = True
    confidence: float = 1.0
    control_type: Optional[str] = None
    control_state: Optional[str] = None
    figures: List["OCRFigureBlock"] = field(default_factory=list)
    borders: Dict[str, bool] = field(default_factory=dict)
    border_confidence: Dict[str, float] = field(default_factory=dict)
    grid_confidence: float = 1.0
    source: str = "ruled_legacy"

    # 텍스트 작업을 수행함
    @property
    def text(self) -> str:
        lines = _cluster_words_into_lines(self.words)
        return "\n".join(_line_text(line) for line in lines).strip()


@dataclass
class OCRTable:
    bbox: Tuple[int, int, int, int]
    cells: List[OCRTableCell] = field(default_factory=list)
    rows_count: int = 0
    cols_count: int = 0

    x_lines: Tuple[int, ...] = ()
    y_lines: Tuple[int, ...] = ()
    grid_confidence: float = 1.0
    source: str = "ruled_legacy"

    # 격자 구조 형식으로 변환하여 반환함
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

    # base64 src 작업을 수행함
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
    ocr_engine: str = ""
    mean_confidence: float = 0.0
    requires_review: bool = False
    warnings: List[str] = field(default_factory=list)

    # full 텍스트 작업을 수행함
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


# scanned PDF 문서 여부 및 유효성을 판별함
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


# 감지 표(테이블) 격자 구조 셀 목록 작업을 수행함
def detect_table_grid_cells(
    img_gray: np.ndarray,
    min_cell_w: int = 30,
    min_cell_h: int = 15,
    min_table_area: int = 8000,
) -> List[OCRTable]:
    """Detect v2 ruled grids first, retaining legacy-only table regions."""

    # convert 작업을 수행함
    def convert(grid: Any) -> OCRTable:
        return OCRTable(
            bbox=grid.bbox,
            cells=[
                OCRTableCell(
                    row=cell.row_start,
                    col=cell.col_start,
                    rowspan=cell.rowspan,
                    colspan=cell.colspan,
                    bbox=cell.bbox,
                    is_border_detected=cell.is_border_detected,
                    borders=dict(cell.borders),
                    border_confidence=dict(cell.border_confidence),
                    grid_confidence=cell.grid_confidence,
                    source=cell.source,
                )
                for cell in grid.cells
            ],
            rows_count=grid.rows_count,
            cols_count=grid.cols_count,
            x_lines=tuple(grid.x_lines),
            y_lines=tuple(grid.y_lines),
            grid_confidence=float(grid.confidence),
            source=grid.source,
        )

    candidates = [
        convert(grid)
        for grid in detect_ruled_table_grids_v2(
            img_gray,
            min_table_area=min_table_area,
        )
        if grid.confidence >= 0.50
    ]
    for grid in detect_ruled_table_grids(
        img_gray,
        min_cell_w=min_cell_w,
        min_cell_h=min_cell_h,
        min_table_area=min_table_area,
    ):
        table = convert(grid)
        if not any(_bbox_iou(table.bbox, existing.bbox) >= 0.55 for existing in candidates):
            candidates.append(table)
    return sorted(candidates, key=lambda table: (table.bbox[1], table.bbox[0]))


# 바운딩 박스 iou 작업을 수행함
def _bbox_iou(
    left: Tuple[int, int, int, int], right: Tuple[int, int, int, int]
) -> float:
    intersection = _intersection_area(left, right)
    left_area = max(1, (left[2] - left[0]) * (left[3] - left[1]))
    right_area = max(1, (right[2] - right[0]) * (right[3] - right[1]))
    return intersection / max(1, left_area + right_area - intersection)


# deduplicate 표 목록 작업을 수행함
def _deduplicate_tables(
    tables: List[OCRTable], *, iou_threshold: float = 0.55
) -> List[OCRTable]:
    priority = {"ruled_v2": 2, "ruled_legacy": 1, "borderless": 0}
    kept: List[OCRTable] = []
    for table in sorted(
        tables,
        key=lambda item: (
            -priority.get(item.source, 0),
            -item.grid_confidence,
            item.bbox[1],
            item.bbox[0],
        ),
    ):
        if any(_bbox_iou(table.bbox, existing.bbox) >= iou_threshold for existing in kept):
            continue
        kept.append(table)
    return sorted(kept, key=lambda table: (table.bbox[1], table.bbox[0]))


# 감지 이미지 figures 작업을 수행함
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
        # 페이지 전체를 잘못 캡처하는 윤곽선은 제외함
        if fw > w * 0.95 and fh > h * 0.95:
            continue
        # 가로 비율이 극단적으로 긴 텍스트 줄 형태(종횡비 2.5 이상 또는 높이 50px 미만)는 이미지 요소에서 배제함
        if fw / max(1, fh) >= 2.5 or fh < 50:
            continue
        # 추출 영역이 인식 텍스트 박스와 겹치는 경우 배제함
        if any(_intersection_area((fx, fy, fx + fw, fy + fh), wd.bbox) > 0 for wd in words):
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


# 감지 표(테이블) 셀 figures 작업을 수행함
def _detect_table_cell_figures(
    img_bgr: np.ndarray,
    tables: List[OCRTable],
    words: List[OCRWord],
) -> List[OCRFigureBlock]:
    """Detect non-text image regions that live inside a recovered table cell."""
    if not tables:
        return []
    h, w = img_bgr.shape[:2]
    figures: List[OCRFigureBlock] = []
    seen: set[Tuple[int, int, int, int]] = set()

    for table in tables:
        for cell in table.cells:
            x0, y0, x1, y1 = cell.bbox
            x0, y0 = max(0, x0 + 3), max(0, y0 + 3)
            x1, y1 = min(w, x1 - 3), min(h, y1 - 3)
            if x1 - x0 < 24 or y1 - y0 < 24:
                continue

            crop = img_bgr[y0:y1, x0:x1].copy()
            if crop.ndim == 2:
                crop_bgr = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            else:
                crop_bgr = crop
            for word in words:
                wx0, wy0, wx1, wy1 = word.bbox
                if wx1 <= x0 or wx0 >= x1 or wy1 <= y0 or wy0 >= y1:
                    continue
                lx0, ly0 = max(0, wx0 - x0 - 3), max(0, wy0 - y0 - 3)
                lx1, ly1 = min(x1 - x0, wx1 - x0 + 3), min(y1 - y0, wy1 - y0 + 3)
                crop_bgr[ly0:ly1, lx0:lx1] = 255

            if cell.is_border_detected:
                crop_bgr = remove_table_lines_for_handwriting(
                    crop_bgr,
                    (0, 0, crop_bgr.shape[1], crop_bgr.shape[0]),
                )

            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
            foreground = ((gray < 235) | (hsv[:, :, 1] > 45)).astype(np.uint8) * 255
            foreground = cv2.morphologyEx(
                foreground,
                cv2.MORPH_OPEN,
                cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
            )
            foreground = cv2.morphologyEx(
                foreground,
                cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)),
            )
            contours, _ = cv2.findContours(
                foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            min_cell_area = max(500, int((x1 - x0) * (y1 - y0) * 0.025))
            for contour in contours:
                fx, fy, fw, fh = cv2.boundingRect(contour)
                if fw * fh < min_cell_area or fw < 18 or fh < 18:
                    continue
                page_bbox = (x0 + fx, y0 + fy, x0 + fx + fw, y0 + fy + fh)
                if page_bbox in seen:
                    continue
                figure_crop = img_bgr[page_bbox[1]:page_bbox[3], page_bbox[0]:page_bbox[2]]
                if figure_crop.size == 0 or np.std(figure_crop) < 10:
                    continue
                success, buf = cv2.imencode(".png", figure_crop)
                if not success:
                    continue
                seen.add(page_bbox)
                figures.append(OCRFigureBlock(
                    bbox=page_bbox,
                    image_bytes=buf.tobytes(),
                    format="png",
                    width=fw,
                    height=fh,
                ))

    figures.sort(key=lambda f: (f.bbox[1], f.bbox[0]))
    return figures


# assign figures to 표(테이블) 셀 목록 작업을 수행함
def _assign_figures_to_table_cells(tables: List[OCRTable], figures: List[OCRFigureBlock]) -> None:
    """Attach figures whose center falls inside a logical table cell."""
    for table in tables:
        for cell in table.cells:
            cell.figures.clear()
    for figure in figures:
        center = _bbox_center(figure.bbox)
        for table in tables:
            if not _point_in_bbox(center, table.bbox):
                continue
            for cell in table.cells:
                if _point_in_bbox(center, cell.bbox):
                    cell.figures.append(figure)
                    break
            break


# PDF 문서 embedded 이미지 목록 요소를 추출하여 반환함
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



# deduplicate line words 작업을 수행함
def _deduplicate_line_words(line: List[OCRWord]) -> List[OCRWord]:
    """한 라인 안에서 중복 인식된 후보를 NMS로 정리하고 독립된 어절을 모두 보존함."""
    if len(line) <= 1:
        return line
    sorted_words = sorted(line, key=lambda w: w.bbox[0])
    kept: List[OCRWord] = []
    for w in sorted_words:
        if not kept:
            kept.append(w)
            continue
        prev = kept[-1]
        overlap_w = min(prev.bbox[2], w.bbox[2]) - max(prev.bbox[0], w.bbox[0])
        min_w = min(prev.bbox[2] - prev.bbox[0], w.bbox[2] - w.bbox[0])
        if min_w > 0 and overlap_w / min_w > 0.4:
            # 중복 영역: 한글 포함 수 및 신뢰도를 종합 비교하여 우수 후보 채택함
            prev_ko = len(re.findall(r"[가-힣]", prev.text))
            w_ko = len(re.findall(r"[가-힣]", w.text))
            if (w_ko, w.confidence) > (prev_ko, prev.confidence):
                kept[-1] = w
        else:
            kept.append(w)
    return kept


# OCR 인식 on 이미지 작업을 실행함
def _run_ocr_on_image(img_np: np.ndarray) -> List[OCRWord]:
    """Recognize a page and adapt bridge words to the reconstructor schema."""
    return [
        OCRWord(word.text, word.bbox, word.confidence)
        for word in recognize_page_words(img_np, backend_factory=get_ocr_backend)
    ]


# contains 한중일 다국어 작업을 수행함
def _contains_cjk(text: str) -> bool:
    """Detect Korean, Japanese kana, or Han characters in OCR output."""
    return bool(re.search(r"[가-힣ぁ-ゟァ-ヿ一-鿿]", str(text)))


# special 문자 ratio 작업을 수행함
def _special_character_ratio(text: str) -> float:
    """Measure characters that cannot belong to supported OCR scripts."""
    return special_character_ratio(text)


# garbage OCR 인식 word 여부 및 유효성을 판별함
def _is_garbage_ocr_word(word: OCRWord) -> bool:
    return word.confidence < 0.60 or _special_character_ratio(word.text) >= 0.25


# 보정 low 품질 words 작업을 수행함
def _repair_low_quality_words(image: np.ndarray, words: List[OCRWord]) -> List[OCRWord]:
    """Preserve low-quality OCR evidence for review instead of guessing text.

    Targeted retries are owned by the common ensemble backend.  Replacing text
    here would discard the engine's raw prediction and make confidence
    calibration impossible.
    """
    return list(words)


# apply korean spacing 작업을 수행함
def _apply_korean_spacing(words: List[OCRWord]) -> List[OCRWord]:
    """Compatibility helper that preserves per-word OCR evidence.

    Spacing is reconstructed after line clustering, never inside OCR word
    records whose raw text and bbox are audit data.
    """
    return list(words)


# restore korean spacing 작업을 수행함
@lru_cache(maxsize=4096)
def _restore_korean_spacing(text: str) -> str:
    """Use Kiwi only when spacing changes do not alter any other character."""
    global _KOREAN_SPACER
    corrected = unicodedata.normalize("NFC", str(text))
    if os.getenv("OCR_KOREAN_SPACING", "true").strip().lower() not in {
        "1", "true", "yes", "on"
    }:
        return corrected
    if len(corrected) < 4 or not re.search(r"[가-힣]", corrected):
        return corrected
    # Structured identifiers and numeric fields are audit-sensitive.  Kiwi is
    # intentionally skipped for the whole OCR line rather than risking a new
    # space inside dates, amounts, phone numbers, filenames or codes.
    if re.search(r"\d|https?://|\b[^\s@]+@[^\s@]+\b|[\\/:@%₩$€¥]", corrected):
        return corrected
    try:
        if _KOREAN_SPACER is None:
            from kiwipiepy import Kiwi

            _KOREAN_SPACER = Kiwi()
        spaced = str(_KOREAN_SPACER.space(corrected, reset_whitespace=False))
    except (ImportError, RuntimeError, ValueError):
        return corrected
    compact = lambda value: re.sub(r"\s+", "", value)
    return spaced if compact(spaced) == compact(corrected) else corrected


# assign words to 표 목록 작업을 수행함
def assign_words_to_tables(
    words: List[OCRWord],
    tables: List[OCRTable],
    *,
    min_overlap_ratio: float = 0.35,
) -> Tuple[List[OCRTable], List[OCRWord]]:
    """Bind words by bbox coverage and return words that remain outside tables.

    The primary ratio is intersection / word area. A word substantially covered
    by a table is consumed by the table even when damage to the grid leaves no
    cell above the binding threshold, preventing duplicate plain-text output.
    """

    for table in tables:
        for cell in table.cells:
            cell.words.clear()

    outside_words: List[OCRWord] = []
    for word in words:
        word_area = max(
            1,
            (word.bbox[2] - word.bbox[0]) * (word.bbox[3] - word.bbox[1]),
        )
        center = word.center
        table_coverage = max(
            (_intersection_area(word.bbox, table.bbox) / word_area for table in tables),
            default=0.0,
        )
        candidates: List[Tuple[float, bool, float, float, OCRTableCell]] = []
        for table in tables:
            if _intersection_area(word.bbox, table.bbox) <= 0:
                continue
            for cell in table.cells:
                overlap_ratio = _intersection_area(word.bbox, cell.bbox) / word_area
                if overlap_ratio < min_overlap_ratio:
                    continue
                cell_center = _bbox_center(cell.bbox)
                distance = math.hypot(center[0] - cell_center[0], center[1] - cell_center[1])
                candidates.append((
                    overlap_ratio,
                    _point_in_bbox(center, cell.bbox),
                    float(cell.grid_confidence),
                    -distance,
                    cell,
                ))
        if candidates:
            # A validated logical span supersedes any accidentally retained
            # primitive candidate. Normal occupancy maps never contain both.
            merged_candidates = [
                item for item in candidates
                if item[-1].rowspan > 1 or item[-1].colspan > 1
            ]
            if merged_candidates:
                candidates = merged_candidates
            # Stable criteria: overlap, center hit, cell/grid confidence, then
            # nearest cell centre.
            chosen = max(candidates, key=lambda item: item[:-1])[-1]
            chosen.words.append(word)
        elif table_coverage < min_overlap_ratio:
            outside_words.append(word)

    for table in tables:
        for cell in table.cells:
            cell.words.sort(key=lambda item: (
                item.center[1] - cell.bbox[1],
                item.bbox[0] - cell.bbox[0],
            ))
    return tables, outside_words


# 셀 OCR 인식 품질 작업을 수행함
def _cell_ocr_quality(text: str, confidence: float) -> float:
    value = text.strip()
    if not value:
        return -1.0
    return (
        max(0.0, min(1.0, confidence)) * 0.50
        + korean_quality_score(value) * 0.30
        + (1.0 - special_character_ratio(value)) * 0.20
    )


# recognize 표(테이블) 셀 목록 작업을 수행함
def recognize_table_cells(
    image: np.ndarray,
    table: OCRTable,
    backend: Any,
    *,
    max_cells: int = 80,
    min_cell_area: int = 900,
) -> OCRTable:
    """Optionally replace low-quality page OCR with better cell-crop OCR.

    Crop OCR boxes are mapped from padded crop coordinates back into the
    deskewed page coordinate space before they are stored.
    """

    if (
        os.getenv("OCR_TABLE_CELL_RECOGNITION", "false").strip().lower()
        not in {"1", "true", "yes", "on"}
        or table.source != "ruled_v2"
        or table.grid_confidence < 0.55
        or len(table.cells) > max_cells
    ):
        return table
    height, width = image.shape[:2]
    high_confidence = float(os.getenv("OCR_TABLE_CELL_SKIP_CONFIDENCE", "0.92"))
    for cell in table.cells:
        x0, y0, x1, y1 = cell.bbox
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(width, x1), min(height, y1)
        if (x1 - x0) * (y1 - y0) < min_cell_area or cell.figures:
            continue
        existing_confidence = (
            sum(word.confidence for word in cell.words) / len(cell.words)
            if cell.words else 0.0
        )
        if cell.words and existing_confidence >= high_confidence:
            continue
        crop = image[y0:y1, x0:x1].copy()
        if crop.size == 0:
            continue
        cleaned = remove_table_lines_for_handwriting(
            crop, (0, 0, crop.shape[1], crop.shape[0])
        )
        padding = max(4, min(12, int(round(min(crop.shape[:2]) * 0.08))))
        padded = cv2.copyMakeBorder(
            cleaned, padding, padding, padding, padding,
            cv2.BORDER_CONSTANT,
            value=255 if cleaned.ndim == 2 else tuple(255 for _ in range(cleaned.shape[2])),
        )
        recognized = recognize_page_words(padded, backend_factory=lambda: backend)
        candidate_words = [
            OCRWord(
                word.text,
                (
                    max(x0, min(x1, x0 + word.bbox[0] - padding)),
                    max(y0, min(y1, y0 + word.bbox[1] - padding)),
                    max(x0, min(x1, x0 + word.bbox[2] - padding)),
                    max(y0, min(y1, y0 + word.bbox[3] - padding)),
                ),
                word.confidence,
            )
            for word in recognized
            if word.text.strip()
        ]
        candidate_words = [
            word for word in candidate_words
            if word.bbox[2] > word.bbox[0] and word.bbox[3] > word.bbox[1]
        ]
        if not candidate_words:
            continue
        candidate_text = "\n".join(
            _line_text(line) for line in _cluster_words_into_lines(candidate_words)
        ).strip()
        existing_text = cell.text
        if existing_text:
            length_ratio = len(candidate_text) / max(1, len(existing_text))
            if length_ratio < 0.35 or length_ratio > 3.0:
                continue
        candidate_confidence = sum(word.confidence for word in candidate_words) / len(candidate_words)
        if _cell_ocr_quality(candidate_text, candidate_confidence) <= _cell_ocr_quality(
            existing_text, existing_confidence
        ) + 0.03:
            continue
        cell.words = candidate_words
        cell.confidence = candidate_confidence
    return table


# scanned 페이지 데이터를 처리함
def process_scanned_page(
    page_img_np: np.ndarray, page_num: int
) -> OCRPageResult:
    """단일 페이지에 대해 기울기 보정, 표 검출, 사진/도표 추출 및 OCR 바인딩을 수행함.

    Coordinate-space contract:
    ``page_img_np`` is the original rendered-pixel space. ``deskewed_img`` and
    ``gray`` are the deskewed processing space. Every OCRWord, OCRTable and
    OCRTableCell bbox returned by this function is in deskewed page pixels.
    OCR-only preprocessing/upscaling must map results back to that space; cell
    crop OCR additionally maps crop-relative boxes back to page coordinates.
    """
    # 1. Deskew (기울기 자동 보정)
    deskewed_img, _ = deskew_image(page_img_np)

    h, w = deskewed_img.shape[:2]
    if len(deskewed_img.shape) == 3:
        gray = cv2.cvtColor(deskewed_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = deskewed_img

    # 2. 텍스트 OCR
    all_words = _run_ocr_on_image(deskewed_img)

    # 3. 표 검출: 실선 격자를 우선하고, 남은 OCR 투영으로 무괘선
    # 격자를 추가 복원함. 텍스트는 표 구조를 바꾸지 않고 셀에만 바인딩함.
    tables = detect_table_grid_cells(gray)
    borderless_words = [
        word for word in all_words
        if not _word_inside_any_table(word, tables)
    ]
    if borderless_words:
        grid_cells = resolve_span_conflicts(
            detect_borderless_table_cells(gray, borderless_words), borderless_words
        )
        if grid_cells:
            tables.append(OCRTable(
                bbox=(
                    min(cell.bbox[0] for cell in grid_cells),
                    min(cell.bbox[1] for cell in grid_cells),
                    max(cell.bbox[2] for cell in grid_cells),
                    max(cell.bbox[3] for cell in grid_cells),
                ),
                cells=[OCRTableCell(
                    row=cell.row_start,
                    col=cell.col_start,
                    rowspan=cell.rowspan,
                    colspan=cell.colspan,
                    bbox=cell.bbox,
                    is_border_detected=cell.is_border_detected,
                    borders=dict(cell.borders),
                    border_confidence=dict(cell.border_confidence),
                    grid_confidence=cell.grid_confidence,
                    source="borderless",
                ) for cell in grid_cells],
                rows_count=max(cell.row_end for cell in grid_cells),
                cols_count=max(cell.col_end for cell in grid_cells),
                grid_confidence=0.45,
                source="borderless",
            ))
    tables = _deduplicate_tables(tables)

    # 4. 사진/도표(Figure) 검출
    figures = detect_image_figures(deskewed_img, tables, all_words)
    figures.extend(_detect_table_cell_figures(deskewed_img, tables, all_words))
    figures.sort(key=lambda figure: (figure.bbox[1], figure.bbox[0]))
    _assign_figures_to_table_cells(tables, figures)

    # 5. 셀 텍스트 바인딩: center hit 대신 word-area overlap을 기준으로 처리함.
    tables, unassigned_words = assign_words_to_tables(all_words, tables)
    if os.getenv("OCR_TABLE_CELL_RECOGNITION", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }:
        backend = get_ocr_backend()
        for table in tables:
            recognize_table_cells(deskewed_img, table, backend)

    # Style extraction is geometry-only and therefore cannot change the grid.
    from synthetic_engine.exporters.ocr_style_extractor import (
        detect_cell_border_styles,
        detect_text_alignment,
        extract_cell_background_color,
    )
    for table in tables:
        for cell in table.cells:
            cell.bg_color_hex = extract_cell_background_color(deskewed_img, cell.bbox)
            if cell.is_border_detected:
                cell.border_styles = detect_cell_border_styles(gray, cell.bbox)
            if cell.words:
                text_bbox = (
                    min(word.bbox[0] for word in cell.words),
                    min(word.bbox[1] for word in cell.words),
                    max(word.bbox[2] for word in cell.words),
                    max(word.bbox[3] for word in cell.words),
                )
                cell.text_align = detect_text_alignment(cell.bbox, text_bbox)
                cell.confidence = sum(word.confidence for word in cell.words) / len(cell.words)

    raw_blocks: List[OCRTextBlock] = []
    for line in _cluster_words_into_lines(unassigned_words):
        line_text = _line_text(line)
        if not line_text:
            continue
        bx0 = min(w.bbox[0] for w in line)
        by0 = min(w.bbox[1] for w in line)
        bx1 = max(w.bbox[2] for w in line)
        by1 = max(w.bbox[3] for w in line)
        raw_blocks.append(OCRTextBlock(
            text=line_text,
            bbox=(bx0, by0, bx1, by1),
            is_heading=(by1 - by0) > 24 or (len(line_text) < 30 and (line_text.startswith("#") or line_text.endswith(":"))),
            font_scale=(by1 - by0) / 16.0
        ))

    text_blocks: List[OCRTextBlock] = []
    idx = 0
    while idx < len(raw_blocks):
        current = raw_blocks[idx]
        # 우측 끝 줄바꿈(word wrap)으로 분리된 문장을 자동 결합함
        while idx + 1 < len(raw_blocks):
            nxt = raw_blocks[idx + 1]
            curr_h = max(1, current.bbox[3] - current.bbox[1])
            vert_gap = nxt.bbox[1] - current.bbox[3]
            is_wrapped = (
                current.bbox[2] >= w - 35
                and nxt.bbox[0] <= 45
                and 0 <= vert_gap <= 1.8 * curr_h
                and not re.search(r"[.!?:\>]\s*$", current.text.strip())
                and not current.is_heading
                and not nxt.is_heading
            )
            if is_wrapped:
                combined_text = _normalize_multilingual_line(f"{current.text} {nxt.text}")
                new_bbox = (
                    min(current.bbox[0], nxt.bbox[0]),
                    min(current.bbox[1], nxt.bbox[1]),
                    max(current.bbox[2], nxt.bbox[2]),
                    max(current.bbox[3], nxt.bbox[3]),
                )
                current = OCRTextBlock(
                    text=combined_text,
                    bbox=new_bbox,
                    is_heading=False,
                    font_scale=current.font_scale,
                )
                idx += 1
            else:
                break
        text_blocks.append(current)
        idx += 1

    return OCRPageResult(
        page_num=page_num,
        width=w,
        height=h,
        tables=tables,
        text_blocks=text_blocks,
        figures=figures,
        ocr_engine=getattr(_OCR_BACKEND, "name", "legacy_local_ocr"),
        mean_confidence=(
            sum(word.confidence for word in all_words) / len(all_words)
            if all_words
            else 0.0
        ),
        requires_review=(
            not all_words
            or any(
                word.confidence < float(os.getenv("OCR_REVIEW_THRESHOLD", "0.85"))
                for word in all_words
            )
        ),
        warnings=(
            ["OCR 결과에 사람이 확인해야 할 저신뢰 텍스트가 있습니다."]
            if all_words and any(
                word.confidence < float(os.getenv("OCR_REVIEW_THRESHOLD", "0.85"))
                for word in all_words
            )
            else (["검색 가능한 텍스트를 추출하지 못했습니다."] if not all_words else [])
        ),
    )


# native 페이지 이미지 작업을 수행함
def _native_page_image(doc: pymupdf.Document, page: pymupdf.Page) -> Optional[np.ndarray]:
    """Extract a single full-page scan without lossy PDF re-rendering."""
    if os.getenv("OCR_USE_NATIVE_PDF_IMAGE", "true").strip().lower() not in {
        "1", "true", "yes", "on"
    }:
        return None
    images = page.get_images(full=True)
    if len(images) != 1:
        return None
    xref = images[0][0]
    rects = page.get_image_rects(xref)
    if not rects:
        return None
    page_area = max(1.0, page.rect.width * page.rect.height)
    covered_area = max(rect.width * rect.height for rect in rects)
    if covered_area / page_area < 0.80:
        return None
    try:
        payload = doc.extract_image(xref).get("image", b"")
        if not payload:
            return None
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return None
        rotation = int(getattr(page, "rotation", 0) or 0) % 360
        if rotation == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if rotation == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        if rotation == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image
    except (OSError, RuntimeError, ValueError):
        return None


# scanned PDF 문서 페이지 목록 요소를 추출하여 반환함
def extract_scanned_pdf_pages(pdf_path: Path, dpi: Optional[int] = None) -> List[OCRPageResult]:
    """스캔본 PDF의 모든 페이지를 고화질 이미지로 렌더링하고 표, 사진, 본문을 복원함."""
    results: List[OCRPageResult] = []
    dpi = dpi or int(os.getenv("OCR_RENDER_DPI", "300"))
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)

    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            img_bgr = _native_page_image(doc, page)
            if img_bgr is None:
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                if pix.n == 3:
                    img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
                elif pix.n == 1:
                    img_bgr = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)
                else:
                    img_bgr = img_data

            page_res = process_scanned_page(img_bgr, page_num=i + 1)
            results.append(page_res)

    return results


# HTML 웹 문서 셀 스타일 서식 작업을 수행함
def _html_cell_style(cell: OCRTableCell) -> str:
    border_map = {"none": "none", "solid": "1px solid #334155", "dashed": "1px dashed #334155", "double": "3px double #334155"}
    bg_color = (
        cell.bg_color_hex
        if re.fullmatch(r"#[0-9a-fA-F]{6}", str(cell.bg_color_hex))
        else "#ffffff"
    )
    text_align = cell.text_align if cell.text_align in {"left", "center", "right"} else "left"
    declarations = [
        f"background-color:{bg_color}",
        f"text-align:{text_align}",
    ]
    for side in ("top", "right", "bottom", "left"):
        if side in cell.border_styles:
            declarations.append(f"border-{side}:{border_map.get(cell.border_styles[side], border_map['solid'])}")
        elif side in cell.borders:
            declarations.append(
                f"border-{side}:{border_map['solid'] if cell.borders[side] else border_map['none']}"
            )
    return ";".join(declarations)


# HTML 웹 문서 텍스트 with breaks 작업을 수행함
def _html_text_with_breaks(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


# 표(테이블) anchor map 작업을 수행함
def _table_anchor_map(table: OCRTable) -> Tuple[Dict[Tuple[int, int], OCRTableCell], set[Tuple[int, int]]]:
    anchors: Dict[Tuple[int, int], OCRTableCell] = {}
    covered: set[Tuple[int, int]] = set()
    for cell in sorted(table.cells, key=lambda item: (item.row, item.col)):
        anchors[(cell.row, cell.col)] = cell
        for row in range(cell.row, min(table.rows_count, cell.row + cell.rowspan)):
            for col in range(cell.col, min(table.cols_count, cell.col + cell.colspan)):
                if (row, col) != (cell.row, cell.col):
                    covered.add((row, col))
    return anchors, covered


# 표(테이블) 컬럼 너비 목록 작업을 수행함
def _table_column_widths(table: OCRTable) -> List[int]:
    if len(table.x_lines) == table.cols_count + 1:
        return [
            right - left
            for left, right in zip(table.x_lines, table.x_lines[1:])
            if right > left
        ]
    boundaries = snap_grid_boundaries(
        [cell.bbox[0] for cell in table.cells],
        [cell.bbox[2] for cell in table.cells],
        tolerance=5,
    )
    widths = [right - left for left, right in zip(boundaries, boundaries[1:]) if right > left]
    if len(widths) == table.cols_count:
        return widths
    return [1] * max(1, table.cols_count)


# 표(테이블) 행 heights 작업을 수행함
def _table_row_heights(table: OCRTable) -> List[int]:
    if len(table.y_lines) == table.rows_count + 1:
        return [
            bottom - top
            for top, bottom in zip(table.y_lines, table.y_lines[1:])
            if bottom > top
        ]
    boundaries = snap_grid_boundaries(
        [cell.bbox[1] for cell in table.cells],
        [cell.bbox[3] for cell in table.cells],
        tolerance=5,
    )
    heights = [bottom - top for top, bottom in zip(boundaries, boundaries[1:]) if bottom > top]
    return heights if len(heights) == table.rows_count else []


# 표(테이블) is complex 작업을 수행함
def _table_is_complex(table: OCRTable) -> bool:
    if any(cell.rowspan > 1 or cell.colspan > 1 for cell in table.cells):
        return True
    if any("\n" in cell.text for cell in table.cells):
        return True
    widths, heights = _table_column_widths(table), _table_row_heights(table)
    for dimensions in (widths, heights):
        if dimensions and min(dimensions) > 0 and max(dimensions) / min(dimensions) >= 1.8:
            return True
    styles = {
        style
        for cell in table.cells
        for style in cell.border_styles.values()
    }
    if len(styles) > 1:
        return True
    return table.grid_confidence < 0.65


# 표(테이블) HTML 웹 문서 fragment 데이터를 타깃 포맷으로 렌더링함
def _render_table_html_fragment(table: OCRTable) -> str:
    anchors, covered = _table_anchor_map(table)
    widths = _table_column_widths(table)
    heights = _table_row_heights(table)
    parts = [
        '<table class="ocr-table" style="width:100%;border-collapse:collapse" '
        f'data-grid-confidence="{table.grid_confidence:.3f}">'
    ]
    if widths:
        total_width = max(1, sum(widths))
        parts.append("<colgroup>")
        for width in widths[:table.cols_count]:
            parts.append(f'<col style="width:{(width / total_width) * 100.0:.4f}%">')
        parts.append("</colgroup>")
    parts.append("<tbody>")
    for row_index in range(table.rows_count):
        row_style = (
            f' style="height:{max(1, heights[row_index])}px"'
            if row_index < len(heights) else ""
        )
        parts.append(f"<tr{row_style}>")
        tag = "th" if row_index == 0 else "td"
        for column_index in range(table.cols_count):
            if (row_index, column_index) in covered:
                continue
            cell = anchors.get((row_index, column_index))
            if cell is None:
                parts.append(f"<{tag}>&nbsp;</{tag}>")
                continue
            attrs = []
            if cell.rowspan > 1:
                attrs.append(f'rowspan="{cell.rowspan}"')
            if cell.colspan > 1:
                attrs.append(f'colspan="{cell.colspan}"')
            attrs.append(f'style="{html.escape(_html_cell_style(cell), quote=True)}"')
            fragments = []
            if cell.text.strip():
                fragments.append(_html_text_with_breaks(cell.text.strip()))
            for figure in getattr(cell, "figures", ()):
                fragments.append(
                    f'<img class="ocr-cell-figure" src="{figure.base64_src}" alt="표 셀 추출 이미지">'
                )
            value = "".join(fragments) if fragments else "&nbsp;"
            parts.append(f"<{tag} {' '.join(attrs)}>{value}</{tag}>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


# OCR 인식 결과 to HTML 웹 문서 데이터를 대상 포맷으로 변환함
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
        ".ocr-quality { margin: 0 0 16px; padding: 8px 10px; border-left: 3px solid #d97706; background: #fffbeb; color: #78350f; font-size: 12px; }",
        "h2 { font-size: 19px; font-weight: 800; color: #0f172a; margin: 16px 0 8px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }",
        "p { font-size: 14px; margin: 6px 0; }",
        "table.ocr-table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 13px; }",
        "table.ocr-table th, table.ocr-table td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; vertical-align: middle; }",
        "table.ocr-table tr:first-child td, table.ocr-table th { background: #f8fafc; font-weight: 700; color: #334155; }",
        "table.ocr-table tr:hover { background: #f1f5f9; }",
        ".ocr-cell-figure { display: block; max-width: 100%; height: auto; margin-top: 6px; border: 0; border-radius: 4px; }",
        ".ocr-figure-container { margin: 20px 0; text-align: center; }",
        ".ocr-figure-container img { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for page in pages:
        html_parts.append("<div class=\"page-container\">")
        html_parts.append(f"<span class=\"page-badge\">PAGE {page.page_num} (OCR & FIGURE RECONSTRUCTED)</span>")
        if getattr(page, "requires_review", False):
            message = " ".join(getattr(page, "warnings", ())) or "OCR 결과를 검토해 주세요."
            html_parts.append(
                f'<div class="ocr-quality">신뢰도 {getattr(page, "mean_confidence", 0.0):.1%} · '
                f'{html.escape(message)}</div>'
            )

        elements: List[Tuple[int, str, Any]] = []
        for tb in page.text_blocks:
            elements.append((tb.bbox[1], "text", tb))
        for table in page.tables:
            elements.append((table.bbox[1], "table", table))
        cell_figure_ids = {
            id(figure)
            for table in page.tables
            for cell in table.cells
            for figure in getattr(cell, "figures", ())
        }
        for fig in page.figures:
            if id(fig) not in cell_figure_ids:
                elements.append((fig.bbox[1], "figure", fig))

        elements.sort(key=lambda x: x[0])

        for _, elem_type, elem in elements:
            if elem_type == "text":
                tb: OCRTextBlock = elem
                if tb.is_heading:
                    html_parts.append(f"<h2>{_html_text_with_breaks(tb.text)}</h2>")
                else:
                    html_parts.append(f"<p>{_html_text_with_breaks(tb.text)}</p>")
            elif elem_type == "table":
                t: OCRTable = elem
                if not t.cells or not any(
                    cell.text.strip() or getattr(cell, "figures", ())
                    for cell in t.cells
                ):
                    continue
                html_parts.append(_render_table_html_fragment(t))
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                html_parts.append(f'<div class=\"ocr-figure-container\"><img src=\"{fig.base64_src}\" alt=\"문서 추출 이미지\" /></div>')

        html_parts.append("</div>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


# OCR 인식 결과 to 마크다운 데이터를 대상 포맷으로 변환함
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
                if _table_is_complex(t):
                    # Raw HTML is valid Markdown and is the canonical form for
                    # geometry that pipe tables cannot represent losslessly.
                    md_lines.append(_render_table_html_fragment(t))
                    md_lines.append("")
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


# OCR 인식 결과 to 한글 표준(HWPX) 데이터를 대상 포맷으로 변환함
def convert_ocr_result_to_hwpx(pages: List[OCRPageResult], output_path: Path) -> None:
    """OCR 복원 결과를 한글 HWPX 문서 패키지, 표 객체 및 이미지로 변환함."""
    from hwpx.document import HwpxDocument

    doc = HwpxDocument.new()

    # 셀 텍스트 속성 값을 설정 및 갱신함
    def set_cell_text(target: Any, value: str) -> None:
        target.set_text(value)
        if "\n" not in value:
            return
        from lxml import etree
        text_nodes = [node for node in target.element.iter() if etree.QName(node).localname == "t"]
        if not text_nodes:
            return
        text_node = text_nodes[0]
        for child in list(text_node):
            text_node.remove(child)
        lines = value.split("\n")
        text_node.text = lines[0]
        namespace = etree.QName(text_node).namespace
        for line in lines[1:]:
            line_break = etree.SubElement(text_node, f"{{{namespace}}}lineBreak")
            line_break.tail = line

    # 셀 정렬 상태 속성 값을 설정 및 갱신함
    def set_cell_alignment(target: Any, alignment: str) -> None:
        normalized = alignment if alignment in {"left", "center", "right"} else "left"
        para_pr_id = doc._root.headers[0].ensure_paragraph_alignment(normalized)
        for paragraph in target.paragraphs:
            paragraph.element.set("paraPrIDRef", para_pr_id)

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
                if not t.cells:
                    continue
                try:
                    tbl = doc.add_table(t.rows_count, t.cols_count)
                    tbl.set_column_widths(_table_column_widths(t))
                    for cell in sorted(t.cells, key=lambda item: (item.row, item.col)):
                        target = tbl.cell(cell.row, cell.col)
                        if cell.rowspan > 1 or cell.colspan > 1:
                            target = tbl.merge_cells(
                                cell.row,
                                cell.col,
                                cell.row + cell.rowspan - 1,
                                cell.col + cell.colspan - 1,
                            )
                        set_cell_text(target, cell.text)
                        set_cell_alignment(target, cell.text_align)
                        active_borders = [
                            side for side, style in cell.border_styles.items()
                            if style != "none"
                        ]
                        if active_borders or cell.bg_color_hex.lower() != "#ffffff":
                            dominant_style = next(
                                (style for style in ("double", "dashed", "solid")
                                 if style in cell.border_styles.values()),
                                "solid",
                            )
                            border_type = {
                                "solid": "SOLID",
                                "dashed": "DASH",
                                "double": "DOUBLE_SLIM",
                            }[dominant_style]
                            border_fill_id = doc.styles.ensure_border_fill(
                                active_borders=active_borders or None,
                                border_type=border_type,
                                fill_color=(cell.bg_color_hex if cell.bg_color_hex.lower() != "#ffffff" else None),
                            )
                            tbl.set_cell_border_fill(cell.row, cell.col, border_fill_id)
                except Exception:
                    for r in t.to_grid():
                        doc.add_paragraph(" | ".join(r))
            elif elem_type == "figure":
                fig: OCRFigureBlock = elem
                doc.add_paragraph(f"[그림: {fig.width}x{fig.height}px]")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(output_path)


# OCR 인식 결과 to 엑셀(XLSX) 데이터를 대상 포맷으로 변환함
def convert_ocr_result_to_xlsx(pages: List[OCRPageResult], output_path: Path) -> None:
    """Export OCR tables with spans, fills, borders and alignment to XLSX."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, PatternFill, Side
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    workbook.remove(workbook.active)
    border_style = {"solid": "thin", "dashed": "dashed", "double": "double", "none": None}
    sheet_index = 0
    for page in pages:
        for table_index, table in enumerate(page.tables, start=1):
            sheet_index += 1
            sheet = workbook.create_sheet(f"P{page.page_num}_T{table_index}"[:31])
            widths = _table_column_widths(table)
            for index, width in enumerate(widths, start=1):
                sheet.column_dimensions[get_column_letter(index)].width = max(4.0, width / 7.0)

            for cell in sorted(table.cells, key=lambda item: (item.row, item.col)):
                row, col = cell.row + 1, cell.col + 1
                target = sheet.cell(row=row, column=col, value=cell.text)
                target.alignment = Alignment(horizontal=cell.text_align, vertical="center", wrap_text=True)
                color = cell.bg_color_hex.lstrip("#").upper()
                if color != "FFFFFF":
                    target.fill = PatternFill(fill_type="solid", fgColor=color)
                sides = {
                    side: Side(style=border_style.get(cell.border_styles.get(side)))
                    for side in ("left", "right", "top", "bottom")
                }
                target.border = Border(**sides)
                if cell.rowspan > 1 or cell.colspan > 1:
                    sheet.merge_cells(
                        start_row=row,
                        start_column=col,
                        end_row=row + cell.rowspan - 1,
                        end_column=col + cell.colspan - 1,
                    )

    if sheet_index == 0:
        workbook.create_sheet("OCR")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


# OCR 인식 결과 to 워드(DOCX) 데이터를 대상 포맷으로 변환함
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
