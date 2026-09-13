# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: benchmark_ocr_samples.py
# 경로: scripts/benchmark_ocr_samples.py
# 목적: 로컬 OCR 샘플 말뭉치 벤치마크 평가를 일괄 실행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Run and report a reproducible local OCR baseline benchmark.

The command evaluates only samples with a paired source image and no dataset
validation errors. Every per-sample failure is recorded and the remaining
samples continue. No OCR engine or source-data rule is changed here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = REPO_ROOT / "packages" / "ocr"
if str(OCR_ROOT) not in sys.path:
    sys.path.insert(0, str(OCR_ROOT))

from PIL import Image  # noqa: E402

from ocr.dataset import (  # noqa: E402
    BaselineConfig,
    analyze_sample_page,
    build_phase2_comparison,
    build_baseline_report,
    load_sample_dataset,
    render_baseline_markdown,
    render_phase2_comparison_markdown,
)
from ocr.engine.factory import build_local_ocr_backend  # noqa: E402
from ocr.image.pipeline import run_image_ocr  # noqa: E402


# main 작업을 수행함
def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local OCR on labelled images")
    parser.add_argument("root", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="number of valid paired samples; 0 means all")
    parser.add_argument("--output-dir", type=Path, help="directory for baseline summary/errors/worst-cases/report")
    parser.add_argument("--output", type=Path, help="legacy single JSON output path")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--confidence-threshold", type=float, default=0.85)
    parser.add_argument("--bbox-iou-threshold", type=float, default=0.85)
    parser.add_argument("--one-to-one-iou-threshold", type=float, default=0.50)
    parser.add_argument("--baseline-summary", type=Path, help="previous summary JSON for a Phase 2 comparison")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be zero or greater")
    if not 0.0 <= args.confidence_threshold <= 1.0:
        parser.error("--confidence-threshold must be between 0 and 1")
    if not 0.0 <= args.bbox_iou_threshold <= 1.0:
        parser.error("--bbox-iou-threshold must be between 0 and 1")
    if not 0.0 <= args.one_to_one_iou_threshold <= 1.0:
        parser.error("--one-to-one-iou-threshold must be between 0 and 1")

    samples, audit = load_sample_dataset(args.root)
    candidates = [sample for sample in samples if sample.image_path and not sample.has_errors]
    if args.limit > 0:
        candidates = candidates[: args.limit]
    config = BaselineConfig(
        confidence_threshold=args.confidence_threshold,
        bbox_iou_threshold=args.bbox_iou_threshold,
        one_to_one_iou_threshold=args.one_to_one_iou_threshold,
        top_n=max(1, args.top_n),
    )
    backend = build_local_ocr_backend(REPO_ROOT) if candidates else None
    analyses: list[tuple[Any, dict[str, Any], tuple[Any, ...]]] = []
    for index, sample in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {sample.sample_id}", flush=True)
        try:
            actual_size = _image_size(sample.image_path)
            result = run_image_ocr(
                sample.image_path,
                backend=backend,
                ground_truth=sample.ground_truth_text,
                max_attempts=max(1, args.max_attempts),
            )
            page = result.pages[0] if result.pages else None
            # Aspect/upscale retries produce OCR boxes in the transformed
            # image space.  Prefer the explicit coordinate metadata instead
            # of assuming that every attempt has the source image dimensions.
            evaluated_size = actual_size
            if page is not None and page.coordinate_width_px and page.coordinate_height_px:
                evaluated_size = (page.coordinate_width_px, page.coordinate_height_px)
            row, groups = analyze_sample_page(
                sample,
                page,
                source_image_size=evaluated_size,
                config=config,
            )
            row["pipeline_cer"] = result.cer
            row["pipeline_wer"] = result.wer
            row["pipeline_quality_score"] = result.quality_score
            row["pipeline_issues"] = [issue.value for issue in result.issues]
        except Exception as exc:  # noqa: BLE001 - isolate one corrupt/runtime sample
            message = f"{type(exc).__name__}: {exc}"
            print(f"  OCR_RUNTIME_ERROR: {message}", file=sys.stderr, flush=True)
            row, groups = analyze_sample_page(
                sample,
                None,
                config=config,
                runtime_error=message,
            )
        analyses.append((sample, row, groups))

    report, error_rows = build_baseline_report(
        analyses,
        dataset_audit=audit.to_dict(),
        config=config,
    )
    if backend is not None:
        primary = getattr(backend, "primary", backend)
        detector_settings = {}
        for name in ("det_box_thresh", "det_text_thresh", "det_unclip_ratio", "det_limit_side_len", "input_padding"):
            if hasattr(primary, name):
                detector_settings[name] = getattr(primary, name)
        if detector_settings:
            report.setdefault("configuration", {})["ocr_detector"] = detector_settings
        ensemble_settings = {
            name: getattr(backend, name)
            for name in (
                "supplemental_detection",
                "uncovered_component_ratio",
                "supplemental_min_confidence",
            )
            if hasattr(backend, name)
        }
        if ensemble_settings:
            report.setdefault("configuration", {})["ocr_ensemble"] = ensemble_settings
    output_dir = args.output_dir
    if output_dir is None:
        output_path = args.output or Path("output/ocr_sample_benchmark.json")
        output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "ocr_baseline_summary.json"
    errors_path = output_dir / "ocr_baseline_errors.jsonl"
    worst_path = output_dir / "ocr_baseline_worst_cases.json"
    markdown_path = output_dir / "ocr_baseline_report.md"
    summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors_path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in error_rows), encoding="utf-8")
    worst_path.write_text(json.dumps(report["worst_cases"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_baseline_markdown(report), encoding="utf-8")
    if args.baseline_summary:
        before = json.loads(args.baseline_summary.read_text(encoding="utf-8"))
        comparison = build_phase2_comparison(before, report)
        (output_dir / "ocr_phase2_comparison.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output_dir / "ocr_phase2_comparison.md").write_text(
            render_phase2_comparison_markdown(comparison), encoding="utf-8"
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "processed_count": report["metrics"]["processed_sample_count"],
        "failed_sample_count": report["metrics"]["failed_sample_count"],
        "summary": str(summary_path),
        "errors": str(errors_path),
        "worst_cases": str(worst_path),
        "report": str(markdown_path),
    }, ensure_ascii=False))
    return 0


# 이미지 크기 작업을 수행함
def _image_size(path: Path | None) -> tuple[int, int]:
    if path is None:
        raise ValueError("source image is missing")
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return image.size


if __name__ == "__main__":
    raise SystemExit(main())
