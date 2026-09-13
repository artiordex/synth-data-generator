# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_sample_dataset.py
# 경로: tests/ocr/test_sample_dataset.py
# 목적: OCR 샘플 데이터셋 규격 및 파싱 유효성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Regression tests for the box-level OCR sample standard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ocr.dataset import SampleDatasetError, load_sample_dataset, sample_to_manifest_record
from ocr.dataset.rules import annotations_to_text, order_annotations
from ocr.pipeline.models import BoundingBox


# sample 데이터를 파일에 기록함
def _write_sample(root: Path, *, duplicate_id: bool = True, missing_image: bool = False) -> None:
    label_dir = root / "라벨링데이터" / "인.허가"
    image_dir = root / "원천데이터" / "인.허가"
    label_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    filename = "sample.jpg"
    if not missing_image:
        (image_dir / filename).write_bytes(b"not decoded in audit mode")
    annotations = [
        {"id": 1, "annotation.type": "rectangle", "annotation.text": "금액 1,000원", "annotation.ttype": "textType1", "annotation.bbox": [10, 20, 100, 20]},
        {"id": 1 if duplicate_id else 2, "annotation.type": "rectangle", "annotation.text": "2026-09-11", "annotation.ttype": "textType1", "annotation.bbox": [10, 60, 100, 20]},
    ]
    payload = {
        "images": [{"image.width": 200, "image.height": 100, "image.file.name": filename}],
        "annotations": annotations,
    }
    (label_dir / "sample.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# loader pairs 이미지 목록 and retains duplicate ids as warning 기능의 정상 동작 및 제약조건을 테스트함
def test_loader_pairs_images_and_retains_duplicate_ids_as_warning(tmp_path):
    _write_sample(tmp_path)

    samples, audit = load_sample_dataset(tmp_path)

    assert audit.sample_count == 1
    assert audit.paired_image_count == 1
    assert audit.passed
    assert any(issue.code == "DUPLICATE_ANNOTATION_ID" for issue in audit.issues)
    assert samples[0].ground_truth_text == "금액 1,000원\n2026-09-11"


# missing 이미지 is a strict error but 감사 로그 remains actionable 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_image_is_a_strict_error_but_audit_remains_actionable(tmp_path):
    _write_sample(tmp_path, missing_image=True)

    _, audit = load_sample_dataset(tmp_path)

    assert not audit.passed
    assert any(issue.code == "MISSING_SOURCE_IMAGE" for issue in audit.issues)
    with pytest.raises(SampleDatasetError):
        load_sample_dataset(tmp_path, strict=True)


# ordering does not invent spaces or change format tokens 기능의 정상 동작 및 제약조건을 테스트함
def test_ordering_does_not_invent_spaces_or_change_format_tokens():
    from ocr.dataset.models import SampleAnnotation

    annotations = (
        SampleAnnotation(0, 0, "A-001/02", BoundingBox(50, 10, 40, 10), "rectangle", "textType1"),
        SampleAnnotation(1, 1, "환경을", BoundingBox(10, 10, 35, 10), "rectangle", "textType1"),
        SampleAnnotation(2, 2, "제공한다", BoundingBox(10, 30, 60, 10), "rectangle", "textType1"),
    )

    assert annotations_to_text(annotations) == "환경을A-001/02\n제공한다"
    assert tuple(item.sequence for item in order_annotations(annotations)) == (1, 0, 2)


# 매니페스트 is source preserving and contains training boxes 기능의 정상 동작 및 제약조건을 테스트함
def test_manifest_is_source_preserving_and_contains_training_boxes(tmp_path):
    _write_sample(tmp_path, duplicate_id=False)
    samples, _ = load_sample_dataset(tmp_path)

    record = sample_to_manifest_record(samples[0])

    assert record["text"] == "금액 1,000원\n2026-09-11"
    assert record["annotations"][0]["bbox"] == [10, 20, 100, 20]
    assert record["annotations"][0]["text"] == "금액 1,000원"
