# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pseudonym_api.py
# 경로: apps/api/tests/test_pseudonym_api.py
# 목적: 개인식별정보(PII) 탐지 및 가명화 처리 API를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import pytest
import io
from fastapi.testclient import TestClient
from synthetic_api.main import app
from synthetic_api.core.config import settings

client = TestClient(app)


# isolated storage 작업을 수행함
@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    uploads, outputs = tmp_path / 'uploads', tmp_path / 'outputs'
    uploads.mkdir()
    outputs.mkdir()
    monkeypatch.setattr(settings, 'UPLOAD_DIR', uploads)
    monkeypatch.setattr(settings, 'OUTPUT_DIR', outputs)

# 가명화 처리 flow 기능의 정상 동작 및 제약조건을 테스트함
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

    # Check that phone is smart-masked with format preserved (e.g. 010-****-5678)
    first_row = data["pseudonymized_preview"][0]
    assert first_row["phone"] == "010-****-5678"

    # Check that email is hashed (64-char sha256 hex)
    assert len(first_row["email"]) == 64

    # Check that name is not equal to original 홍길동
    assert first_row["name"] != "홍길동"

    history = client.get('/api/v1/datasets/pseudonymize/history').json()
    assert len(history) == 1
    latest = history[0]
    assert latest['original_file'] == uploaded_filename
    assert latest['pii_summary']['phone']['action'] == 'mask'
    download = client.get(latest['download_url'])
    assert download.status_code == 200
    exported = download.content.decode('utf-8-sig')
    assert '***' in exported and '홍길동' not in exported

# 가명화 처리 엑셀(XLSX) format 기능의 정상 동작 및 제약조건을 테스트함
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
