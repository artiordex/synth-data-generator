# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: image_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/image_parser.py
# 목적: 단일/다중 이미지 파일을 문서 IR 트리로 변환 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Image parser that turns scanned images into text-first DocumentIR."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence, UnidentifiedImageError

from ..core.ir import (
    BorderIR,
    ConversionWarning,
    DocumentIR,
    ImageIR,
    ParagraphIR,
    SectionIR,
    TableCellIR,
    TableIR,
    TextRunIR,
)
from ..core.enums import BorderStyle
from ..core.source_ref import SourceRef
from ..exceptions import DocumentConversionError


# 이미지 bytes 작업을 수행함
def _image_bytes(image: Image.Image, fmt: str) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# bgr array 형식으로 변환하여 반환함
def _to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb = image.convert("RGB")
    array = np.asarray(rgb)
    return array[:, :, ::-1].copy()


# 문단 작업을 수행함
def _paragraph(text: str, *, heading: bool = False, ref: SourceRef | None = None) -> ParagraphIR:
    return ParagraphIR([TextRunIR(text, source_ref=ref)], heading_level=1 if heading else None, source_ref=ref)


# 셀 텍스트 작업을 수행함
def _cell_text(cell) -> str:
    text = getattr(cell, "text", "")
    return str(text).strip()


# 테두리 map 작업을 수행함
def _border_map(styles: dict[str, str]) -> dict[str, BorderIR]:
    if not styles:
        return {}
    borders: dict[str, BorderIR] = {}
    for side in ("top", "right", "bottom", "left"):
        if side in styles:
            borders[side] = BorderIR(BorderStyle.SOLID, 0.5, "000000")
    return borders


# 표(테이블) ir 작업을 수행함
def _table_ir(ocr_table, page_no: int) -> TableIR:
    rows_count = max(0, int(getattr(ocr_table, "rows_count", 0)))
    cols_count = max(0, int(getattr(ocr_table, "cols_count", 0)))
    rows: list[list[TableCellIR]] = [[] for _ in range(rows_count)]
    for cell in getattr(ocr_table, "cells", []):
        text = _cell_text(cell)
        ref = SourceRef(
            "image",
            page_no=page_no,
            table_id=f"page-{page_no}",
            row_index=int(getattr(cell, "row", 0)),
            col_index=int(getattr(cell, "col", 0)),
        )
        bg = str(getattr(cell, "bg_color_hex", "") or "").lstrip("#") or None
        table_cell = TableCellIR(
            row_index=int(getattr(cell, "row", 0)),
            col_index=int(getattr(cell, "col", 0)),
            row_span=max(1, int(getattr(cell, "rowspan", 1))),
            col_span=max(1, int(getattr(cell, "colspan", 1))),
            bg_color_hex=bg,
            borders=_border_map(getattr(cell, "border_styles", {}) or {}),
            content=[_paragraph(text, ref=ref)] if text else [],
            source_ref=ref,
            cell_confidence=getattr(cell, "confidence", None),
        )
        if 0 <= table_cell.row_index < rows_count:
            rows[table_cell.row_index].append(table_cell)
    for row in rows:
        row.sort(key=lambda item: item.col_index)
    x0, _, x1, _ = getattr(ocr_table, "bbox", (0, 0, cols_count * 80, rows_count * 24))
    width_pt = max(0.0, (float(x1) - float(x0)) * 0.75)
    return TableIR(
        rows=rows,
        column_widths_pt=[width_pt / cols_count] * cols_count if cols_count else [],
        total_width_pt=width_pt,
        source_ref=SourceRef("image", page_no=page_no, table_id=f"page-{page_no}"),
        table_confidence=getattr(ocr_table, "table_confidence", None),
    )


# figure ir 작업을 수행함
def _figure_ir(figure, page_no: int) -> ImageIR:
    fmt = str(getattr(figure, "format", "png") or "png").lower()
    width = int(getattr(figure, "width", 0) or 0)
    height = int(getattr(figure, "height", 0) or 0)
    return ImageIR(
        bytes(getattr(figure, "image_bytes")),
        "image/jpeg" if fmt in {"jpg", "jpeg"} else f"image/{fmt}",
        fmt,
        max(1, width) * 0.75,
        max(1, height) * 0.75,
        original_width_px=max(1, width),
        original_height_px=max(1, height),
        source_ref=SourceRef("image", page_no=page_no, object_id="figure"),
    )


