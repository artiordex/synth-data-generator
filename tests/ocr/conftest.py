# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: conftest.py
# 경로: tests/ocr/conftest.py
# 목적: OCR 단위 및 통합 테스트 환경 픽스처를 구성함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Import local OCR package from the monorepo workspace."""

from __future__ import annotations

import sys
from pathlib import Path


OCR_PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "ocr"
if str(OCR_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(OCR_PACKAGE_ROOT))
