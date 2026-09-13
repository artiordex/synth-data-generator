# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/preprocessing/__init__.py
# 목적: OCR 인식률 향상을 위한 이미지 전처리 모듈을 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Adaptive OpenCV preprocessing.

The public package keeps imports lazy so schema modules can reference
``preprocessing.transforms`` without pulling OpenCV and image inspection back
into ``pipeline.models`` during package initialization.
"""

from .transforms import CoordinateTransform, TransformMetadata

__all__ = [
    "CoordinateTransform",
    "TransformMetadata",
    "build_attempt_plan",
    "get_profile_config",
    "preprocess_image",
    "resize_horizontal",
]


# getattr 작업을 수행함
def __getattr__(name: str):
    if name in {"preprocess_image", "resize_horizontal"}:
        from .opencv import preprocess_image, resize_horizontal

        return {
            "preprocess_image": preprocess_image,
            "resize_horizontal": resize_horizontal,
        }[name]
    if name in {"build_attempt_plan", "get_profile_config"}:
        from .profiles import build_attempt_plan, get_profile_config

        return {
            "build_attempt_plan": build_attempt_plan,
            "get_profile_config": get_profile_config,
        }[name]
    raise AttributeError(name)
