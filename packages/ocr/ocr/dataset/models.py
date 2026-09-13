# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: models.py
# 경로: packages/ocr/ocr/dataset/models.py
# 목적: OCR 데이터셋 샘플 및 어노테이션 데이터 모델을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Stable data contracts for OCR sample datasets.

The New_sample data is a box-level corpus rather than a conventional one-text
per-image corpus.  These models deliberately keep the original annotation
strings and array order.  A vendor supplied ``id`` is metadata only because
the corpus contains reused ids within a single JSON file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..pipeline.models import BoundingBox


class SampleSeverity(str, Enum):
    """Severity used by dataset validation and benchmark gates."""

    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class DatasetIssue:
    """A deterministic, machine-readable dataset quality issue."""

    code: str
    severity: SampleSeverity
    message: str
    source: str
    annotation_index: int | None = None


@dataclass(frozen=True)
class SampleAnnotation:
    """One source annotation, retaining exact source text and position."""

    sequence: int
    annotation_id: Any
    text: str
    bbox: BoundingBox
    annotation_type: str
    text_type: str


@dataclass(frozen=True)
class OCRSample:
    """One image and its matching label file."""

    sample_id: str
    label_path: Path
    image_path: Path | None
    image_filename: str
    image_width: int
    image_height: int
    metadata: dict[str, Any]
    annotations: tuple[SampleAnnotation, ...]
    issues: tuple[DatasetIssue, ...] = ()

    # errors 보유 여부를 확인함
    @property
    def has_errors(self) -> bool:
        return any(issue.severity is SampleSeverity.ERROR for issue in self.issues)

    # ground truth 텍스트 작업을 수행함
    @property
    def ground_truth_text(self) -> str:
        """Return source-preserving reading-order text."""

        from .rules import annotations_to_text

        return annotations_to_text(self.annotations)


@dataclass(frozen=True)
class SampleRuleConfig:
    """Standard rules for this box-level OCR corpus."""

    label_directory: str = "라벨링데이터"
    image_directory: str = "원천데이터"
    label_suffix: str = ".json"
    image_suffixes: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    expected_annotation_type: str = "rectangle"
    expected_text_type: str = "textType1"
    allow_empty_text: bool = False
    allow_duplicate_annotation_ids: bool = True
    reject_path_escape: bool = True
    line_overlap_ratio: float = 0.35
    line_center_tolerance_ratio: float = 0.55


@dataclass(frozen=True)
class DatasetAudit:
    """Aggregate validation result suitable for API/CLI reporting."""

    root: Path
    sample_count: int
    valid_sample_count: int
    warning_count: int
    error_count: int
    annotation_count: int
    paired_image_count: int
    issues: tuple[DatasetIssue, ...] = field(default_factory=tuple)

    # passed 작업을 수행함
    @property
    def passed(self) -> bool:
        return self.error_count == 0

    # dict 형식으로 변환하여 반환함
    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "sample_count": self.sample_count,
            "valid_sample_count": self.valid_sample_count,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "annotation_count": self.annotation_count,
            "paired_image_count": self.paired_image_count,
            "passed": self.passed,
            "issues": [
                {
                    "code": issue.code,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "source": issue.source,
                    "annotation_index": issue.annotation_index,
                }
                for issue in self.issues
            ],
        }
