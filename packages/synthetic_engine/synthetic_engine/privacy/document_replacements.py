# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: document_replacements.py
# 경로: packages/synthetic_engine/synthetic_engine/privacy/document_replacements.py
# 목적: 문서 내 개인정보 검출 항목 치환 및 가명 처리를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PII suggestions use the same context-gated person detector as masking."""
import re
import secrets
import string
from collections import Counter
from typing import Iterable

from ..profiling.kiwi_pii_detector import detect_korean_named_entities
from .domain_whitelist import exclusions, normalize
from .masker import SmartMasker
from .text_format_rules import detection_view, restore_format, validate_format

PATTERNS = {
    '이메일': re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
    '전화번호': re.compile(r'(?<!\d)(?:01[016789]|02|0[3-6][1-5])[- ]?\d{3,4}[- ]?\d{4}(?!\d)'),
    '주민등록번호': re.compile(r'(?<!\d)\d{6}-[1-8]\d{6}(?!\d)'),
}

# Only labelled identifiers and address-shaped text are added here; ordinary
# nouns and organization names are never inferred to be personal names.
CONTEXT_PATTERNS = {
    '이름': re.compile(r'(?:고객|본인|상담원|배우자|보호자|환자\s*정보|주문자(?:\s*이름은)?|성명\s*\(한글/영문\)|비상연락망\s*\(부친\))\s*[:：]?\s*(?:[가-힣0-9]+팀\s+)?(?P<value>[가-힣]{3,4})(?=[ \t]*[(:：/)]|[ \t]*고객님|[ \t]*\n|$)'),
    '영문 이름': re.compile(r'성명\s*\(한글/영문\)\s*[가-힣]{2,4}\s*/\s*(?P<value>[A-Z]+(?: [A-Z]+){1,3})'),
    '생년월일': re.compile(r'(?:생년월일\s*[:：]?\s*|성별\s*/\s*생년월일\s*[남여]\s*/\s*)(?P<value>\d{4}(?:[-.]\d{2}[-.]\d{2}|년\s*\d{2}월\s*\d{2}일))'),
    '출생일': re.compile(r'(?P<value>\d{4}-\d{2}-\d{2})(?=\s*출생)'),
    '여권번호': re.compile(r'여권번호\s*[:：(]?\s*(?P<value>[A-Z]\d{8})'),
    '계좌번호': re.compile(r'[가-힣]+은행\s+(?P<value>\d{3,6}-\d{2,6}-\d{4,6})'),
    '운전면허번호': re.compile(r'(?P<value>\d{2}-\d{2}-\d{6}-\d{2})(?=\s*\(운전면허번호\))'),
    '사용자 ID': re.compile(r'아이디\s*[:：]\s*(?P<value>[A-Za-z0-9_]+)'),
    '환자번호': re.compile(r'환자\s*번호\s*[:：]\s*(?P<value>[A-Za-z]+-\d+-\d+)'),
    '보험 자격번호': re.compile(r'자격번호\s*\(\s*(?P<value>\d+)'),
    '카드번호': re.compile(r'카드\s+(?P<value>\d{4}-\*{4}-\*{4}-\d{4})'),
    '주소': re.compile(r'(?P<value>(?:[가-힣]+(?:특별시|광역시|도)|경기)\s+[가-힣]+시?\s*(?:[가-힣]+구\s+)?[가-힣]+(?:로|길)\s+\d+(?:\s+\d+동\s+\d+호|\s+[가-힣A-Za-z]+(?:\s+[A-Z]동)?\s+\d+(?:동\s+\d+호|호|층)|\s+\d+호)?)(?=\s|[),.]|이며|이고|에서|에서|로|으로|에)'),
}


