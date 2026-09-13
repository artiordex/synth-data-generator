# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_resources.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_resources.py
# 목적: 문서 첨부 이미지 및 바이너리 리소스 관리를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Binary retention, interning, and metadata behavior."""

from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest

from synthetic_engine.document_conversion.core.resources import ResourceStore


# repeated resource uses one binary instance 기능의 정상 동작 및 제약조건을 테스트함
def test_repeated_resource_uses_one_binary_instance():
    store = ResourceStore()
    original = bytes(range(256)) * 8
    digest = store.add(original, "image/png")
    assert digest == sha256(original).hexdigest()
    for _ in range(10):
        duplicate = bytes(bytearray(original))
        assert store.intern(duplicate) is original
    assert len(store) == 1
    assert store.total_bytes == len(original)
    assert store.get(digest) == original
    assert store.get_metadata(digest).mime_types == ("image/png",)


# mime disagreement retains claims without mutating bytes 기능의 정상 동작 및 제약조건을 테스트함
def test_mime_disagreement_retains_claims_without_mutating_bytes():
    store = ResourceStore()
    digest = store.add(b"payload")
    store.add(b"payload", "image/png")
    store.add(b"payload", "IMAGE/JPEG")
    metadata = store.get_metadata(digest)
    assert metadata.mime_types == ("image/jpeg", "image/png")
    assert store.get(digest) == b"payload"
    with pytest.raises(FrozenInstanceError):
        metadata.size_bytes = 0


# missing resource is not silently substituted 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_resource_is_not_silently_substituted():
    with pytest.raises(KeyError):
        ResourceStore().get("missing")


# mutable data rejected and empty resources preserved 기능의 정상 동작 및 제약조건을 테스트함
def test_mutable_data_rejected_and_empty_resources_preserved():
    store = ResourceStore()
    with pytest.raises(TypeError):
        store.add(bytearray(b"mutable"))
    digest = store.add(b"")
    assert digest in store
    assert store.digests() == (digest,)
    assert store.get(digest) == b""


# stores are document scoped 기능의 정상 동작 및 제약조건을 테스트함
def test_stores_are_document_scoped():
    first, second = ResourceStore(), ResourceStore()
    first.add(b"private attachment")
    assert len(second) == 0
