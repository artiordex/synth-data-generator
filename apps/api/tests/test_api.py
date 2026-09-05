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