# propose 작업을 수행함
def _propose(text: str, *, ignored: Iterable[str] = (), whitelist: Iterable[str] | None = None):
    excluded = exclusions(ignored, whitelist)
    found = {}
    matches = [(match.group(), kind) for kind, pattern in PATTERNS.items() for match in pattern.finditer(text)]
    entities = detect_korean_named_entities(text, whitelist=excluded)
    name_counts = Counter(entity['entity'] for entity in entities if entity['type'] == 'PERSON_NAME')
    matches.extend((entity['entity'], '이름') for entity in entities if entity['type'] == 'PERSON_NAME')
    for kind, pattern in CONTEXT_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group('value')
            if '\n' in value or '\r' in value:
                continue
            matches.append((value, kind))
            if kind == '이름':
                name_counts[value] += 1
    for original, kind in matches:
        if original in found or normalize(original) in excluded:
            continue
        if kind == '이름':
            # Native editing replaces every exact occurrence. Reject global
            # replacement if the same spelling also occurs without name context.
            if text.count(original) > name_counts[original]:
                continue
            replacement = SmartMasker.mask_name(original)
        elif kind == '이메일':
            local, domain = original.split('@')
            replacement = ''.join(secrets.choice(string.ascii_lowercase) for _ in local) + '@' + domain
            if replacement == original:
                replacement = ('a' if local[0] != 'a' else 'b') + replacement[1:]
        elif kind in {'생년월일', '출생일'}:
            numbers = iter(['1990', '06', '15'] if not original.startswith('1990') else ['1991', '07', '16'])
            replacement = re.sub(r'\d+', lambda _: next(numbers), original)
        elif kind in {'주소', '영문 이름', '사용자 ID'}:
            replacement = ''.join(
                secrets.choice('가나다라마바사아자차카타파하') if '가' <= c <= '힣'
                else secrets.choice(string.ascii_uppercase) if c.isupper()
                else secrets.choice(string.ascii_lowercase) if c.islower()
                else str((int(c) + secrets.randbelow(9) + 1) % 10) if c.isdigit()
                else c for c in original)
        else:
            replacement = ''.join(str((int(c) + secrets.randbelow(9) + 1) % 10) if c.isdigit() else c for c in original)
            if kind == '전화번호':
                prefix = re.match(r'(?:01[016789]|02|0[3-6][1-5])', original).group()
                replacement = prefix + replacement[len(prefix):]
        found[original] = {'original': original, 'replacement': replacement, 'kind': kind, 'count': text.count(original)}
    return list(found.values())


# restore valid candidate 작업을 수행함
def _restore_valid_candidate(text: str, item: dict, match: re.Match, excluded: set[str]):
    original = text[match.start():match.end()]
    if normalize(original) in excluded:
        return None
    try:
        replacement = restore_format(original, item['replacement'])
        validate_format(original, replacement)
    except ValueError:
        # Automatic PII suggestions are best-effort. A malformed suggestion
        # must not abort the entire document inspection; strict validation is
        # still enforced for user-submitted replacements in validate_replacements.
        return None
    if original == replacement:
        return None
    return {
        **item,
        'original': original,
        'replacement': replacement,
        'count': text.count(original),
    }


# propose 작업을 수행함
def propose(text: str, *, ignored: Iterable[str] = (), whitelist: Iterable[str] | None = None):
    view = detection_view(text)
    excluded = exclusions(ignored, whitelist)
    candidates = _propose(view.text, ignored=ignored, whitelist=whitelist)
    found = {}
    for item in candidates:
        for match in re.finditer(re.escape(item['original']), view.text):
            candidate = _restore_valid_candidate(text, item, match, excluded)
            if candidate is None or candidate['original'] in found:
                continue
            found[candidate['original']] = candidate
    return list(found.values())


# replacements 유효성 및 제약조건을 검증함
def validate_replacements(items):
    if not items:
        return
    originals = [item['original'] for item in items]
    if len(set(originals)) != len(originals):
        raise ValueError('중복된 원문 항목이 있습니다.')
    for item in items:
        old, new = item['original'], item['replacement']
        if not old.strip() or not new.strip() or old == new or '\n' in old + new or '\r' in old + new:
            raise ValueError('원문과 다른 한 줄의 대체값을 입력하세요.')
        if len(old) != len(new):
            raise ValueError('서식 유지 모드에서는 원문과 대체값의 글자 수를 맞추세요.')
        validate_format(old, new)
        if any(other in new for other in originals):
            raise ValueError('대체값에 원본 개인정보가 포함되어 있습니다.')
        if any(other != old and (old in other or other in old) for other in originals):
            raise ValueError('겹치는 원문 항목을 하나로 정리하세요.')
