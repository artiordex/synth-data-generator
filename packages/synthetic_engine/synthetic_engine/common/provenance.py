# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
import pandas as pd

def calculate_sha256(path_or_df: Path | pd.DataFrame) -> str:
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
