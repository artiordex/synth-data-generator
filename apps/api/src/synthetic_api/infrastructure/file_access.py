"""Resolve client-controlled file paths within a single permitted directory."""
from pathlib import Path

from fastapi import HTTPException


def confined_file(path: Path, root: Path) -> Path:
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise HTTPException(status_code=403, detail='File access is not permitted.')
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail='File not found.')
        return resolved
    except (OSError, ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail='File not found.') from None