class ImageParser:
    """Parse PNG/JPEG/TIFF/BMP/WEBP/HEIC images through local OCR into IR."""

    # parse 작업을 수행함
    def parse(self, path: Path) -> DocumentIR:
        source = Path(path)
        try:
            image = Image.open(source)
        except (OSError, UnidentifiedImageError) as exc:
            raise DocumentConversionError(f"이미지 파일을 열 수 없습니다: {source.name}") from exc

        document = DocumentIR(source_format="image", source_path=str(source))
        for page_no, frame in enumerate(ImageSequence.Iterator(image), start=1):
            page = frame.convert("RGB")
            width, height = page.size
            section = SectionIR(
                page_width_pt=width * 0.75,
                page_height_pt=height * 0.75,
                source_ref=SourceRef("image", page_no=page_no, section_no=page_no),
            )
            try:
                from synthetic_engine.exporters.ocr_table_reconstructor import process_scanned_page

                ocr = process_scanned_page(_to_bgr_array(page), page_num=page_no)
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                ocr = None
                document.metadata.custom[f"ocr_status_p{page_no}"] = "failed"
                document.metadata.custom[f"ocr_error_p{page_no}"] = str(exc)[:500]
                document.warnings.append(ConversionWarning(
                    "IMAGE_OCR_FAILED",
                    f"이미지 OCR 처리에 실패했습니다: {exc}",
                    source_ref=SourceRef("image", page_no=page_no),
                    feature="image_ocr",
                ))

            if ocr is not None:
                for block in getattr(ocr, "text_blocks", []):
                    text = str(getattr(block, "text", "") or "").strip()
                    if text:
                        section.elements.append(_paragraph(
                            text,
                            heading=bool(getattr(block, "is_heading", False)),
                            ref=SourceRef("image", page_no=page_no),
                        ))
                for table in getattr(ocr, "tables", []):
                    section.elements.append(_table_ir(table, page_no))
                for figure in getattr(ocr, "figures", []):
                    try:
                        section.elements.append(_figure_ir(figure, page_no))
                    except (AttributeError, OSError, TypeError, ValueError) as exc:
                        document.warnings.append(ConversionWarning(
                            "IMAGE_FIGURE_PRESERVATION_FAILED",
                            f"{page_no}페이지 이미지 요소를 보존하지 못했습니다: {exc}",
                            source_ref=SourceRef("image", page_no=page_no),
                            feature="embedded_image",
                        ))
                        continue
                for message in getattr(ocr, "warnings", []) or []:
                    document.warnings.append(ConversionWarning(
                        "IMAGE_OCR_REVIEW",
                        str(message),
                        source_ref=SourceRef("image", page_no=page_no),
                        feature="image_ocr",
                    ))

            if not section.elements:
                fmt = (page.format or image.format or "PNG").upper()
                payload = _image_bytes(page, fmt)
                section.elements.append(ImageIR(
                    payload,
                    "image/png",
                    "png",
                    width * 0.75,
                    height * 0.75,
                    original_width_px=width,
                    original_height_px=height,
                    caption=_paragraph("이미지에서 텍스트를 추출하지 못했습니다.", ref=SourceRef("image", page_no=page_no)),
                    source_ref=SourceRef("image", page_no=page_no, object_id="source-image"),
                ))
            if ocr is not None and hasattr(ocr, "mean_confidence"):
                mean_confidence = float(ocr.mean_confidence)
                document.metadata.custom[f"ocr_mean_confidence_p{page_no}"] = str(round(mean_confidence, 4))
                document.metadata.custom[f"ocr_status_p{page_no}"] = (
                    "review_required"
                    if bool(getattr(ocr, "requires_review", False)) or mean_confidence < 0.85
                    else "success"
                )
            document.sections.append(section)

        if not document.sections:
            raise DocumentConversionError(f"이미지 페이지를 찾을 수 없습니다: {source.name}")
        page_confs = [
            float(v) for k, v in document.metadata.custom.items()
            if k.startswith("ocr_mean_confidence_p")
        ]
        if page_confs:
            document.metadata.custom["ocr_mean_confidence"] = str(round(sum(page_confs) / len(page_confs), 4))
        document.intern_resources()
        return document
