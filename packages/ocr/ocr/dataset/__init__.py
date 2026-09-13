# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/ocr/ocr/dataset/__init__.py
# 목적: 로컬 OCR 정답 데이터셋 어댑터 및 평가 유틸리티를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Dataset adapters for local OCR ground-truth samples."""

from .loader import SampleDatasetError, load_sample_dataset
from .benchmark import SampleOCRMetrics, evaluate_sample_page
from .manifest import sample_to_manifest_record, write_jsonl_manifest
from .baseline import (
    BaselineConfig,
    analyze_sample_page,
    build_baseline_report,
    classify_text_errors,
    render_baseline_markdown,
)
from .comparison import build_phase2_comparison, render_phase2_comparison_markdown
from .models import (
    DatasetAudit,
    DatasetIssue,
    OCRSample,
    SampleAnnotation,
    SampleRuleConfig,
    SampleSeverity,
)
from .rules import annotations_to_text, order_annotations

__all__ = [
    "DatasetAudit",
    "DatasetIssue",
    "OCRSample",
    "SampleAnnotation",
    "SampleDatasetError",
    "SampleRuleConfig",
    "SampleSeverity",
    "SampleOCRMetrics",
    "annotations_to_text",
    "evaluate_sample_page",
    "sample_to_manifest_record",
    "write_jsonl_manifest",
    "BaselineConfig",
    "analyze_sample_page",
    "build_baseline_report",
    "classify_text_errors",
    "render_baseline_markdown",
    "build_phase2_comparison",
    "render_phase2_comparison_markdown",
    "load_sample_dataset",
    "order_annotations",
]
