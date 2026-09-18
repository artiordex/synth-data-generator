# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/synthetic_engine/docengine/__init__.py
# 목적: Universal Document Engine 공유 IR 퍼사드 진입점을 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Universal Document Engine facade backed by the workspace's shared IR engine.

The public package name and version originate from the user's standalone
universal-document-engine scaffold. No second IR class hierarchy is created.
"""
from pathlib import Path

try:
    from synthetic_engine import __version__
except ImportError:  # pragma: no cover - standalone source checkout
    __version__ = '2.1.0'
__all__ = ['__version__', 'convert_document']


# document 데이터를 대상 포맷으로 변환함
def convert_document(input_file: Path, output_format: str, *, output_dir: Path | None = None,
                     fidelity_profile: str = 'auto', strict: bool = False) -> Path:
    """Convert using the single workspace implementation and its loss policy."""
    from synthetic_engine.document_conversion.pipeline import convert_document as convert
    return convert(input_file, output_format, output_dir=output_dir,
                   fidelity_profile=fidelity_profile, strict=strict)
