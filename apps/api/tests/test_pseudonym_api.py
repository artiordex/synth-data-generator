import pytest
import io
from fastapi.testclient import TestClient
from synthetic_api.main import app

client = TestClient(app)

def test_pseudonymize_flow():
    # 1. Upload sample CSV with PII
    csv_data = (
        "name,phone,email,age\n"
        "홍길동,010-1234-5678,hong@test.com,30\n"
        "김철수,010-9876-5432,kim@test.com,40\n"
        "이영희,010-5555-6666,lee@test.com,25\n"
    )
    files = {"file": ("test_pii_sample.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    assert upload_res.status_code == 200
    uploaded_filename = upload_res.json()["filename"]

    # 2. Call pseudonymize endpoint
    payload = {
        "file_name": uploaded_filename,
        "pii_actions": {
            "name": "faker",
            "phone": "mask",
            "email": "hash"
        },
        "export_format": "csv"
    }
    res = client.post("/api/v1/datasets/pseudonymize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["rows_count"] == 3
    assert len(data["pseudonymized_preview"]) == 3

    # Check that phone is masked with ***
    first_row = data["pseudonymized_preview"][0]
    assert first_row["phone"] == "***"

    # Check that email is hashed (64-char sha256 hex)
    assert len(first_row["email"]) == 64

    # Check that name is not equal to original 홍길동
    assert first_row["name"] != "홍길동"

def test_pseudonymize_xlsx_format():
    csv_data = "name,amount\n홍길동,1000\n"
    files = {"file": ("test_xlsx_sample.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    uploaded_filename = upload_res.json()["filename"]

    payload = {
        "file_name": uploaded_filename,
        "pii_actions": {"name": "mask"},
        "export_format": "xlsx"
    }
    res = client.post("/api/v1/datasets/pseudonymize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["file_name"].endswith(".xlsx")
