import pytest

from fastapi.testclient import TestClient

from synthetic_api.main import app



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

