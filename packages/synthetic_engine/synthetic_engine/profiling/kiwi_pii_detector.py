# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: kiwi_pii_detector.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/kiwi_pii_detector.py
# 목적: Kiwi 형태소 분석기 기반 비정형 텍스트 내 개인정보를 검출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Context-gated Korean names. Morphology alone never establishes identity."""
from __future__ import annotations

import re
from threading import Lock
from typing import Any, Iterable

from ..privacy.domain_whitelist import exclusions, normalize

_KIWI_INSTANCE = None
_KIWI_READY = False
_KIWI_LOCK = Lock()

ORGANIZATION_SUFFIXES = (
    '은행', '뱅크', '카드', '증권', '보험', '생명', '화재', '캐피탈', '금고', '저축은행',
    '신협', '농협', '수협', '회사', '주식회사', '기업', '그룹', '법인',
    '병원', '의원', '약국', '보건소', '클리닉', '센터', '처', '청', '재단', '연구소',
    '연구원', '공사', '공단', '본부', '지사', '지점', '대학교', '학교', '협회', '학회',
)
NAME_PREFIX_WORDS = (
    '성명', '이름', '담당자', '환자명', '환자', '수검자', '피험자', '작성자', '확인자',
    '승인자', '수취인', '예금주', '의뢰인', '대표자', '연구책임자', '보호자', '검토자',
)
NAME_POSTFIXES = (
    '씨', '님', '연구원', '연구책임자', '박사', '교수', '원장', '부장', '과장', '팀장',
    '대리', '사원', '주임', '의사', '약사', '간호사', '주무관', '사무관', '서기관',
    '심사관', '조사관', '위원', '대표', '귀하', '선생님', '대표이사',
)


# alternatives 작업을 수행함
def alternatives(words):
    return '|'.join(re.escape(word) for word in sorted(words, key=len, reverse=True))


# Do not borrow context across paragraph/table-cell line boundaries.
_PREFIX = re.compile(rf'(?<![가-힣\w])(?:{alternatives(NAME_PREFIX_WORDS)})[^\S\r\n]*[:：][^\S\r\n]*(?P<name>[가-힣]{{2,4}})(?![가-힣])')
_POSTFIX = re.compile(rf'(?<![가-힣\w])(?P<name>[가-힣]{{2,4}}?)[^\S\r\n]*(?:{alternatives(NAME_POSTFIXES)})(?=$|[^가-힣\w]|(?:은|는|이|가|께|의|에게|을|를)(?=$|\s))')
_ORG = re.compile(rf'(?<![가-힣\w])[가-힣A-Za-z0-9·&]+?(?:{alternatives(ORGANIZATION_SUFFIXES)})(?=$|[^가-힣\w]|(?:은|는|이|가|의|에서|으로|와|과)(?=$|\s))')
_LOCATION = re.compile(r'(?<![가-힣\w])[가-힣]{2,}(?:특별시|광역시|특별자치시|특별자치도)(?![가-힣])')


# kiwi 정보를 조회하여 반환함
def get_kiwi():
    """Initialize once, including unavailable state; context rules work offline."""
    global _KIWI_INSTANCE, _KIWI_READY
    if not _KIWI_READY:
        with _KIWI_LOCK:
            if not _KIWI_READY:
                try:
                    from kiwipiepy import Kiwi
                    _KIWI_INSTANCE = Kiwi(num_workers=1)
                except (ImportError, RuntimeError, OSError):
                    _KIWI_INSTANCE = None
                _KIWI_READY = True
    return _KIWI_INSTANCE


# organization 여부 및 유효성을 판별함
def is_organization(word: str) -> bool:
    return word.strip().endswith(ORGANIZATION_SUFFIXES)


# 감지 korean named 엔티티 목록 작업을 수행함
def detect_korean_named_entities(text: str, *, ignored: Iterable[str] = (),
                                whitelist: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return []
    excluded = exclusions(ignored, whitelist)
    entities = []
    organizations = [(match.start(), match.end()) for match in _ORG.finditer(text)]
    for pattern, kind in ((_ORG, 'ORGANIZATION'), (_LOCATION, 'LOCATION')):
        for match in pattern.finditer(text):
            if normalize(match.group()) not in excluded:
                entities.append({'entity': match.group(), 'type': kind, 'start': match.start(),
                                 'end': match.end(), 'confidence': 0.9})

    candidates = {}
    for pattern, reason in ((_PREFIX, 'key_value'), (_POSTFIX, 'title')):
        for match in pattern.finditer(text):
            start, end = match.span('name')
            word = match.group('name')
            if normalize(word) in excluded or is_organization(word):
                continue
            if any(start < right and end > left for left, right in organizations):
                continue
            candidates.setdefault((start, end), (word, reason))

    # NNP is never enough without context. Keep NNG evidence from alternative
    # analyses even when the first segmentation labels a word as NNP.
    analyses = []
    if candidates:
        kiwi = get_kiwi()
        if kiwi is not None:
            try:
                analyses = kiwi.analyze(text, top_n=3)
            except (RuntimeError, ValueError):
                analyses = []
    for (start, end), (word, reason) in candidates.items():
        tags = {token.tag for tokens, _score in analyses for token in tokens
                if token.start < end and token.start + token.len > start}
        entities.append({'entity': word, 'type': 'PERSON_NAME', 'start': start, 'end': end,
                         'confidence': 0.95 if reason == 'key_value' else 0.9,
                         'reason': reason, 'morphology': 'NNG' if 'NNG' in tags else 'NNP' if 'NNP' in tags else 'context_only'})
    return sorted(entities, key=lambda item: (item['start'], item['end']))
