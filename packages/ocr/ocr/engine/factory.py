# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: factory.py
# 경로: packages/ocr/ocr/engine/factory.py
# 목적: 설정 기반 OCR 엔진 인스턴스 생성 및 팩토리 패턴을 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Environment-driven factory for the fully local OCR stack."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .base import OCRBackend
from .easyocr import EasyOCRBackend
from .ensemble import ConfidenceEnsembleBackend
from .rapidocr_korean import RapidOCRKoreanBackend
from .tesseract import TesseractBackend


# local OCR 인식 backend 구조를 생성 및 조립함
def build_local_ocr_backend(workspace_root: str | Path | None = None) -> OCRBackend:
    root = Path(workspace_root or Path.cwd()).resolve()
    model_root = _resolve_model_root(root)
    model_root.mkdir(parents=True, exist_ok=True)

    review_threshold = _float_env("OCR_REVIEW_THRESHOLD", 0.85)
    primary_name = os.getenv("OCR_PRIMARY_BACKEND", "rapidocr_korean").lower()
    primary: OCRBackend
    if primary_name == "easyocr":
        primary = _easyocr_backend(root, model_root)
    else:
        primary = RapidOCRKoreanBackend(
            model_root / "rapidocr", review_threshold=review_threshold
        )

    secondary = None
    secondary_name = os.getenv("OCR_SECONDARY_BACKEND", "easyocr").lower()
    if secondary_name == "easyocr" and primary_name != "easyocr":
        secondary = _easyocr_backend(root, model_root)

    tiebreaker = None
    if (
        os.getenv("OCR_TIEBREAKER_BACKEND", "tesseract").lower() == "tesseract"
        and shutil.which("tesseract")
    ):
        tiebreaker = TesseractBackend(
            language="kor+eng",
            timeout_seconds=_positive_float_env("OCR_TESSERACT_TIMEOUT_SECONDS", 60.0),
        )

    return ConfidenceEnsembleBackend(
        primary,
        secondary,
        tiebreaker,
        review_threshold=review_threshold,
        supplemental_detection=_bool_env("OCR_SUPPLEMENTAL_DETECTION", True),
        uncovered_component_ratio=_float_env(
            "OCR_UNCOVERED_COMPONENT_RATIO", 0.20
        ),
        supplemental_min_confidence=_float_env(
            "OCR_SUPPLEMENTAL_MIN_CONFIDENCE", 0.55
        ),
    )


# resolve 모델 root 작업을 수행함
def _resolve_model_root(root: Path) -> Path:
    configured = Path(os.getenv("OCR_MODEL_DIR", "storage/models/ocr"))
    model_root = configured if configured.is_absolute() else root / configured
    model_root = model_root.resolve()
    if not model_root.is_relative_to(root):
        raise ValueError("OCR_MODEL_DIR must resolve within workspace_root")
    return model_root


# easyocr backend 작업을 수행함
def _easyocr_backend(root: Path, model_root: Path) -> EasyOCRBackend:
    model_dir = model_root / "easyocr" / "models"
    network_dir = model_root / "easyocr" / "user_network"
    model_dir.mkdir(parents=True, exist_ok=True)
    network_dir.mkdir(parents=True, exist_ok=True)
    return EasyOCRBackend(
        root,
        model_dir,
        network_dir,
        download_enabled=_bool_env("OCR_ALLOW_MODEL_DOWNLOAD", False),
    )


# bool env 작업을 수행함
def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# float env 작업을 수행함
def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(0.0, min(1.0, value))


# positive float env 작업을 수행함
def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default
