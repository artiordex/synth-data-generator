import io
import pytest
from synthetic_api.core.config import settings
from fastapi.testclient import TestClient
from synthetic_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    uploads, outputs = tmp_path / 'uploads', tmp_path / 'outputs'
    uploads.mkdir()
    outputs.mkdir()
    monkeypatch.setattr(settings, 'UPLOAD_DIR', uploads)
    monkeypatch.setattr(settings, 'OUTPUT_DIR', outputs)

def test_pseudonym_history():
    # 1. Upload sample
    csv_data = "name,email\n홍길동,hong@test.com\n이순신,lee@test.com\n"
    files = {"file": ("test_hist.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    assert upload_res.status_code == 200
    fname = upload_res.json()["filename"]

    # 2. Pseudonymize
    payload = {
        "file_name": fname,
        "pii_actions": {"name": "mask", "email": "hash"},
        "export_format": "csv"
    }
    p_res = client.post("/api/v1/datasets/pseudonymize", json=payload)
    assert p_res.status_code == 200

    # 3. Check history
    h_res = client.get("/api/v1/datasets/pseudonymize/history")
    assert h_res.status_code == 200
    history = h_res.json()
    assert isinstance(history, list)
    assert len(history) > 0
    latest = history[0]
    assert "file_name" in latest
    assert "download_url" in latest
    assert latest["original_file"] == fname
    assert latest['pii_summary']['name']['action'] == 'mask'
    download = client.get(latest['download_url'])
    assert download.status_code == 200
    assert '***' in download.content.decode('utf-8-sig')
    assert '홍길동' not in download.content.decode('utf-8-sig')

def test_dummy_history():
    # 1. Generate dummy data
    payload = {
        "table_name": "test_hist_orders",
        "columns": [
            {"name": "order_id", "domain_id": "주문번호"},
            {"name": "user_name", "domain_id": "고객명"}
        ],
        "target_rows": 5,
        "export_format": "csv"
    }
    g_res = client.post("/api/v1/dummy/generate", json=payload)
    assert g_res.status_code == 200

    # 2. Check history
    h_res = client.get("/api/v1/dummy/history")
    assert h_res.status_code == 200
    history = h_res.json()
    assert isinstance(history, list)
    assert len(history) > 0
    latest = history[0]
    assert latest["table_name"] == "test_hist_orders"
    assert "download_url" in latest
    assert latest["rows_generated"] == 5
    assert latest['columns_count'] == 2
    assert client.get(latest['download_url']).status_code == 200

def test_jobs_history():
    h_res = client.get("/api/v1/jobs")
    assert h_res.status_code == 200
    assert isinstance(h_res.json(), list)
