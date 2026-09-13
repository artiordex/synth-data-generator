# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: manifest.py
# 경로: packages/ocr/ocr/dataset/manifest.py
# 목적: OCR 벤치마크용 JSONL 매니페스트 레코드 생성 및 저장을 담당함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Portable JSONL manifest for local OCR training and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import OCRSample
from .rules import annotations_to_text, order_annotations


# sample to 매니페스트 record 작업을 수행함
def sample_to_manifest_record(sample: OCRSample) -> dict[str, object]:
    """Convert a sample to a deterministic, source-preserving record."""

    ordered = order_annotations(sample.annotations)
    return {
        "sample_id": sample.sample_id,
        "image": str(sample.image_path) if sample.image_path else None,
        "image_filename": sample.image_filename,
        "width": sample.image_width,
        "height": sample.image_height,
        "text": annotations_to_text(ordered),
        "annotations": [
            {
                "sequence": annotation.sequence,
                "id": annotation.annotation_id,
                "text": annotation.text,
                "bbox": [annotation.bbox.x, annotation.bbox.y, annotation.bbox.width, annotation.bbox.height],
                "type": annotation.annotation_type,
                "text_type": annotation.text_type,
            }
            for annotation in ordered
        ],
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity.value,
                "message": issue.message,
                "annotation_index": issue.annotation_index,
            }
            for issue in sample.issues
        ],
    }


# jsonl 매니페스트 데이터를 파일에 기록함
def write_jsonl_manifest(samples: Iterable[OCRSample], output: str | Path, *, include_invalid: bool = True) -> int:
    """Write one normalized JSON record per sample and return its count."""

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for sample in samples:
            if not include_invalid and sample.has_errors:
                continue
            stream.write(json.dumps(sample_to_manifest_record(sample), ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count
