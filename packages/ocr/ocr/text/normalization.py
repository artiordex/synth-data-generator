# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: normalization.py
# 경로: packages/ocr/ocr/text/normalization.py
# 목적: OCR 인식 텍스트의 특수문자, 공백, 유니코드 정규화를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Safe OCR text normalization."""

from __future__ import annotations

import re
import unicodedata


CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
_CONFUSABLE_DIGITS = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "s": "5", "B": "8"})


# OCR 인식 텍스트 데이터를 표준 형식으로 정규화함
def normalize_ocr_text(raw_text: str, *, preserve_whitespace: bool = True) -> str:
    """Normalize OCR text without silently destroying layout whitespace.

    NFC and line-ending normalization are safe for all OCR output.  Space
    collapsing is opt-in for legacy consumers because it makes whitespace
    quality impossible to measure and damages fixed-format fields.
    """

    normalized = unicodedata.normalize("NFC", raw_text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = CONTROL_RE.sub("", normalized)
    if not preserve_whitespace:
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


# structured 토큰 데이터를 표준 형식으로 정규화함
def normalize_structured_token(token: str) -> str:
    """Apply conservative OCR repairs to date and amount-shaped tokens.

    This does not rewrite arbitrary letters or infer a value from a sample.
    Confusable glyphs are changed only when the surrounding token already
    looks like a date or an amount, and separators are only de-spaced inside
    date-like tokens.
    """

    value = unicodedata.normalize("NFC", str(token))
    separator_count = len(re.findall(r"[./-]", value))
    amount_like = bool(re.search(r"(?:원|KRW|₩|￦)", value)) or bool(
        re.search(r"\d[\dOolI|SsbB]*(?:,\d{3})+", value)
    )
    date_like = separator_count >= 2 and bool(re.search(r"\d", value))
    if not (date_like or amount_like):
        return value
    repaired = value.translate(_CONFUSABLE_DIGITS)
    if date_like:
        repaired = re.sub(r"\s*([./-])\s*", r"\1", repaired)
    if amount_like:
        repaired = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", repaired)
    return repaired
