import pytest
from fastapi.testclient import TestClient
from synthetic_api.main import app

client = TestClient(app)

def test_dummy_domains_endpoint():
    res = client.get("/api/v1/dummy/domains")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    assert data["total_count"] >= 100
    assert len(data["categories"]) >= 7

def test_dummy_templates_endpoint():
    res = client.get("/api/v1/dummy/templates")
    assert res.status_code == 200
    data = res.json()
    assert len(data["templates"]) >= 6

def test_dummy_infer_column_endpoint():
    res = client.post("/api/v1/dummy/infer-column", json={"column_name": "휴대폰번호"})
    assert res.status_code == 200
    data = res.json()
    assert data["inferred_domain"]["id"] == "phone_mobile"

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
