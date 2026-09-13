# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: loader.py
# 경로: packages/ocr/ocr/dataset/loader.py
# 목적: OCR 정답 샘플 데이터셋 및 어노테이션 로딩을 처리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Safe loader and validator for the New_sample OCR corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..pipeline.models import BoundingBox
from .models import DatasetAudit, DatasetIssue, OCRSample, SampleAnnotation, SampleRuleConfig, SampleSeverity
from .rules import preserve_source_text


class SampleDatasetError(ValueError):
    """Raised when strict loading finds at least one dataset error."""


# sample 데이터셋 데이터를 파일 또는 저장소에서 로드함
def load_sample_dataset(
    root: str | Path,
    *,
    config: SampleRuleConfig | None = None,
    strict: bool = False,
) -> tuple[tuple[OCRSample, ...], DatasetAudit]:
    """Load all JSON labels and pair them with local images.

    No image is opened or executed here.  This keeps audit mode safe for
    untrusted files and lets callers choose a decoder in a later pipeline step.
    """

    cfg = config or SampleRuleConfig()
    dataset_root = Path(root).expanduser().resolve()
    label_root = dataset_root / cfg.label_directory
    image_root = dataset_root / cfg.image_directory
    if not label_root.is_dir():
        raise SampleDatasetError(f"Label directory does not exist: {label_root}")
    image_index = _build_image_index(image_root, cfg)
    samples: list[OCRSample] = []
    all_issues: list[DatasetIssue] = []
    for label_path in sorted(label_root.rglob(f"*{cfg.label_suffix}")):
        sample = _load_one(label_path, label_root, image_root, image_index, cfg)
        samples.append(sample)
        all_issues.extend(sample.issues)
    errors = sum(issue.severity is SampleSeverity.ERROR for issue in all_issues)
    warnings = sum(issue.severity is SampleSeverity.WARNING for issue in all_issues)
    audit = DatasetAudit(
        root=dataset_root,
        sample_count=len(samples),
        valid_sample_count=sum(not sample.has_errors for sample in samples),
        warning_count=warnings,
        error_count=errors,
        annotation_count=sum(len(sample.annotations) for sample in samples),
        paired_image_count=sum(sample.image_path is not None for sample in samples),
        issues=tuple(all_issues),
    )
    if strict and not audit.passed:
        raise SampleDatasetError(
            f"OCR sample validation failed: {audit.error_count} errors, {audit.warning_count} warnings"
        )
    return tuple(samples), audit


# 이미지 index 구조를 생성 및 조립함
def _build_image_index(image_root: Path, config: SampleRuleConfig) -> dict[str, tuple[Path, ...]]:
    if not image_root.is_dir():
        return {}
    index: dict[str, list[Path]] = {}
    suffixes = {suffix.lower() for suffix in config.image_suffixes}
    for path in image_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            index.setdefault(path.name, []).append(path.resolve())
    return {name: tuple(paths) for name, paths in index.items()}


