from pathlib import Path

from fastapi.testclient import TestClient

from synthetic_api.main import app
from synthetic_api.core.config import settings



client = TestClient(app)



def test_health():

    res = client.get("/health")

    assert res.status_code == 200

    assert res.json()["status"] == "healthy"



def test_jobs_list():
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_job_distributions_not_found():
    res = client.get("/api/v1/jobs/non-existent-job-id/distributions")
    assert res.status_code == 404


def test_src_layout_resolves_workspace_paths():
    root = Path(__file__).resolve().parents[3]
    assert settings.ROOT_DIR == root
    assert settings.UPLOAD_DIR == root / "storage/uploads"
    assert settings.OUTPUT_DIR == root / "storage/outputs"
    assert (root / "storage/templates/원본데이터 명세서.hwpx").exists()
    assert "/api/v1/synthesis/start" in app.openapi()["paths"]


def test_delete_selected_history_endpoint():
    res = client.post("/api/v1/history/delete-selected", json={"items": [{"type": "pseudo", "id": "test-id-123"}]})
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_system_docs_endpoints():
    res = client.get("/api/v1/system/docs")
    assert res.status_code == 200
    data = res.json()
    assert "docs" in data
    assert len(data["docs"]) > 0
    assert any(d["id"] == "개발이력.md" for d in data["docs"])

    doc_res = client.get("/api/v1/system/doc", params={"path": "개발이력.md"})
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert "content" in doc_data
    assert len(doc_data["content"]) > 0

    bad_res = client.get("/api/v1/system/doc", params={"path": "../../../windows/system32/cmd.exe"})
    assert bad_res.status_code in (400, 404)



