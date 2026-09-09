"""
파일명: document_replacements.py
경로: packages/synthetic_engine/synthetic_engine/privacy/document_replacements.py
목적: 문서 본문에서 명시적인 개인정보 후보를 찾아 대체안을 생성함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
import re
import secrets
import string
from faker import Faker

from .masker import SmartMasker

NAME_PREFIXES = (
    r'이름|성명|담당자|연구원|연구책임자|책임자|작성자|조사자|보고자|확인자|승인자|수검자|'
    r'환자명|환자|피험자|대표자|대표이사|대표|신청인|의뢰인|피평가자|평가자|작업자|관리자|소유자|'
    r'수혜자|진료의|담당의|주임|과장|팀장|부장|처장|원장|교수|박사|심사관|조사관'
)

PATTERNS = {
    '이메일': re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
    '전화번호': re.compile(r'(?<!\d)(?:01[016789]|02|0[3-6][1-5])[- ]?\d{3,4}[- ]?\d{4}(?!\d)'),
    '주민등록번호': re.compile(r'(?<!\d)\d{6}-[1-8]\d{6}(?!\d)'),
    '이름': re.compile(rf'(?:{NAME_PREFIXES})\s*[:：]\s*(?P<value>[가-힣]{{2,4}})(?![가-힣])'),
}

NAME_POSTFIX_PATTERN = re.compile(
    r'(?<![가-힣])(?P<value>[가-힣]{2,4})[^\S\r\n]+(?:연구책임자|책임연구원|수석연구원|선임연구원|연구원|'
    r'대표이사|원장|교수|박사|선생님|선생|의사|약사|간호사|팀장|부장|과장|대리|주임|사원|'
    r'주무관|사무관|서기관|심사관|조사관|위원|귀하|님|씨)(?![가-힣])'
)


def propose(text):
    """문서 텍스트에서 대체 가능한 개인정보 후보를 제안함"""
    found = {}
    fake = Faker('ko_KR')
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            original = match.groupdict().get('value') or match.group()
            cnt = text.count(original)
            if original in found or cnt == 0:
                continue
            if kind == '이름':
                try:
                    from ..profiling.kiwi_pii_detector import NON_PERSON_WORDS, ORGANIZATION_SUFFIXES
                    if original in NON_PERSON_WORDS or any(original.endswith(s) for s in ORGANIZATION_SUFFIXES):
                        continue
                except Exception:
                    pass
                replacement = SmartMasker.mask_name(original)
                if replacement == original or len(replacement) != len(original):
                    if len(original) == 2:
                        replacement = f"{original[0]}*"
                    elif len(original) == 3:
                        replacement = f"{original[0]}*{original[2]}"
                    elif len(original) == 4:
                        replacement = f"{original[0]}**{original[3]}"
                    else:
                        replacement = f"{original[0]}{'*' * (len(original) - 2)}{original[-1]}"
            elif kind == '이메일':
                local, domain = original.split('@')
                replacement = ''.join(secrets.choice(string.ascii_lowercase) for _ in local) + '@' + domain
            else:
                replacement = ''.join(str((int(c) + secrets.randbelow(9) + 1) % 10) if c.isdigit() else c for c in original)
            found[original] = {'original': original, 'replacement': replacement, 'kind': kind, 'count': cnt}

    # 직책/호칭 결합 인명 탐지
    for match in NAME_POSTFIX_PATTERN.finditer(text):
        name = match.group('value')
        cnt = text.count(name)
        try:
            from ..profiling.kiwi_pii_detector import NON_PERSON_WORDS, ORGANIZATION_SUFFIXES
            if name in NON_PERSON_WORDS or any(name.endswith(s) for s in ORGANIZATION_SUFFIXES):
                continue
        except Exception:
            pass
        if name not in found and 2 <= len(name) <= 4 and cnt > 0:
            rep = SmartMasker.mask_name(name)
            if rep == name or len(rep) != len(name):
                rep = f"{name[0]}*{name[-1]}" if len(name) == 3 else f"{name[0]}*"
            found[name] = {'original': name, 'replacement': rep, 'kind': '이름', 'count': cnt}

    # Kiwi 형태소 분석 기반 인명 고정밀 탐지
    try:
        from ..profiling.kiwi_pii_detector import detect_korean_named_entities, NON_PERSON_WORDS, ORGANIZATION_SUFFIXES
        entities = detect_korean_named_entities(text)
        for ent in entities:
            if ent.get('type') == 'PERSON_NAME':
                name = ent.get('entity', '').strip()
                if name in NON_PERSON_WORDS or any(name.endswith(s) for s in ORGANIZATION_SUFFIXES):
                    continue
                cnt = text.count(name)
                if 2 <= len(name) <= 4 and name not in found and cnt > 0:
                    rep = SmartMasker.mask_name(name)
                    if rep == name or len(rep) != len(name):
                        rep = f"{name[0]}*{name[-1]}" if len(name) == 3 else f"{name[0]}*"
                    found[name] = {'original': name, 'replacement': rep, 'kind': '이름', 'count': cnt}
    except Exception:
        pass

    return list(found.values())


def validate_replacements(items):
    """개인정보 대체 후보의 형식과 중복 여부를 검증함"""
    if not items:
        raise ValueError('치환할 개인정보를 하나 이상 지정하세요.')
    originals = [item['original'] for item in items]
    if len(set(originals)) != len(originals):
        raise ValueError('중복된 원문 항목이 있습니다.')
    for item in items:
        old, new = item['original'], item['replacement']
        if not old.strip() or not new.strip() or old == new or '\n' in old + new or '\r' in old + new:
            raise ValueError('원문과 다른 한 줄의 대체값을 입력하세요.')
        if len(old) != len(new):
            raise ValueError('서식 유지 모드에서는 원문과 대체값의 글자 수를 맞추세요.')
        if any(other in new for other in originals):
            raise ValueError('대체값에 원본 개인정보가 포함되어 있습니다.')
        if any(other != old and (old in other or other in old) for other in originals):
            raise ValueError('겹치는 원문 항목을 하나로 정리하세요.')
