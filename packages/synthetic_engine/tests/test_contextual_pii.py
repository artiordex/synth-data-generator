# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_contextual_pii.py
# 경로: packages/synthetic_engine/tests/test_contextual_pii.py
# 목적: 문맥 기반 개인식별정보(PII) 검출 정확도를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import json
from types import SimpleNamespace

import pytest

from synthetic_engine.profiling import kiwi_pii_detector as detector
from synthetic_engine.privacy.document_replacements import propose
from synthetic_engine.privacy.domain_whitelist import load_whitelist
from synthetic_engine.privacy.masker import SmartMasker


# isolated 화이트리스트 작업을 수행함
@pytest.fixture(autouse=True)
def isolated_whitelist(tmp_path, monkeypatch):
    path = tmp_path / 'whitelist.json'
    monkeypatch.setenv('SYNTHETIC_PII_WHITELIST_PATH', str(path))
    return path


# contextual detection and proposals 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('text,names', [
    ('계좌이체 수수료: 우리은행 100-1234-5678, 수취인: 홍길동', {'홍길동'}),
    ('연구책임자: 김철수 박사, 승인자: 남궁민수', {'김철수', '남궁민수'}),
    ('이상반응 발생 보고서 작성일: 2026-09-09', set()),
    ('이체 출금 조사 이상 수수료 보고서 김철수', set()),
    ('성명: 우리은행, 담당자: 신한카드', set()),
    ('김철수 연구원, 남궁민수 교수, 김민 씨, 이수님', {'김철수', '남궁민수', '김민', '이수'}),
    ('우리은행 연구원, 한국연구원, 삼성생명 대표', set()),
    ('홍길동\n연구원', set()),
    ('기관담당자: 홍길동, 이름: 홍길동연구소', set()),
])
def test_contextual_detection_and_proposals(text, names):
    entities = detector.detect_korean_named_entities(text)
    assert {e['entity'] for e in entities if e['type'] == 'PERSON_NAME'} == names
    assert {item['original'] for item in propose(text) if item['kind'] == '이름'} == names
    for entity in entities:
        assert text[entity['start']:entity['end']] == entity['entity']


# organization suffix exclusion 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('word', ['우리은행', '신한카드', '삼성생명', '현대카드', '가상캐피탈', '동부보험', '중앙공단', '한국연구원'])
def test_organization_suffix_exclusion(word):
    assert detector.is_organization(word)
    assert not [e for e in detector.detect_korean_named_entities(f'성명: {word}') if e['type'] == 'PERSON_NAME']
    assert SmartMasker.mask_value(word, pii_type='name') == word


# kiwi alternatives prefer nng without inventing names 기능의 정상 동작 및 제약조건을 테스트함
def test_kiwi_alternatives_prefer_nng_without_inventing_names(monkeypatch):
    class Kiwi:
        # analyze 작업을 수행함
        def analyze(self, text, top_n):
            assert top_n == 3
            start = text.index('이상')
            return [([SimpleNamespace(tag=tag, start=start, len=2)], 0) for tag in ('NNP', 'NNG')]
    monkeypatch.setattr(detector, 'get_kiwi', lambda: Kiwi())
    assert detector.detect_korean_named_entities('이상') == []
    explicit = detector.detect_korean_named_entities('성명: 이상')
    assert explicit[0]['morphology'] == 'NNG'
    assert explicit[0]['reason'] == 'key_value'


# missing kiwi does not enable surname guess 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_kiwi_does_not_enable_surname_guess(monkeypatch):
    monkeypatch.setattr(detector, 'get_kiwi', lambda: None)
    assert detector.detect_korean_named_entities('이체 김철수') == []
    assert detector.detect_korean_named_entities('승인자: 남궁민수')[0]['entity'] == '남궁민수'


# masking uses 스팬 목록 not global string replace 기능의 정상 동작 및 제약조건을 테스트함
def test_masking_uses_spans_not_global_string_replace():
    text = '이상반응, 성명: 이상, 수취인: 홍길동. 우리은행 수수료'
    assert SmartMasker.mask_full_text(text) == '이상반응, 성명: 이*, 수취인: 홍*동. 우리은행 수수료'
    # Native replacement is global: ambiguous repeated spelling needs manual review.
    assert '이상' not in {item['original'] for item in propose(text)}


# unknown structured value is not generically masked 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('value', ['이체', '출금', '수수료', '보고서', '우리은행', '신한카드'])
def test_unknown_structured_value_is_not_generically_masked(value):
    assert SmartMasker.mask_value(value) == value


# domain 화이트리스트 reloads without restart 기능의 정상 동작 및 제약조건을 테스트함
def test_domain_whitelist_reloads_without_restart(isolated_whitelist):
    path = isolated_whitelist
    path.write_text(json.dumps({'words': ['홍길동']}), encoding='utf-8')
    text = '수취인: 홍길동, 승인자: 김철수'
    assert {item['original'] for item in propose(text)} == {'김철수'}
    assert SmartMasker.mask_full_text(text) == '수취인: 홍길동, 승인자: 김*수'
    path.write_text(json.dumps(['홍길동', '김철수']), encoding='utf-8')
    assert propose(text) == []
    assert load_whitelist() == {'홍길동', '김철수'}


# invalid 화이트리스트 does not silently disappear 기능의 정상 동작 및 제약조건을 테스트함
def test_invalid_whitelist_does_not_silently_disappear(isolated_whitelist):
    isolated_whitelist.write_text('{"words": "invalid"}', encoding='utf-8')
    with pytest.raises(ValueError):
        propose('수취인: 홍길동')


# 세션 ignored candidates and masking 기능의 정상 동작 및 제약조건을 테스트함
def test_session_ignored_candidates_and_masking():
    text = '수취인: 홍길동, 승인자: 김철수'
    assert {item['original'] for item in propose(text, ignored={'홍길동'})} == {'김철수'}
    assert SmartMasker.mask_full_text(text, ignored={'홍길동'}) == '수취인: 홍길동, 승인자: 김*수'
