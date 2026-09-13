# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_text_format_rules.py
# 경로: packages/synthetic_engine/tests/test_text_format_rules.py
# 목적: 정형 개인정보 서식 규칙 유효성 및 치환을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pytest

from synthetic_engine.privacy.text_format_rules import (
    detection_view, restore_format, validate_format,
)
from synthetic_engine.privacy.document_replacements import propose, validate_replacements


# detection offsets and original whitespace are lossless 기능의 정상 동작 및 제약조건을 테스트함
def test_detection_offsets_and_original_whitespace_are_lossless():
    original = '성명：홍길동\t전화：０１０－１２３４－５６７８\r\n주소\u3000서울\u00a0송파'
    view = detection_view(original)
    assert len(view.text) == len(original)
    assert '전화:010-1234-5678' in view.text
    assert view.original == original
    assert '\r\n' in view.text


# proposal restores fullwidth phone and separators 기능의 정상 동작 및 제약조건을 테스트함
def test_proposal_restores_fullwidth_phone_and_separators():
    original = '０１０－１２３４－５６７８'
    items = propose('전화：' + original)
    phone = next(item for item in items if item['kind'] == '전화번호')
    assert phone['original'] == original
    assert phone['replacement'].startswith('０１０－')
    assert phone['replacement'][8] == '－'
    validate_replacements(items)


# restore preserves every whitespace codepoint 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('space', [' ', '  ', '\t', '\u00a0', '\u3000', '\r\n'])
def test_restore_preserves_every_whitespace_codepoint(space):
    old = 'AB' + space + '12'
    new = restore_format(old, 'CD' + ' ' * len(space) + '34')
    assert new == 'CD' + space + '34'
    validate_format(old, new)


# manual replacements cannot change format 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize(('old', 'new'), [
    ('AB-12', 'CD 34'), ('AB 12', 'CD-34'), ('AB\t12', 'CD 34'),
    ('AB12', 'cd34'), ('AB12', 'CDxy'), ('１２', '34'),
    ('AB', 'A\u200b'), ('(AB)', '[CD]'),
])
def test_manual_replacements_cannot_change_format(old, new):
    with pytest.raises(ValueError, match='FORMAT_'):
        validate_format(old, new)


# normalization does not join jamo or expand ligatures 기능의 정상 동작 및 제약조건을 테스트함
def test_normalization_does_not_join_jamo_or_expand_ligatures():
    text = '\u1100\u1161\ufb03'
    assert detection_view(text).text == text


# multiline native edit is explicitly rejected 기능의 정상 동작 및 제약조건을 테스트함
def test_multiline_native_edit_is_explicitly_rejected():
    with pytest.raises(ValueError):
        validate_replacements([{'original': '서울\n주소', 'replacement': '가상\n지역'}])


# invalid auto candidate is skipped without blocking inspection 기능의 정상 동작 및 제약조건을 테스트함
def test_invalid_auto_candidate_is_skipped_without_blocking_inspection(monkeypatch):
    from synthetic_engine.privacy import document_replacements

    # broken candidate 작업을 수행함
    def broken_candidate(*_args, **_kwargs):
        return [
            {'original': '1234567890123', 'replacement': '12345678901**', 'kind': '테스트', 'count': 1},
            {'original': '010-1234-5678', 'replacement': '010-8765-4321', 'kind': '전화번호', 'count': 1},
        ]

    monkeypatch.setattr(document_replacements, '_propose', broken_candidate)
    items = document_replacements.propose('번호 1234567890123, 전화 010-1234-5678')

    assert [item['original'] for item in items] == ['010-1234-5678']
    with pytest.raises(ValueError, match='FORMAT_DIGIT'):
        validate_replacements([{'original': '1234567890123', 'replacement': '12345678901**'}])
