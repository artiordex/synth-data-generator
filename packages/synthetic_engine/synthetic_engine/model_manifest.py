# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: model_manifest.py
# 경로: packages/synthetic_engine/synthetic_engine/model_manifest.py
# 목적: 로컬 AI/ML 모델 가중치 및 체크포인트 매니페스트를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Small local model manifest schema and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


class ModelManifestError(ValueError):
    """Raised when a local model manifest is malformed."""


MODEL_MANIFEST_SCHEMA: dict[str, Any] = {
    "schema_version": 1,
    "required_model_fields": ("path", "license", "commercial_use_reviewed"),
    "optional_model_fields": ("name", "sha256", "source", "notes"),
}


# 모델 매니페스트 유효성 및 제약조건을 검증함
def validate_model_manifest(
    data: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
    require_files: bool = False,
) -> dict[str, Any]:
    """Validate and normalize a local model manifest dictionary.

    The manifest is intentionally small:

    {
      "schema_version": 1,
      "models": [
        {
          "path": "ocr/rapidocr/model.onnx",
          "license": "Apache-2.0",
          "commercial_use_reviewed": true
        }
      ]
    }
    """
    if not isinstance(data, dict):
        raise ModelManifestError("model manifest must be a JSON object")
    if data.get("schema_version") != 1:
        raise ModelManifestError("model manifest schema_version must be 1")
    models = data.get("models")
    if not isinstance(models, list):
        raise ModelManifestError("model manifest models must be a list")

    root = Path(base_dir).resolve() if base_dir is not None else None
    normalized_models = []
    seen_paths: set[str] = set()
    for index, item in enumerate(models):
        normalized = _validate_model_record(
            item,
            index=index,
            base_dir=root,
            require_files=require_files,
        )
        if normalized["path"] in seen_paths:
            raise ModelManifestError(f"model manifest contains duplicate path: {normalized['path']}")
        seen_paths.add(normalized["path"])
        normalized_models.append(normalized)
    return {"schema_version": 1, "models": normalized_models}


# 모델 매니페스트 데이터를 파일 또는 저장소에서 로드함
def load_model_manifest(
    path: str | Path,
    *,
    require_files: bool = False,
) -> dict[str, Any]:
    """Load and validate a JSON model manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    return validate_model_manifest(
        data,
        base_dir=manifest_path.parent,
        require_files=require_files,
    )


# 모델 record 유효성 및 제약조건을 검증함
def _validate_model_record(
    item: Any,
    *,
    index: int,
    base_dir: Path | None,
    require_files: bool,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ModelManifestError(f"model record {index} must be an object")
    path = _validate_relative_path(item.get("path"), index=index)
    license_name = str(item.get("license", "")).strip()
    if not license_name:
        raise ModelManifestError(f"model record {index} requires license")
    commercial_use_reviewed = item.get("commercial_use_reviewed")
    if not isinstance(commercial_use_reviewed, bool):
        raise ModelManifestError(
            f"model record {index} requires boolean commercial_use_reviewed"
        )
    sha256 = item.get("sha256")
    if sha256 is not None:
        sha256 = str(sha256).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ModelManifestError(f"model record {index} sha256 must be 64 hex chars")
    if require_files and base_dir is not None:
        resolved = (base_dir / path).resolve()
        if not resolved.is_relative_to(base_dir) or not resolved.is_file():
            raise ModelManifestError(f"model record {index} file does not exist: {path}")

    normalized: dict[str, Any] = {
        "path": path,
        "license": license_name,
        "commercial_use_reviewed": commercial_use_reviewed,
    }
    for optional in ("name", "sha256", "source", "notes"):
        if optional in item and item[optional] is not None:
            normalized[optional] = sha256 if optional == "sha256" else str(item[optional]).strip()
    return normalized


# relative 파일 경로 유효성 및 제약조건을 검증함
def _validate_relative_path(value: Any, *, index: int) -> str:
    path_text = str(value or "").replace("\\", "/").strip()
    if not path_text:
        raise ModelManifestError(f"model record {index} requires path")
    path = Path(path_text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ModelManifestError(
            f"model record {index} path must be a safe manifest-relative path"
        )
    return path_text


__all__ = [
    "MODEL_MANIFEST_SCHEMA",
    "ModelManifestError",
    "load_model_manifest",
    "validate_model_manifest",
]
