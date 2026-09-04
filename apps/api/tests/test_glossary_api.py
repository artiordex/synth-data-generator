from fastapi.testclient import TestClient
from synthetic_api.main import app

client = TestClient(app)

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

def test_glossary_search():
    # Search for RAG
    response = client.get("/api/v1/glossary?q=RAG")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    # Every item returned should contain rag in name or description
    for item in data["items"]:
        assert "rag" in item["name"].lower() or "rag" in item["description"].lower()

def test_glossary_category_filter():
    category = "보안 & 프라이버시"
    response = client.get("/api/v1/glossary", params={"category": category})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    for item in data["items"]:
        assert item["category"] == category

def test_glossary_initial_filter():
    response = client.get("/api/v1/glossary?initial=ㄱ")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    for item in data["items"]:
        assert item["initial"] == "ㄱ"

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

def test_glossary_not_found():
    res = client.get("/api/v1/glossary/non-existent-id-99999")
    assert res.status_code == 404
