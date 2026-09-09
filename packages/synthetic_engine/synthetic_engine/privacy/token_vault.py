"""
파일명: token_vault.py
경로: packages/synthetic_engine/synthetic_engine/privacy/token_vault.py
목적: 원본값을 저장하지 않고 프로젝트 범위의 결정적 가명 토큰을 생성함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any


def _secret() -> bytes:
    """가명 토큰 생성에 사용할 비밀키를 반환함"""
    return os.environ.get("PSEUDONYM_TOKEN_SECRET", "local-development-token-secret").encode("utf-8")


def project_token(value: Any, *, project_id: str, namespace: str, key_version: str = "v1") -> str | None:
    """프로젝트 범위의 결정적 가명 토큰을 생성함"""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return normalized
    scope = f"{key_version}\x1f{project_id}\x1f{namespace}\x1f{normalized}".encode("utf-8")
    digest = hmac.new(_secret(), scope, hashlib.sha256).hexdigest()[:20].upper()
    prefix = re.sub(r"[^A-Za-z0-9]", "", namespace).upper()[:4] or "TOK"
    return f"{prefix}-{digest}"

