# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: text_format_rules.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/text_format_rules.py
# 목적: 주민등록번호, 전화번호 등 정형 개인정보 서식 규칙을 처리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Versioned, lossless text-format constraints for native document editing."""
from dataclasses import dataclass
import unicodedata

RULE_VERSION = '1.0.0'
DETECTION_SEPARATORS = dict.fromkeys('‐‑‒–−－', '-')


@dataclass(frozen=True)
class DetectionView:
    original: str
    text: str


# detection view 작업을 수행함
def detection_view(text: str) -> DetectionView:
    """One code point in, one code point out: regex offsets remain reversible.

    Compatibility expansions and decomposed Hangul are deliberately left alone.
    Joining letters or crossing cells requires document geometry, not Unicode
    normalization, so this function never deletes spaces or joins lines.
    """
    result = []
    for char in text:
        if char in '\r\n':
            result.append(char)
        elif char.isspace():
            result.append(' ')
        elif char in DETECTION_SEPARATORS:
            result.append(DETECTION_SEPARATORS[char])
        else:
            normalized = unicodedata.normalize('NFKC', char)
            result.append(normalized if len(normalized) == 1 else char)
    return DetectionView(text, ''.join(result))


# literal 여부 및 유효성을 판별함
def is_literal(char: str) -> bool:
    return char.isspace() or unicodedata.category(char)[0] in {'P', 'S', 'C', 'Z', 'M'}


# restore format 작업을 수행함
def restore_format(original: str, replacement: str) -> str:
    """Restore exact original separators, whitespace and fullwidth glyph forms."""
    if len(original) != len(replacement):
        raise ValueError('FORMAT_LENGTH: 원문과 대체값의 글자 수가 다릅니다.')
    output = []
    for old, new in zip(original, replacement):
        if is_literal(old):
            output.append(old)
        elif '\uff01' <= old <= '\uff5e' and '!' <= new <= '~':
            output.append(chr(ord(new) + 0xFEE0))
        else:
            output.append(new)
    return ''.join(output)


# format 유효성 및 제약조건을 검증함
def validate_format(original: str, replacement: str) -> None:
    if len(original) != len(replacement):
        raise ValueError('FORMAT_LENGTH: 원문과 대체값의 글자 수가 다릅니다.')
    for index, (old, new) in enumerate(zip(original, replacement)):
        if is_literal(old) and old != new:
            raise ValueError(f'FORMAT_LITERAL: {index + 1}번째 공백·기호·제어문자를 유지하세요.')
        if not is_literal(old) and is_literal(new) and new not in {'*', '＊'}:
            raise ValueError(f'FORMAT_INSERTION: {index + 1}번째에 공백·기호를 삽입할 수 없습니다.')
        if '가' <= old <= '힣' and not ('가' <= new <= '힣' or new in {'*', '＊'}):
            raise ValueError('FORMAT_HANGUL: 한글 음절 또는 마스킹 문자로 치환하세요.')
        if old.isdecimal() and not new.isdecimal():
            raise ValueError(f'FORMAT_DIGIT: {index + 1}번째 숫자 형식을 유지하세요.')
        if '\uff10' <= old <= '\uff19' and not '\uff10' <= new <= '\uff19':
            raise ValueError('FORMAT_WIDTH: 전각 숫자 형식을 유지하세요.')
        if old.isascii() and old.isdecimal() and not new.isascii():
            raise ValueError('FORMAT_WIDTH: 반각 숫자 형식을 유지하세요.')
        if old.isascii() and old.isalpha() and new not in {'*', '＊'}:
            if not new.isascii() or not new.isalpha() or old.isupper() != new.isupper():
                raise ValueError('FORMAT_CASE: 영문 대소문자 형식을 유지하세요.')
