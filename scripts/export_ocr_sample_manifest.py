# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: export_ocr_sample_manifest.py
# 경로: scripts/export_ocr_sample_manifest.py
# 목적: OCR 말뭉치를 기계학습용 JSONL 매니페스트로 내보냄.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Export the local OCR corpus to a deterministic JSONL training manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = REPO_ROOT / "packages" / "ocr"
if str(OCR_ROOT) not in sys.path:
    sys.path.insert(0, str(OCR_ROOT))

from ocr.dataset import load_sample_dataset, write_jsonl_manifest  # noqa: E402


# main 작업을 수행함
def main() -> int:
    parser = argparse.ArgumentParser(description="Export local OCR labels as JSONL")
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/ocr_sample_manifest.jsonl"))
    parser.add_argument("--valid-only", action="store_true", help="exclude samples with validation errors")
    args = parser.parse_args()
    samples, audit = load_sample_dataset(args.root)
    count = write_jsonl_manifest(samples, args.output, include_invalid=not args.valid_only)
    print(f"manifest_records={count} dataset_errors={audit.error_count} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
