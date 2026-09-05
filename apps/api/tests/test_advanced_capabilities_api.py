import pandas as pd
from fastapi.testclient import TestClient

from synthetic_api.core.config import settings
from synthetic_api.main import app


def test_schema_import_and_pseudonym_privacy_metrics(tmp_path, monkeypatch):
    uploads, outputs = tmp_path / "uploads", tmp_path / "outputs"
    uploads.mkdir(); outputs.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(settings, "OUTPUT_DIR", outputs)
    client = TestClient(app)

    imported = client.post("/api/v1/dummy/import-schema", json={
        "source_type": "ddl",
        "content": "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(100) UNIQUE NOT NULL);",
    })
    assert imported.status_code == 200
    assert imported.json()["tables"][0]["columns"][0]["primary_key"] is True

    multi = client.post("/api/v1/dummy/import-schema", json={
        "source_type": "ddl",
        "content": "CREATE TABLE parents (id INTEGER PRIMARY KEY); CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER, FOREIGN KEY (parent_id) REFERENCES parents(id));",
    }).json()
    generated = client.post("/api/v1/dummy/generate-schema", json={
        "schema_definition": multi, "target_rows": 10, "scenario": "normal"})
    assert generated.status_code == 200
    assert generated.json()["relationships"][0]["orphan_count"] == 0

    pd.DataFrame({"name": ["Kim", "Kim", "Lee", "Lee"], "age": [20, 20, 30, 30],
                  "diagnosis": ["A", "B", "A", "B"]}).to_csv(uploads / "people.csv", index=False)
    payload = {"file_name": "people.csv", "pii_actions": {"name": "token"},
               "project_id": "study-1", "quasi_identifiers": ["age"],
               "sensitive_columns": ["diagnosis"], "k_threshold": 2}
    response = client.post("/api/v1/datasets/pseudonymize", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["privacy_metrics"]["k"] == 2
    assert body["pseudonymized_preview"][0]["name"] == body["pseudonymized_preview"][1]["name"]

    comparison = client.post("/api/v1/synthesis/compare-models", json={
        "file_name": "people.csv", "candidates": ["statistical"], "sample_rows": 50})
    assert comparison.status_code == 200
    assert comparison.json()["recommended_model"] == "statistical"


def test_relational_and_time_series_generation(tmp_path, monkeypatch):
    uploads, outputs = tmp_path / "uploads", tmp_path / "outputs"
    uploads.mkdir(); outputs.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(settings, "OUTPUT_DIR", outputs)
    client = TestClient(app)

    pd.DataFrame({"user_id": [1, 2], "segment": ["A", "B"]}).to_csv(uploads / "users.csv", index=False)
    pd.DataFrame({"order_id": [10, 11, 12], "user_id": [1, 1, 2], "amount": [5, 8, 9]}).to_csv(uploads / "orders.csv", index=False)
    request = {"file_names": ["users.csv", "orders.csv"], "model_type": "turbo", "scale": 1.0,
               "primary_keys": {"users": "user_id", "orders": "order_id"},
               "relationships": [{"parent_table": "users", "child_table": "orders",
                                   "parent_key": "user_id", "child_key": "user_id"}]}
    response = client.post("/api/v1/relational/generate", json=request)
    assert response.status_code == 200
    assert response.json()["relationships"][0]["orphan_count"] == 0

    pd.DataFrame({"member": [1, 1, 2, 2], "date": ["2024-01-01", "2024-01-03", "2024-02-01", "2024-02-04"],
                  "value": [1, 2, 10, 12]}).to_csv(uploads / "panel.csv", index=False)
    response = client.post("/api/v1/time-series/generate", json={"file_name": "panel.csv", "entity_column": "member",
                                                                  "time_column": "date", "target_entities": 3})
    assert response.status_code == 200
    assert response.json()["entities"] == 3
