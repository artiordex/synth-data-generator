# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: korean_quality.py
# 경로: packages/ocr/ocr/text/korean_quality.py
# 목적: 한국어 자모 분리 교정, 맞춤법 및 OCR 오인식 패턴 품질을 검증함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Korean OCR candidate quality heuristics.

These helpers do not claim OCR accuracy.  They only rank competing local OCR
candidates and flag Hangul-shaped gibberish that should be retried or reviewed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Protocol


class TextCandidate(Protocol):
    text: str
    confidence: float


KOREAN_DOCUMENT_TERMS = (
    "가공", "가능", "개선", "경제", "계획", "공유", "국민", "기관", "다양",
    "대응", "대책", "데이터", "문제", "문화", "발굴", "배경", "범위", "분석",
    "분야", "비교", "사회", "서비스", "수립", "수요", "안전", "예상", "예측",
    "요소", "원인", "위험", "이용", "절차", "정책", "제공", "제거", "제시",
    "질병", "충분", "충족", "필요", "행정", "혁신", "활용", "효율",
)
KOREAN_FUNCTIONAL_PATTERNS = (
    "하기", "하고", "하며", "하여", "하는", "되는", "있는", "등이", "등을",
    "등에", "등의", "위한", "위하여", "대한", "통해", "또는", "거나",
    "가", "을", "를", "은", "는", "에", "의",
)
SUPPORTED_PUNCTUATION = set(
    ".,:;!?()[]/%+-_'\"·ㆍ※℃℉°㎎㎏㎖㎗㎘㎜㎝㎞㎡㎥μµ≤≥≠±×÷"
    "。、「」！？（）【】《》"
    "①②③④⑤⑥⑦⑧⑨⑩○●◎□■☑✓"
)


# special 문자 ratio 작업을 수행함
def special_character_ratio(text: str) -> float:
    """Return the fraction of characters outside supported OCR scripts."""

    characters = [character for character in str(text) if not character.isspace()]
    if not characters:
        return 0.0
    invalid = sum(
        not (
            character.isalnum()
            or character == "_"
            or character in SUPPORTED_PUNCTUATION
            or "\uac00" <= character <= "\ud7a3"
            or "\u3040" <= character <= "\u30ff"
            or "\u4e00" <= character <= "\u9fff"
        )
        for character in characters
    )
    return invalid / len(characters)


# korean 품질 score 작업을 수행함
def korean_quality_score(text: str) -> float:
    """Score whether Hangul OCR looks like Korean prose, not only valid glyphs."""

    value = unicodedata.normalize("NFC", str(text or "")).strip()
    characters = [ch for ch in value if not ch.isspace()]
    if not characters:
        return 0.0
    hangul_count = len(re.findall(r"[\uac00-\ud7a3]", value))
    if hangul_count == 0:
        return 0.35 if re.search(r"[A-Za-z0-9]", value) else 0.0

    hangul_ratio = hangul_count / max(1, len(characters))
    tokens = re.findall(r"[\uac00-\ud7a3A-Za-z0-9]+", value)
    singleton_ratio = (
        sum(1 for token in tokens if re.fullmatch(r"[\uac00-\ud7a3]", token)) / len(tokens)
        if tokens
        else 0.0
    )
    term_hits = sum(1 for term in KOREAN_DOCUMENT_TERMS if term in value)
    functional_hits = sum(1 for pattern in KOREAN_FUNCTIONAL_PATTERNS if pattern in value)
    long_hangul_tokens = [
        token for token in tokens
        if re.fullmatch(r"[\uac00-\ud7a3]{5,}", token)
    ]
    long_without_pattern = sum(
        1 for token in long_hangul_tokens
        if not any(pattern in token for pattern in KOREAN_FUNCTIONAL_PATTERNS)
    )
    long_token_penalty = long_without_pattern / max(1, len(long_hangul_tokens))

    score = 0.18 + min(0.26, hangul_ratio * 0.26)
    score += min(0.32, term_hits * 0.055)
    score += min(0.18, functional_hits * 0.025)
    score -= min(0.16, singleton_ratio * 0.16)
    score -= min(0.20, special_character_ratio(value) * 0.50)
    score -= min(0.16, long_token_penalty * 0.16)
    return max(0.0, min(1.0, score))


# OCR 인식 candidate score 작업을 수행함
def ocr_candidate_score(text: str, confidence: float) -> float:
    """Rank one OCR candidate by confidence and Korean text plausibility."""

    value = str(text or "").strip()
    if not value:
        return -1.0
    confidence = max(0.0, min(1.0, float(confidence)))
    replacement_penalty = 0.2 if "\ufffd" in value else 0.0
    valid_chars = len(
        re.findall(r"[0-9A-Za-z\uac00-\ud7a3\s.,:;!?()\[\]/%+\-'\"\u00b7]", value)
    )
    plausibility = valid_chars / max(1, len(value))
    return (
        confidence * 0.40
        + plausibility * 0.08
        + korean_quality_score(value) * 0.52
        - replacement_penalty
    )


# needs secondary check 작업을 수행함
def needs_secondary_check(text: str, confidence: float) -> bool:
    """Return True when a candidate should be retried by another OCR backend."""

    value = str(text or "").strip()
    confidence = max(0.0, min(1.0, float(confidence)))
    if not value:
        return True
    if "\ufffd" in value:
        return True
    if special_character_ratio(value) >= 0.18:
        return True
    if not re.search(r"[\uac00-\ud7a3]", value):
        return confidence < 0.55
    if confidence >= 0.85 and len(re.findall(r"[\uac00-\ud7a3]", value)) < 6:
        return False
    return korean_quality_score(value) < 0.52


# OCR 인식 노이즈 텍스트 여부 및 유효성을 판별함
def is_ocr_noise_text(text: str) -> bool:
    """Detect separators or empty OCR artifacts that should not enter output."""

    value = str(text or "").strip()
    if not value:
        return True
    if len(value) >= 8 and not re.search(r"[\uac00-\ud7a3A-Za-z0-9]", value):
        return True
    if len(value) >= 8 and len(re.sub(r"[.\-_=~·ㆍ…\s]", "", value)) <= 1:
        return True
    return False


# OCR 인식 결과 품질 작업을 수행함
def ocr_result_quality(candidates: Iterable[TextCandidate], *, expected_words: int = 18) -> float:
    """Score a page/crop candidate for choosing between OCR attempts."""

    text_words = [
        candidate for candidate in candidates
        if re.search(r"[\uac00-\ud7a3A-Za-z0-9]", str(candidate.text))
    ]
    if not text_words:
        return -1.0
    confidence = sum(float(candidate.confidence) for candidate in text_words) / len(text_words)
    quality = sum(korean_quality_score(str(candidate.text)) for candidate in text_words) / len(text_words)
    coverage = min(1.0, len(text_words) / max(1, expected_words))
    return confidence * 0.34 + quality * 0.52 + coverage * 0.14
