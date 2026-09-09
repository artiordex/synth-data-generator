# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: provenance.py
# 경로: packages/synthetic_engine/synthetic_engine/common/provenance.py
# 목적: 파일·데이터 무결성과 실행 장치 정보를 계산함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
import pandas as pd

def calculate_sha256(path_or_df: Path | pd.DataFrame) -> str:
    """파일 또는 데이터프레임의 SHA-256 해시를 계산함"""
    if isinstance(path_or_df, Path):
        hasher = hashlib.sha256()
        with path_or_df.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    else:
        csv_bytes = path_or_df.to_csv(index=False).encode("utf-8")
        return hashlib.sha256(csv_bytes).hexdigest()

def detect_system_device() -> dict[str, Any]:
    """현재 실행 환경의 CPU·GPU 장치 정보를 반환함"""
    gpu_available = False
    device_name = "CPU"
    vram_total_mb = 0
    cuda_version = ""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            device_name = torch.cuda.get_device_name(0)
            vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2)
            cuda_version = torch.version.cuda or ""
    except Exception:
        pass
    return {
        "gpu_available": gpu_available,
        "device_name": device_name,
        "vram_total_mb": vram_total_mb,
        "cuda_version": cuda_version,
    }