# one 데이터를 파일 또는 저장소에서 로드함
def _load_one(label_path: Path, label_root: Path, image_root: Path, image_index: dict[str, tuple[Path, ...]], config: SampleRuleConfig) -> OCRSample:
    source = str(label_path)
    issues: list[DatasetIssue] = []
    try:
        payload = json.loads(label_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(DatasetIssue("INVALID_LABEL_JSON", SampleSeverity.ERROR, f"라벨 JSON을 읽을 수 없습니다: {exc}", source))
        return OCRSample(label_path.stem, label_path, None, "", 0, 0, {}, (), tuple(issues))
    if not isinstance(payload, dict):
        issues.append(DatasetIssue("INVALID_LABEL_ROOT", SampleSeverity.ERROR, "라벨 최상위 값은 객체여야 합니다.", source))
        payload = {}
    image_record = (payload.get("images") or [{}])[0]
    if not isinstance(image_record, dict):
        image_record = {}
        issues.append(DatasetIssue("INVALID_IMAGE_METADATA", SampleSeverity.ERROR, "images[0]가 객체가 아닙니다.", source))
    filename = preserve_source_text(image_record.get("image.file.name", ""))
    width, height = _positive_int(image_record.get("image.width")), _positive_int(image_record.get("image.height"))
    if width is None or height is None:
        issues.append(DatasetIssue("INVALID_IMAGE_DIMENSIONS", SampleSeverity.ERROR, "이미지 width/height는 양의 정수여야 합니다.", source))
        width, height = width or 0, height or 0
    image_path = _resolve_image(label_path, label_root, image_root, filename, image_index, config, issues)
    raw_annotations = payload.get("annotations", [])
    if not isinstance(raw_annotations, list):
        issues.append(DatasetIssue("INVALID_ANNOTATIONS", SampleSeverity.ERROR, "annotations는 배열이어야 합니다.", source))
        raw_annotations = []
    annotations: list[SampleAnnotation] = []
    seen_ids: set[str] = set()
    for sequence, raw in enumerate(raw_annotations):
        if not isinstance(raw, dict):
            issues.append(DatasetIssue("INVALID_ANNOTATION", SampleSeverity.ERROR, "annotation 항목은 객체여야 합니다.", source, sequence))
            continue
        annotation_id = raw.get("id")
        id_key = repr(annotation_id)
        if id_key in seen_ids:
            severity = SampleSeverity.WARNING if config.allow_duplicate_annotation_ids else SampleSeverity.ERROR
            issues.append(DatasetIssue("DUPLICATE_ANNOTATION_ID", severity, f"annotation id가 파일 내에서 재사용되었습니다: {annotation_id!r}", source, sequence))
        seen_ids.add(id_key)
        annotation_type = preserve_source_text(raw.get("annotation.type", ""))
        text_type = preserve_source_text(raw.get("annotation.ttype", ""))
        if annotation_type != config.expected_annotation_type:
            issues.append(DatasetIssue("UNSUPPORTED_ANNOTATION_TYPE", SampleSeverity.ERROR, f"지원하지 않는 annotation.type: {annotation_type!r}", source, sequence))
        if text_type != config.expected_text_type:
            issues.append(DatasetIssue("UNSUPPORTED_TEXT_TYPE", SampleSeverity.ERROR, f"지원하지 않는 annotation.ttype: {text_type!r}", source, sequence))
        bbox = _parse_bbox(raw.get("annotation.bbox"), width, height, source, sequence, issues)
        if bbox is None:
            continue
        text = preserve_source_text(raw.get("annotation.text", ""))
        if not text and not config.allow_empty_text:
            issues.append(DatasetIssue("EMPTY_ANNOTATION_TEXT", SampleSeverity.WARNING, "빈 텍스트 영역은 OCR 정답으로 확정하지 않습니다.", source, sequence))
        annotations.append(SampleAnnotation(sequence, annotation_id, text, bbox, annotation_type, text_type))
    return OCRSample(label_path.stem, label_path, image_path, filename, width, height, dict(image_record), tuple(annotations), tuple(issues))


# resolve 이미지 작업을 수행함
def _resolve_image(label_path: Path, label_root: Path, image_root: Path, filename: str, image_index: dict[str, tuple[Path, ...]], config: SampleRuleConfig, issues: list[DatasetIssue]) -> Path | None:
    if not filename:
        issues.append(DatasetIssue("MISSING_IMAGE_FILENAME", SampleSeverity.ERROR, "image.file.name이 없습니다.", str(label_path)))
        return None
    candidate = (image_root / label_path.relative_to(label_root).parent / filename).resolve()
    if config.reject_path_escape and not candidate.is_relative_to(image_root.resolve()):
        issues.append(DatasetIssue("IMAGE_PATH_ESCAPE", SampleSeverity.ERROR, f"이미지 경로가 원천데이터 밖을 가리킵니다: {filename!r}", str(label_path)))
        return None
    if candidate.is_file():
        return candidate
    alternatives = image_index.get(Path(filename).name, ())
    if len(alternatives) == 1:
        issues.append(DatasetIssue("IMAGE_RELATIVE_PATH_RECOVERED", SampleSeverity.WARNING, "상대경로가 없어 파일명 고유 매칭으로 복구했습니다.", str(label_path)))
        return alternatives[0]
    issues.append(DatasetIssue("MISSING_SOURCE_IMAGE", SampleSeverity.ERROR, f"원천 이미지를 찾을 수 없습니다: {filename}", str(label_path)))
    return None


# 바운딩 박스 데이터를 분석하여 파싱함
def _parse_bbox(value: Any, width: int, height: int, source: str, index: int, issues: list[DatasetIssue]) -> BoundingBox | None:
    if not isinstance(value, list) or len(value) != 4:
        issues.append(DatasetIssue("INVALID_BBOX", SampleSeverity.ERROR, "bbox는 [x, y, width, height] 배열이어야 합니다.", source, index))
        return None
    try:
        x, y, box_width, box_height = (int(number) for number in value)
    except (TypeError, ValueError):
        issues.append(DatasetIssue("INVALID_BBOX", SampleSeverity.ERROR, "bbox 좌표는 정수여야 합니다.", source, index))
        return None
    if x < 0 or y < 0 or box_width <= 0 or box_height <= 0:
        issues.append(DatasetIssue("INVALID_BBOX", SampleSeverity.ERROR, "bbox는 음수 좌표나 0 이하 크기를 가질 수 없습니다.", source, index))
        return None
    if width <= 0 or height <= 0 or x + box_width > width or y + box_height > height:
        issues.append(DatasetIssue("BBOX_OUTSIDE_IMAGE", SampleSeverity.ERROR, "bbox가 이미지 경계를 벗어났습니다.", source, index))
        return None
    return BoundingBox(x, y, box_width, box_height)


# positive int 작업을 수행함
def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
