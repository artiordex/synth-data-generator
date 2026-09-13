# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: rendering.py
# 경로: packages/ocr/ocr/pdf/rendering.py
# 목적: PDF 페이지를 고해상도 이미지로 래스터화 렌더링을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PyMuPDF page rendering for OCR-required PDF pages."""

from __future__ import annotations

from dataclasses import replace
import cv2
import numpy as np
import pymupdf

from ..pipeline.models import PreprocessedImage, PreprocessingConfig, PreprocessingProfile
from ..preprocessing.transforms import TransformMetadata


DEFAULT_MAX_PIXELS = 25_000_000
MAX_DPI = 600


# 페이지 for OCR 인식 데이터를 타깃 포맷으로 렌더링함
def render_page_for_ocr(
    page, *, dpi: int = 300, config: PreprocessingConfig | None = None,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> PreprocessedImage:
    """Render one PDF page to a preprocessed image object for OCR backends."""

    if type(dpi) is not int or not 1 <= dpi <= MAX_DPI:
        raise ValueError(f"dpi must be an integer between 1 and {MAX_DPI}")
    if type(max_pixels) is not int or max_pixels <= 0:
        raise ValueError("max_pixels must be a positive integer")
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    bounds = (page.rect * matrix).irect
    if bounds.width <= 0 or bounds.height <= 0 or bounds.width * bounds.height > max_pixels:
        raise ValueError("PDF render exceeds pixel budget or has invalid dimensions")
    pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY, alpha=False)
    if pixmap.width * pixmap.height > max_pixels:
        raise ValueError("PDF render exceeds pixel budget")
    data = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    if pixmap.n == 4:
        data = cv2.cvtColor(data, cv2.COLOR_RGBA2GRAY)
    elif pixmap.n == 3:
        data = cv2.cvtColor(data, cv2.COLOR_RGB2GRAY)
    else:
        data = data[:, :, 0]
    image = cv2.threshold(data, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return PreprocessedImage(
        image=image,
        config=replace(config, target_dpi=dpi) if config else PreprocessingConfig(profile=PreprocessingProfile.STANDARD, target_dpi=dpi, psm=3),
        width_px=int(image.shape[1]),
        height_px=int(image.shape[0]),
        applied_steps=("pdf_render", f"dpi:{dpi}", "grayscale", "threshold:otsu"),
        original_width_px=int(image.shape[1]),
        original_height_px=int(image.shape[0]),
        ocr_width_px=int(image.shape[1]),
        ocr_height_px=int(image.shape[0]),
        transform_metadata=TransformMetadata.identity((int(image.shape[1]), int(image.shape[0]))),
    )
