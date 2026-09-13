# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: file_access.py
# 경로: apps/api/src/synthetic_api/infrastructure/file_access.py
# 목적: 외부 입력 경로 접근 검증 및 허용 디렉터리 접근 제어 유틸리티를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from fastapi import HTTPException


# 허용 디렉터리 내 파일 경로 접근 유효성을 검증함
def confined_file(path: Path, root: Union[Path, Sequence[Path]]) -> Path:
    """파일 경로가 지정된 허용 루트(단일 또는 복수) 안에 있고 실제 파일인지 검증함"""
    roots = [root] if isinstance(root, Path) else list(root)
    try:
        resolved = path.resolve()
        matching_root = None
        for r in roots:
            try:
                if resolved.is_relative_to(r.resolve()):
                    matching_root = r
                    break
            except (ValueError, OSError):
                continue

        if not matching_root:
            raise HTTPException(status_code=403, detail='허용되지 않은 파일 경로입니다.')
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail='다운로드 파일을 찾을 수 없습니다.')
        return resolved
    except HTTPException:
        raise
    except (OSError, ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail='다운로드 파일을 찾을 수 없습니다.') from None
