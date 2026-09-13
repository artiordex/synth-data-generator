# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: domain_whitelist.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/domain_whitelist.py
# 목적: 비식별화 제외 대상 안전 도메인 및 키워드 화이트리스트를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Reloadable domain exclusions shared by detection and masking."""
import json
import os
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Iterable


# normalize 작업을 수행함
def normalize(word: str) -> str:
    return unicodedata.normalize('NFC', word).strip().casefold()


# 화이트리스트 파일 경로 작업을 수행함
def whitelist_path() -> Path:
    configured = os.environ.get('SYNTHETIC_PII_WHITELIST_PATH')
    if configured:
        return Path(configured)
    root = next((p for p in Path(__file__).resolve().parents if (p / 'apps').is_dir()), Path.cwd())
    return Path(os.environ.get('STORAGE_DIR', str(root / 'storage'))) / 'whitelist.json'


# read 작업을 수행함
@lru_cache(maxsize=8)
def _read(path: str, modified: int, size: int) -> frozenset[str]:
    if size > 1024 * 1024:
        raise ValueError('화이트리스트는 1MB 이하로 설정하세요.')
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    words = data.get('words') if isinstance(data, dict) else data
    if not isinstance(words, list) or len(words) > 5000 or any(
            not isinstance(word, str) or not word.strip() or len(word) > 200 for word in words):
        raise ValueError('화이트리스트는 200자 이하 문자열의 배열이어야 합니다 (최대 5,000개).')
    return frozenset(normalize(word) for word in words)


# 화이트리스트 데이터를 파일 또는 저장소에서 로드함
def load_whitelist(path: Path | None = None) -> set[str]:
    path = path or whitelist_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return set()
    return set(_read(str(path.resolve()), stat.st_mtime_ns, stat.st_size))


# exclusions 작업을 수행함
def exclusions(ignored: Iterable[str] = (), whitelist: Iterable[str] | None = None) -> set[str]:
    return {normalize(word) for word in ignored} | (
        load_whitelist() if whitelist is None else {normalize(word) for word in whitelist})
