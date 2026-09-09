"""
파일명: file_access.py
경로: apps/api/src/synthetic_api/infrastructure/file_access.py
목적: 외부 입력 파일 경로가 허용 저장소 안에 있는지 검증함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from pathlib import Path

from fastapi import HTTPException


def confined_file(path: Path, root: Path) -> Path:
    """파일 경로가 지정된 루트 안에 있고 실제 파일인지 검증함"""
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise HTTPException(status_code=403, detail='File access is not permitted.')
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail='File not found.')
        return resolved
    except (OSError, ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail='File not found.') from None
