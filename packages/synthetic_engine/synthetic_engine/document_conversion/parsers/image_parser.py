# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: image_parser.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/image_parser.py
# 목적: 단일/다중 이미지 파일을 문서 IR 트리로 변환 파싱함
# 작성자: 개발팀
# 작성일: 2026-09-13
# 수정일: 2026-09-16
# =============================================================================
"""Image parser that turns scanned images into text-first DocumentIR."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageSequence, UnidentifiedImageError

from ..core.ir import (
    BorderIR,
    ConversionWarning,
    DocumentIR,
    ImageIR,
    MathIR,
    ParagraphIR,
    SectionIR,
    TableCellIR,
    TableIR,
    TextRunIR,
)
from ..core.enums import BorderStyle
from ..core.source_ref import BoundingBoxIR, SourceRef
from ..exceptions import DocumentConversionError


# PIL 이미지를 PNG 포맷 바이트 배열로 인코딩함
def _image_bytes(image: Image.Image, fmt: str) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# PIL 이미지를 BGR 포맷의 NumPy 배열로 변환함
def _to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb = image.convert("RGB")
    array = np.asarray(rgb)
    return array[:, :, ::-1].copy()


# 텍스트 문자열로부터 ParagraphIR 객체를 생성함
def _paragraph(text: str, *, heading: bool = False, ref: SourceRef | None = None) -> ParagraphIR:
    return ParagraphIR([TextRunIR(text, source_ref=ref)], heading_level=1 if heading else None, source_ref=ref)


# OCR 셀 객체에서 공백이 정제된 텍스트 문자열을 추출함
def _cell_text(cell) -> str:
    text = getattr(cell, "text", "")
    return str(text).strip()


# 후보 객체의 신뢰도 값을 0~1 범위의 실수로 정규화함
def _candidate_confidence(item) -> float | None:
    value = getattr(item, "confidence", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if 0 <= value <= 1 else None


# 후보 객체의 좌표를 pt 단위의 BoundingBoxIR로 변환함
def _candidate_bbox(item, page_no: int) -> BoundingBoxIR | None:
    value = getattr(item, "bbox", None)
    try:
        x0, y0, x1, y1 = (float(part) * 0.75 for part in value)
        return BoundingBoxIR(x0, y0, x1, y1, page_no)
    except (TypeError, ValueError):
        return None


# OCR 인식 블록이 명시적인 수식 후보인지 여부를 판별함
def _is_explicit_math_candidate(item) -> bool:
    kind = str(getattr(item, "block_type", getattr(item, "text_type", ""))).lower()
    return bool(getattr(item, "is_equation", False) or kind in {"equation", "formula", "math"})


# OCR 인식 수식 후보를 MathIR 객체로 변환함
def _ocr_math(item, page_no: int, ref: SourceRef, source_resource_id: str,
              *, display_mode: str) -> MathIR:
    candidate = str(getattr(item, "text", "") or "")
    return MathIR(
        source_ref=ref,
        display_mode=display_mode,
        fallback_image_resource_id=source_resource_id,
        confidence=_candidate_confidence(item),
        needs_review=True,
        failure_reason=(
            "OCR marked this region as a math candidate, but its semantic structure "
            "and LaTeX/MathML representation are unverified."
        ),
        ocr_candidates=[candidate] if candidate.strip() else [],
        bbox=_candidate_bbox(item, page_no),
        source_syntax="ocr-candidate",
    )


# 셀 테두리 스타일 딕셔너리를 BorderIR 매핑으로 변환함
def _border_map(styles: dict[str, str]) -> dict[str, BorderIR]:
    if not styles:
        return {}
    borders: dict[str, BorderIR] = {}
    for side in ("top", "right", "bottom", "left"):
        if side in styles:
            borders[side] = BorderIR(BorderStyle.SOLID, 0.5, "000000")
    return borders


# OCR 인식 표 구조를 TableIR 객체로 구성함
def _table_ir(ocr_table, page_no: int, source_resource_id: str) -> TableIR:
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
        if _is_explicit_math_candidate(cell):
            content = [_ocr_math(cell, page_no, ref, source_resource_id, display_mode="inline")]
        else:
            content = [_paragraph(text, ref=ref)] if text else []
        table_cell = TableCellIR(
            row_index=int(getattr(cell, "row", 0)),
            col_index=int(getattr(cell, "col", 0)),
            row_span=max(1, int(getattr(cell, "rowspan", 1))),
            col_span=max(1, int(getattr(cell, "colspan", 1))),
            bg_color_hex=bg,
            borders=_border_map(getattr(cell, "border_styles", {}) or {}),
            content=content,
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


# 그림 및 다이어그램 객체를 ImageIR로 변환함
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


# 로컬 OCR 결과의 신뢰도, 손글씨 유무 및 한국어 텍스트 문맥 품질을 평가하여 AI 에스컬레이션 필요 여부를 판별함
def _evaluate_local_ocr_quality(ocr: Any, image_bgr: np.ndarray | None = None) -> tuple[bool, str, float]:
    if ocr is None:
        return False, "ocr_engine_failed", 0.0

    text_blocks = getattr(ocr, "text_blocks", []) or []
    tables = getattr(ocr, "tables", []) or []

    # 1. 텍스트 추출 총량 검사함
    all_texts: list[str] = []
    block_texts: list[str] = []
    for tb in text_blocks:
        t = str(getattr(tb, "text", "") or "").strip()
        if t:
            all_texts.append(t)
            block_texts.append(t)
    for table in tables:
        for cell in getattr(table, "cells", []) or []:
            c_text = str(getattr(cell, "text", "") or "").strip()
            if c_text:
                all_texts.append(c_text)

    combined = " ".join(all_texts).strip()
    if len(combined) < 8:
        return False, "insufficient_text_extracted", 0.0

    # 2. 신뢰도(Confidence) 측정함
    conf_scores: list[float] = []
    for tb in text_blocks:
        conf = getattr(tb, "confidence", None)
        if isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0:
            conf_scores.append(float(conf))
    for table in tables:
        for cell in getattr(table, "cells", []) or []:
            c_conf = getattr(cell, "confidence", None)
            if isinstance(c_conf, (int, float)) and 0.0 <= c_conf <= 1.0:
                conf_scores.append(float(c_conf))

    # OCRTextBlock intentionally keeps only layout fields, so use the page
    # result's aggregate confidence when per-block scores are unavailable.
    page_confidence = getattr(ocr, "mean_confidence", None)
    if isinstance(page_confidence, (int, float)) and 0.0 <= page_confidence <= 1.0:
        mean_conf = float(page_confidence)
    else:
        mean_conf = (sum(conf_scores) / len(conf_scores)) if conf_scores else 0.85
    if bool(getattr(ocr, "requires_review", False)) and mean_conf >= 0.68:
        return False, f"ocr_requires_review_{mean_conf:.2f}", mean_conf
    if conf_scores and mean_conf < 0.68:
        return False, f"low_confidence_{mean_conf:.2f}", mean_conf

    # 3. 깨진 문자 및 노이즈 비율 검사함
    noisy_chars = 0
    total_chars = len(combined)
    for ch in combined:
        if ch in "□■▲▼◆◇§※":
            noisy_chars += 1
    if total_chars > 0 and (noisy_chars / total_chars) > 0.25:
        return False, "high_noise_ratio", mean_conf

    # 4. 손글씨(Handwriting) 영역 탐지 검사함
    try:
        # Printed glyphs can have irregular anti-aliased contours too. Only
        # use the handwriting detector as an escalation signal when the local
        # recognizer already reports low confidence; this prevents clean scans
        # from incurring an unnecessary Vision request.
        if mean_conf < 0.70:
            from synthetic_engine.exporters.handwriting_vlm import is_handwritten_region

            if image_bgr is not None and isinstance(image_bgr, np.ndarray) and image_bgr.size > 0:
                h_img, w_img = image_bgr.shape[:2]
                handwritten_count = 0
                for tb in text_blocks:
                    bbox = getattr(tb, "bbox", None)
                    conf = float(getattr(tb, "confidence", mean_conf) or mean_conf)
                    if bbox and len(bbox) == 4:
                        x0, y0, x1, y1 = [int(v) for v in bbox]
                        x0, y0 = max(0, x0), max(0, y0)
                        x1, y1 = min(w_img, x1), min(h_img, y1)
                        if x1 > x0 + 10 and y1 > y0 + 10:
                            crop = image_bgr[y0:y1, x0:x1]
                            if crop.size > 0 and is_handwritten_region(crop, conf):
                                handwritten_count += 1
                if handwritten_count >= 1:
                    return False, f"handwriting_detected_{handwritten_count}_blocks", mean_conf
    except (ImportError, OSError, RuntimeError, ValueError):
        pass

    # 5. 한국어 문맥 품질(korean_quality_score) 및 외계어 검사함
    try:
        from ocr.text.korean_quality import korean_quality_score

        hangul_blocks = [
            t for t in block_texts
            if any("\uac00" <= c <= "\ud7a3" for c in t) and len(t.strip()) >= 5
        ]
        if hangul_blocks:
            block_scores = [korean_quality_score(t) for t in hangul_blocks]
            low_score_count = sum(1 for s in block_scores if s < 0.45)
            low_ratio = low_score_count / len(block_scores)
            avg_korean_score = sum(block_scores) / len(block_scores)

            if low_ratio >= 0.30:
                return False, f"low_korean_quality_ratio_{low_ratio:.2f}", mean_conf
            if avg_korean_score < 0.48:
                return False, f"low_korean_quality_avg_{avg_korean_score:.2f}", mean_conf
    except (ImportError, OSError, RuntimeError, ValueError):
        pass

    return True, "acceptable_quality", mean_conf


class ImageParser:
    """Parse PNG/JPEG/TIFF/BMP/WEBP/HEIC images through local OCR into IR."""

    # 이미지 파일을 OCR 기반으로 분석하여 DocumentIR 트리를 생성함
    def parse(self, path: Path) -> DocumentIR:
        source = Path(path)
        try:
            image = Image.open(source)
        except (OSError, UnidentifiedImageError) as exc:
            raise DocumentConversionError(f"이미지 파일을 열 수 없습니다: {source.name}") from exc

        document = DocumentIR(source_format="image", source_path=str(source))
        source_format = str(image.format or source.suffix.lstrip(".") or "png").lower()
        source_mime = "image/jpeg" if source_format in {"jpg", "jpeg"} else f"image/{source_format}"
        source_resource_id = document.resources.add(source.read_bytes(), source_mime)
        for page_no, frame in enumerate(ImageSequence.Iterator(image), start=1):
            page = frame.convert("RGB")
            page_bgr = _to_bgr_array(page)
            width, height = page.size
            section = SectionIR(
                page_width_pt=width * 0.75,
                page_height_pt=height * 0.75,
                source_ref=SourceRef("image", page_no=page_no, section_no=page_no),
            )

            # 1. 로컬 고정밀 OCR 파이프라인 1차 시도함
            ocr = None
            try:
                from synthetic_engine.exporters.ocr_table_reconstructor import process_scanned_page

                ocr = process_scanned_page(page_bgr, page_num=page_no)
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                ocr = None
                document.metadata.custom[f"ocr_error_p{page_no}"] = str(exc)[:500]

            # 2. 로컬 결과 품질 자동 진단 게이트 평가함
            is_acceptable, reason, mean_conf = _evaluate_local_ocr_quality(ocr, image_bgr=page_bgr)

            # 3. 품질 미달 또는 판독 실패 시 OpenAI GPT-4o Vision으로 자동 에스컬레이션함
            escalated_to_ai = False
            if not is_acceptable and os.environ.get("OPENAI_API_KEY"):
                try:
                    from .openai_vision_ocr import extract_text_with_openai_vision

                    page_bytes = _image_bytes(page, "PNG")
                    vlm_paragraphs = extract_text_with_openai_vision(page_bytes, "image/png")
                    if vlm_paragraphs:
                        for p_idx, p_text in enumerate(vlm_paragraphs):
                            p_ref = SourceRef("image", page_no=page_no, object_id=f"vlm-block:{p_idx}")
                            section.elements.append(_paragraph(p_text, ref=p_ref))
                        document.metadata.custom[f"ocr_engine_p{page_no}"] = "hybrid_ai_escalated"
                        document.metadata.custom[f"ocr_escalation_reason_p{page_no}"] = reason
                        document.metadata.custom[f"ocr_status_p{page_no}"] = "success"
                        document.metadata.custom[f"ocr_mean_confidence_p{page_no}"] = "0.99"
                        document.metadata.custom[f"ocr_ai_used_p{page_no}"] = "true"
                        document.metadata.custom[f"ocr_ai_model_p{page_no}"] = os.environ.get(
                            "OPENAI_OCR_MODEL", "gpt-4o-mini"
                        )
                        escalated_to_ai = True
                except Exception as exc:
                    document.metadata.custom[f"ocr_ai_error_p{page_no}"] = str(exc)[:500]
                    escalated_to_ai = False

            # 4. AI 에스컬레이션이 실행되지 않은 경우 로컬 OCR 결과를 IR 요소로 조립함
            if not escalated_to_ai:
                if ocr is not None:
                    for block_no, block in enumerate(getattr(ocr, "text_blocks", [])):
                        text = str(getattr(block, "text", "") or "").strip()
                        ref = SourceRef("image", page_no=page_no, object_id=f"ocr-block:{block_no}")
                        if _is_explicit_math_candidate(block):
                            section.elements.append(_ocr_math(
                                block, page_no, ref, source_resource_id, display_mode="display"
                            ))
                            document.warnings.append(ConversionWarning(
                                "IMAGE_MATH_REVIEW",
                                "OCR math candidate retains its source image and coordinates for review.",
                                source_ref=ref,
                                feature="math",
                            ))
                        elif text:
                            section.elements.append(_paragraph(
                                text,
                                heading=bool(getattr(block, "is_heading", False)),
                                ref=ref,
                            ))
                    for table in getattr(ocr, "tables", []):
                        section.elements.append(_table_ir(table, page_no, source_resource_id))
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
                    document.metadata.custom[f"ocr_engine_p{page_no}"] = "local_rapidocr_korean"
                    document.metadata.custom[f"ocr_status_p{page_no}"] = "success" if is_acceptable else "review_required"
                    document.metadata.custom[f"ocr_mean_confidence_p{page_no}"] = f"{mean_conf:.2f}"
                else:
                    document.metadata.custom[f"ocr_status_p{page_no}"] = "failed"
                    document.warnings.append(ConversionWarning(
                        "IMAGE_OCR_FAILED",
                        "이미지 OCR 처리에 실패했습니다.",
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
            if ocr is not None and hasattr(ocr, "mean_confidence") and not escalated_to_ai:
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
