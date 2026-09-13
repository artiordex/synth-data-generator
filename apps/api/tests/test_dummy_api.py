# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_dummy_api.py
# 경로: apps/api/tests/test_dummy_api.py
# 목적: 행안부 공통표준 도메인 기반 더미데이터 생성 API를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import pytest
from fastapi.testclient import TestClient
from synthetic_api.main import app
from synthetic_api.core.config import settings

client = TestClient(app)


# isolated storage 작업을 수행함
@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    output = tmp_path / 'outputs'
    output.mkdir()
    monkeypatch.setattr(settings, 'OUTPUT_DIR', output)

# 더미 데이터 domains endpoint 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_domains_endpoint():
    res = client.get("/api/v1/dummy/domains")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    assert data["total_count"] >= 100
    assert len(data["categories"]) >= 7

# 더미 데이터 templates endpoint 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_templates_endpoint():
    res = client.get("/api/v1/dummy/templates")
    assert res.status_code == 200
    data = res.json()
    assert len(data["templates"]) >= 6

# 더미 데이터 infer 컬럼 endpoint 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_infer_column_endpoint():
    res = client.post("/api/v1/dummy/infer-column", json={"column_name": "휴대폰번호"})
    assert res.status_code == 200
    data = res.json()
    assert data["inferred_domain"]["id"] == "phone_mobile"

# 더미 데이터 generate endpoint 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_generate_endpoint():
    payload = {
        "table_name": "test_members",
        "columns": [
            {"name": "user_id", "domain_id": "user_id"},
            {"name": "user_name", "domain_id": "korean_name"},
            {"name": "phone", "domain_id": "phone_mobile"}
        ],
        "target_rows": 20,
        "export_format": "sql"
    }
    res = client.post("/api/v1/dummy/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["rows_generated"] == 20
    assert len(data["preview"]) > 0
    assert data["file_name"].endswith(".sql")
    history = client.get('/api/v1/dummy/history').json()
    assert len(history) == 1
    assert history[0]['table_name'] == 'test_members'
    assert history[0]['rows_generated'] == 20
    assert history[0]['columns_count'] == 3
    assert client.get(history[0]['download_url']).status_code == 200
