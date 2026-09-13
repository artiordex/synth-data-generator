# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_synthetic_benchmark.py
# 경로: benchmarks/ocr_synthetic_benchmark.py
# 목적: 가상 백엔드 기반 OCR 파이프라인 처리 성능 벤치마크를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Deterministic OCR benchmark for the separated OCR pipeline.

This benchmark uses a fake OCR backend to measure pipeline routing and metric
calculation reproducibly. It does not claim native Tesseract/EasyOCR accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
import sys
import time

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ocr"))

from benchmarks.ocr_quality_report import PageQualityFixture, build_page_quality_record, summarize_page_quality
from ocr.engine.fake import FakeOCRBackend
from ocr.image.pipeline import run_image_ocr
from ocr.pdf.pipeline import plan_pdf_ocr, run_pdf_ocr
from ocr.pipeline.models import PdfType, PreprocessingProfile


GROUND_TRUTH = "식약처 OCR 123"


# main 작업을 수행함
def main() -> int:
    """Run the synthetic benchmark and write JSON/Markdown reports."""

    output_dir = ROOT / "benchmarks"
    fixture_dir = output_dir / "generated"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    image_samples = [
        _sample(fixture_dir / "image-normal.png", "Image", "Korean", "normal"),
        _sample(fixture_dir / "image-low-contrast.png", "Image", "Low Contrast", "low_contrast"),
        _sample(fixture_dir / "image-low-dpi.png", "Image", "Low DPI", "low_dpi"),
        _sample(fixture_dir / "image-empty-result.png", "Image", "Empty Result", "empty"),
    ]
    pdf_samples = _pdf_samples(fixture_dir)

    results = []
    for sample in image_samples:
        started = time.perf_counter()
        result = run_image_ocr(
            sample["path"],
            backend=FakeOCRBackend(_fake_recognizer(sample["problem"])),
            ground_truth=GROUND_TRUTH,
            max_attempts=5,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        page = result.pages[0]
        page_quality = build_page_quality_record(PageQualityFixture(
            page_no=page.page_no,
            reference_text=GROUND_TRUTH,
            recognized_text=page.raw_text,
            confidence=result.confidence,
            processing_time_ms=duration_ms,
            expected_cell_count=0,
            recognized_cell_count=0,
            expected_image_count=0,
            recognized_image_count=0,
            rotation_deg=0.0,
        ))
        results.append({
            "name": sample["path"].name,
            "family": sample["family"],
            "category": sample["category"],
            "engine": result.engine,
            "ground_truth_available": result.ground_truth_available,
            "character_accuracy": result.character_accuracy,
            "cer": result.cer,
            "wer": result.wer,
            "confidence": result.confidence,
            "quality_score": result.quality_score,
            "attempts": len(result.attempts),
            "best_attempt_no": result.best_attempt_no,
            "best_profile": result.profile.value if result.profile else None,
            "status": result.status.value,
            "duration_ms": round(duration_ms, 2),
            "routing_pass": bool(page.raw_text) and result.status.value == "SUCCESS" and result.character_accuracy >= 0.95,
            "page_quality": page_quality,
        })
    for sample in pdf_samples:
        started = time.perf_counter()
        plan = plan_pdf_ocr(sample["path"])
        execution = run_pdf_ocr(sample["path"], backend=FakeOCRBackend(lambda image: (GROUND_TRUTH, 0.93))) if plan.ocr_pages else None
        expected_ocr_pages = sample["expected_ocr_pages"]
        routing_pass = plan.pdf_type == sample["expected_type"] and plan.ocr_pages == expected_ocr_pages
        executed_ocr_pages = tuple(page.page_no for page in execution.pages if page.engine == "fake") if execution else ()
        results.append({
            "name": sample["path"].name,
            "family": "PDF",
            "category": sample["category"],
            "engine": "routing-only",
            "ground_truth_available": False,
            "character_accuracy": None,
            "cer": None,
            "wer": None,
            "confidence": None,
            "quality_score": 1.0 if routing_pass else 0.0,
            "attempts": 0,
            "best_attempt_no": None,
            "best_profile": None,
            "status": plan.status.value,
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "pdf_type": plan.pdf_type.value,
            "ocr_pages": list(plan.ocr_pages),
            "native_text_pages": list(plan.native_text_pages),
            "ocr_pages_executed": list(executed_ocr_pages),
            "routing_pass": routing_pass,
            "page_quality": None,
        })

    report = _summarize(results)
    (output_dir / "ocr-latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "ocr-latest.md").write_text(_markdown(report), encoding="utf-8")
    return 0


# sample 작업을 수행함
def _sample(path: Path, family: str, category: str, problem: str) -> dict[str, object]:
    image = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 120), GROUND_TRUTH, fill="black", font=ImageFont.load_default())
    dpi = (300, 300)
    if problem == "low_contrast":
        image = Image.new("RGB", (700, 500), "#dddddd")
        draw = ImageDraw.Draw(image)
        draw.text((50, 80), GROUND_TRUTH, fill="#999999", font=ImageFont.load_default())
        image = image.filter(ImageFilter.GaussianBlur(radius=0.6))
        dpi = (150, 150)
    elif problem == "low_dpi":
        dpi = (120, 120)
    image.save(path, dpi=dpi)
    return {"path": path, "family": family, "category": category, "problem": problem}


