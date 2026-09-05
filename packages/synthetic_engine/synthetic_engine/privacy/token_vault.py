"""Project-scoped deterministic pseudonym tokens without storing source values."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any


def _secret() -> bytes:
    return os.environ.get("PSEUDONYM_TOKEN_SECRET", "local-development-token-secret").encode("utf-8")


def project_token(value: Any, *, project_id: str, namespace: str, key_version: str = "v1") -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return normalized
    scope = f"{key_version}\x1f{project_id}\x1f{namespace}\x1f{normalized}".encode("utf-8")
    digest = hmac.new(_secret(), scope, hashlib.sha256).hexdigest()[:20].upper()
    prefix = re.sub(r"[^A-Za-z0-9]", "", namespace).upper()[:4] or "TOK"
    return f"{prefix}-{digest}"

