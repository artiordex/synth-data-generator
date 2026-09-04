from unittest.mock import patch

from fastapi.testclient import TestClient
from synthetic_api.main import app
from synthetic_api.domain.models.job import JobStatus
from synthetic_api.application.services.synthesis_service import SynthesisService


def test_notebook_options_reach_pipeline_job():
    with patch.object(SynthesisService, 'create_job', return_value=JobStatus(id='test-options')), \
         patch.object(SynthesisService, 'start_pipeline_async') as start:
        response = TestClient(app).post('/api/v1/synthesis/start', json={
            'file_name': 'data.csv', 'model_type': 'ctgan', 'pac': 10, 'seed': 123,
            'sampling_batch_size': 800, 'max_sampling_attempts': 12, 'enable_gpu': False,
            'preserve_null_columns': ['income'], 'evaluation_excluded_columns': ['month_sin', 'month_cos']})
    assert response.status_code == 200
    request = start.call_args.args[1]
    assert request.pac == 10 and request.seed == 123
    assert request.max_sampling_attempts == 12
    assert request.evaluation_excluded_columns == ['month_sin', 'month_cos']
    assert request.preserve_null_columns == ['income']


def test_invalid_sampling_budget_is_rejected_before_job_creation():
    response = TestClient(app).post('/api/v1/synthesis/start', json={
        'file_name': 'data.csv', 'max_sampling_attempts': 0})
    assert response.status_code == 422
