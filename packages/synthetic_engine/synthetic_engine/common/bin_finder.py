# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: bin_finder.py
# 경로: packages/synthetic_engine/synthetic_engine/common/bin_finder.py
# 목적: pyhwp 등 플랫폼 독립적 바이너리 실행 파일 경로 탐색을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Locate pyhwp commands without requiring a platform-specific installation path."""
from pathlib import Path
import shutil
import sys


# pyhwp bin 대상을 탐색하여 반환함
def find_pyhwp_bin(tool_name: str) -> list[str]:
    if not tool_name or Path(tool_name).name != tool_name or '/' in tool_name or '\\' in tool_name:
        raise ValueError('Expected a pyhwp command name, not a path')
    directory = Path(sys.executable).parent
    for candidate in (directory / f'{tool_name}.exe', directory / tool_name):
        if candidate.is_file():
            return [str(candidate)]
    executable = shutil.which(tool_name)
    if executable:
        return [executable]
    modules = {'hwp5html': 'hwp5.hwp5html', 'hwp5txt': 'hwp5.hwp5txt', 'hwp5proc': 'hwp5.hwp5proc'}
    if tool_name in modules:
        return [sys.executable, '-m', modules[tool_name]]
    return [tool_name]
