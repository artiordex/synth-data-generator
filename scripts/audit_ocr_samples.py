# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: audit_ocr_samples.py
# 경로: scripts/audit_ocr_samples.py
# 목적: OCR 샘플 데이터셋의 파일 구조 및 무결성을 검증함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Audit a local OCR sample corpus without opening or executing source files.

Example:
    python scripts/audit_ocr_samples.py docs/New_sample --json-out output/ocr_sample_audit.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = REPO_ROOT / "packages" / "ocr"
if str(OCR_ROOT) not in sys.path:
    sys.path.insert(0, str(OCR_ROOT))

from ocr.dataset import load_sample_dataset  # noqa: E402


# main 작업을 수행함
def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local box-level OCR samples")
    parser.add_argument("root", type=Path, help="sample root containing 라벨링데이터 and 원천데이터")
    parser.add_argument("--strict", action="store_true", help="return non-zero when any sample error exists")
    parser.add_argument("--json-out", type=Path, help="write the machine-readable audit report")
    args = parser.parse_args()
    _, audit = load_sample_dataset(args.root, strict=False)
    report = audit.to_dict()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if args.strict and not audit.passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
