# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_glossary_api.py
# 경로: apps/api/tests/test_glossary_api.py
# 목적: 표준 용어사전 조회 및 검색 API 엔드포인트를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from fastapi.testclient import TestClient
from synthetic_api.main import app

client = TestClient(app)

# get 용어 사전 list 기능의 정상 동작 및 제약조건을 테스트함
def test_get_glossary_list():
    response = client.get("/api/v1/glossary")
    assert response.status_code == 200
    data = response.json()
    assert "total_count" in data
    assert data["total_count"] >= 349
    assert len(data["items"]) >= 349
    assert "categories" in data
    assert "머신러닝 & 딥러닝" in data["categories"]
    assert "보안 & 프라이버시" in data["categories"]

# 용어 사전 search 기능의 정상 동작 및 제약조건을 테스트함
def test_glossary_search():
    # Search for RAG
    response = client.get("/api/v1/glossary?q=RAG")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    # Every item returned should contain rag in name or description
    for item in data["items"]:
        assert "rag" in item["name"].lower() or "rag" in item["description"].lower()

# 용어 사전 category filter 기능의 정상 동작 및 제약조건을 테스트함
def test_glossary_category_filter():
    category = "보안 & 프라이버시"
    response = client.get("/api/v1/glossary", params={"category": category})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    for item in data["items"]:
        assert item["category"] == category

# 용어 사전 initial filter 기능의 정상 동작 및 제약조건을 테스트함
def test_glossary_initial_filter():
    response = client.get("/api/v1/glossary?initial=ㄱ")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    for item in data["items"]:
        assert item["initial"] == "ㄱ"

# 용어 사전 get item by id 기능의 정상 동작 및 제약조건을 테스트함
def test_glossary_get_item_by_id():
    list_res = client.get("/api/v1/glossary")
    first_item = list_res.json()["items"][0]
    item_id = first_item["id"]

    res = client.get(f"/api/v1/glossary/{item_id}")
    assert res.status_code == 200
    item = res.json()
    assert item["id"] == item_id
    assert item["name"] == first_item["name"]
    assert item["description"] == first_item["description"]

# 용어 사전 not found 기능의 정상 동작 및 제약조건을 테스트함
def test_glossary_not_found():
    res = client.get("/api/v1/glossary/non-existent-id-99999")
    assert res.status_code == 404