# PDF 문서 samples 작업을 수행함
def _pdf_samples(fixture_dir: Path) -> list[dict[str, object]]:
    import pymupdf as fitz

    image_path = fixture_dir / "pdf-page-image.png"
    Image.new("RGB", (200, 120), "white").save(image_path)

    text_pdf = fixture_dir / "pdf-text.pdf"
    with fitz.open() as document:
        page = document.new_page(width=300, height=200)
        page.insert_text((30, 50), "MFDS PDF Text Layer 123")
        document.save(text_pdf)

    image_pdf = fixture_dir / "pdf-image-only.pdf"
    with fitz.open() as document:
        page = document.new_page(width=300, height=200)
        page.insert_image(fitz.Rect(30, 30, 230, 150), filename=image_path)
        document.save(image_pdf)

    mixed_pdf = fixture_dir / "pdf-mixed.pdf"
    with fitz.open() as document:
        text_page = document.new_page(width=300, height=200)
        text_page.insert_text((30, 50), "MFDS PDF Text Layer 123")
        image_page = document.new_page(width=300, height=200)
        image_page.insert_image(fitz.Rect(30, 30, 230, 150), filename=image_path)
        document.save(mixed_pdf)

    return [
        {
            "path": text_pdf,
            "category": "Text PDF",
            "expected_type": PdfType.TEXT_PDF,
            "expected_ocr_pages": (),
        },
        {
            "path": image_pdf,
            "category": "Image-only PDF",
            "expected_type": PdfType.IMAGE_ONLY_PDF,
            "expected_ocr_pages": (1,),
        },
        {
            "path": mixed_pdf,
            "category": "Mixed PDF",
            "expected_type": PdfType.MIXED_PDF,
            "expected_ocr_pages": (2,),
        },
    ]


# fake recognizer 작업을 수행함
def _fake_recognizer(problem: str):
    # recognize 작업을 수행함
    def recognize(preprocessed):
        if problem == "normal":
            return GROUND_TRUTH, 0.96
        if problem == "low_contrast" and preprocessed.config.profile == PreprocessingProfile.LOW_CONTRAST:
            return GROUND_TRUTH, 0.95
        if problem == "low_dpi" and preprocessed.config.profile == PreprocessingProfile.LOW_RESOLUTION:
            return GROUND_TRUTH, 0.94
        if problem == "empty":
            return "", 0.99
        return "식약처 OGR 123", 0.61

    return recognize


# summarize 작업을 수행함
def _summarize(results: list[dict[str, object]]) -> dict[str, object]:
    by_category = {}
    for category in sorted({str(item["category"]) for item in results}):
        subset = [item for item in results if item["category"] == category]
        by_category[category] = _aggregate(subset)
    by_family = {}
    for family in sorted({str(item["family"]) for item in results}):
        subset = [item for item in results if item["family"] == family]
        by_family[family] = _aggregate(subset)
    return {
        "benchmark": "synthetic_fake_backend",
        "native_ocr_accuracy_claimed": False,
        "confidence_is_accuracy": False,
        "ground_truth": GROUND_TRUTH,
        "overall": _aggregate(results),
        "quality_contract": summarize_page_quality(
            row["page_quality"] for row in results if row.get("page_quality") is not None
        ),
        "by_family": by_family,
        "by_category": by_category,
        "samples": results,
    }


# aggregate 작업을 수행함
def _aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    accuracies = [float(row["character_accuracy"]) for row in rows if row["character_accuracy"] is not None]
    durations = [float(row["duration_ms"]) for row in rows]
    return {
        "samples": len(rows),
        "character_accuracy": round(mean(accuracies), 4) if accuracies else None,
        "pass_rate": round(sum(1 for value in accuracies if value >= 0.95) / len(accuracies), 4) if accuracies else None,
        "routing_pass_rate": round(sum(1 for row in rows if row.get("routing_pass") is True) / len(rows), 4) if rows else 0,
        "ocr_execution_pages": sum(len(row.get("ocr_pages_executed", [])) for row in rows),
        "retry_rate": round(sum(1 for row in rows if int(row["attempts"]) > 1) / len(rows), 4) if rows else 0,
        "review_rate": round(sum(1 for row in rows if row["status"] == "REVIEW_REQUIRED") / len(rows), 4) if rows else 0,
        "failure_rate": round(sum(1 for row in rows if row["status"] == "FAILED") / len(rows), 4) if rows else 0,
        "average_processing_time_ms": round(mean(durations), 2) if durations else 0,
    }


# 마크다운 작업을 수행함
def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# OCR Latest Benchmark",
        "",
        "Benchmark: synthetic fake backend",
        "",
        "This report validates pipeline routing and metric calculation. It does not claim native OCR engine accuracy.",
        "Confidence is a review signal, not proof of correctness.",
        "",
        "## Overall",
        "",
        f"- Character Accuracy: {report['overall']['character_accuracy']}",
        f"- Pass Rate: {report['overall']['pass_rate']}",
        f"- Routing Pass Rate: {report['overall']['routing_pass_rate']}",
        f"- Retry Rate: {report['overall']['retry_rate']}",
        f"- Text Fidelity Target Met: {report['quality_contract']['meets_text_target_95']}",
        f"- Structure Fidelity Target Met: {report['quality_contract']['meets_structure_target_95']}",
        f"- Visual Fidelity Target Met: {report['quality_contract']['meets_visual_target_95']}",
        "",
        "## PDF OCR Result",
        "",
        f"- Routing Pass Rate: {report['by_family']['PDF']['routing_pass_rate']}",
        f"- OCR Pages Executed: {report['by_family']['PDF']['ocr_execution_pages']}",
        "",
        "### PDF Categories",
        "",
    ]
    for category, aggregate in report["by_category"].items():
        if "PDF" in category:
            lines.append(f"- {category}: routing_pass_rate={aggregate['routing_pass_rate']}")
    lines.extend([
        "",
        "## Image OCR Result",
        "",
    ])
    for category, aggregate in report["by_category"].items():
        if "PDF" not in category:
            lines.append(f"- {category}: accuracy={aggregate['character_accuracy']}, pass_rate={aggregate['pass_rate']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
