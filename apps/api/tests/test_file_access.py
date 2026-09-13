# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_file_access.py
# 경로: apps/api/tests/test_file_access.py
# 목적: 파일 접근 보안 경계 및 디렉터리 순회 방지 기능을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file
from synthetic_api.routes.v1.files import router


# download env 작업을 수행함
@pytest.fixture
def download_env(tmp_path, monkeypatch):
    outputs = tmp_path / 'outputs'
    outputs.mkdir()
    (outputs / 'result.csv').write_text('synthetic', encoding='utf-8')
    (tmp_path / 'private.txt').write_text('private', encoding='utf-8')
    monkeypatch.setattr(settings, 'ROOT_DIR', tmp_path)
    monkeypatch.setattr(settings, 'OUTPUT_DIR', outputs)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), tmp_path, outputs


# output download remains compatible 기능의 정상 동작 및 제약조건을 테스트함
def test_output_download_remains_compatible(download_env):
    client, _, outputs = download_env
    for path in ('outputs/result.csv', str(outputs / 'result.csv')):
        response = client.get('/files/download', params={'path': path})
        assert response.status_code == 200
        assert response.text == 'synthetic'
        check = client.head('/files/download', params={'path': path})
        assert check.status_code == 200
        assert check.headers['content-length'] == str((outputs / 'result.csv').stat().st_size)


# private 파일 목록 and traversal are rejected 기능의 정상 동작 및 제약조건을 테스트함
def test_private_files_and_traversal_are_rejected(download_env):
    client, root, outputs = download_env
    for path in ('private.txt', 'outputs/../private.txt', str(root / 'private.txt')):
        response = client.get('/files/download', params={'path': path})
        assert response.status_code == 403
        assert 'private' not in response.text
    assert client.get('/files/download', params={'path': str(outputs)}).status_code == 404
    missing = client.get('/files/download', params={'path': 'outputs/missing.csv'})
    assert missing.status_code == 404
    assert '다운로드 파일을 찾을 수 없습니다' in missing.text
    missing_check = client.head('/files/download', params={'path': 'outputs/missing.csv'})
    assert missing_check.status_code == 404


# resolved link outside output is rejected 기능의 정상 동작 및 제약조건을 테스트함
def test_resolved_link_outside_output_is_rejected(tmp_path, monkeypatch):
    outputs = tmp_path / 'outputs'
    outputs.mkdir()
    outside = tmp_path / 'private.txt'
    outside.write_text('private')
    link = outputs / 'result.csv'
    original = Path.resolve

    # Exercise link resolution on Windows without requiring symlink privileges.
    monkeypatch.setattr(Path, 'resolve', lambda self, *a, **kw:
                        outside if self == link else original(self, *a, **kw))
    with pytest.raises(HTTPException) as error:
        confined_file(link, outputs)
    assert error.value.status_code == 403
