import io
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from synthetic_api.main import app
from synthetic_api.core.config import settings
from synthetic_api.domain.models.job import SynthesisRequest
from synthetic_api.infrastructure.db.session import Base
from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository
from synthetic_api.application.services import batch_service, synthesis_service
from synthetic_api.application.services.batch_service import BatchService


@pytest.fixture
def batch_env(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "jobs.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(batch_service, 'SessionLocal', sessions)
    monkeypatch.setattr(synthesis_service, 'SessionLocal', sessions)
    submitted = []
    monkeypatch.setattr(batch_service, '_WORKER', SimpleNamespace(submit=lambda *args: submitted.append(args)))
    uploads, outputs = tmp_path / 'uploads', tmp_path / 'outputs'
    uploads.mkdir(); outputs.mkdir()
    monkeypatch.setattr(settings, 'UPLOAD_DIR', uploads)
    monkeypatch.setattr(settings, 'OUTPUT_DIR', outputs)
    yield SimpleNamespace(client=TestClient(app), uploads=uploads, outputs=outputs,
                          sessions=sessions, submitted=submitted)
    synthesis_service.CANCEL_FLAGS.clear()
    engine.dispose()


def upload_files(env, count=20):
    return env.client.post('/api/v1/datasets/upload-batch', files=[
        ('files', ('same.csv', f'x,y\n{i},1\n{i+1},2\n'.encode(), 'text/csv')) for i in range(count)])


def test_uploads_twenty_same_names_without_overwrite_and_rejects_twenty_one(batch_env):
    response = upload_files(batch_env)
    assert response.status_code == 200
    files = response.json()['files']
    assert len(files) == 20 and all(not f['error'] for f in files)
    assert len({f['filename'] for f in files}) == 20
    assert all(f['original_filename'] == 'same.csv' for f in files)
    assert len({(batch_env.uploads / f['filename']).read_bytes() for f in files}) == 20
    assert upload_files(batch_env, 21).status_code == 422
    assert len(list(batch_env.uploads.iterdir())) == 20


def test_bad_upload_does_not_hide_successful_files(batch_env):
    result = batch_env.client.post('/api/v1/datasets/upload-batch', files=[
        ('files', ('bad.csv', b'', 'text/csv')),
        ('files', ('good.csv', b'x,y\n1,2\n', 'text/csv'))]).json()['files']
    assert result[0]['error'] and result[1]['profile']['row_count'] == 1


def test_twenty_jobs_continue_after_failure_and_package_results(batch_env, monkeypatch):
    uploaded = upload_files(batch_env).json()['files']
    requests = [{'file_name': f['filename'], 'original_filename': f'original-{i}.csv',
                 'target_rows': 4} for i, f in enumerate(uploaded)]
    result = batch_env.client.post('/api/v1/batches', json={'requests': requests})
    assert result.status_code == 200
    batch = result.json()
    assert batch['total'] == 20 and batch['status'] == 'pending'
    assert len(batch_env.submitted) == 1  # one coordinator, not twenty training threads
    executed = []
    def run(job_id, request):
        executed.append(request.original_filename)
        if request.original_filename == 'original-5.csv':
            raise RuntimeError('intentional file failure')
        target = batch_env.outputs / f'{job_id}.zip'
        with ZipFile(target, 'w') as archive:
            archive.writestr('output.csv', 'x\n42\n')
        with batch_env.sessions() as db:
            repo = JobRepository(db)
            job = repo.get_by_id(job_id)
            job.status, job.progress, job.package_zip = 'completed', 100, str(target)
            repo.save(job)
    monkeypatch.setattr(synthesis_service.SynthesisService, '_run_pipeline', run)
    BatchService._run_batch(batch['id'])
    final = batch_env.client.get(f"/api/v1/batches/{batch['id']}").json()
    assert len(executed) == 20 and executed[-1] == 'original-19.csv'
    assert final['status'] == 'completed_with_errors'
    assert final['completed'] == 19 and final['failed'] == 1 and final['progress'] == 100
    with ZipFile(final['package_zip']) as archive:
        assert len([n for n in archive.namelist() if n.endswith('.zip')]) == 19
        manifest = json.loads(archive.read('처리결과.json'))
        assert manifest['jobs'][5]['error'] == 'intentional file failure'
    assert not synthesis_service.CANCEL_FLAGS
    history = batch_env.client.get('/api/v1/batches')
    assert history.status_code == 200
    assert history.json()[0]['id'] == batch['id']
    assert history.json()[0]['completed'] == 19
    assert history.json()[0]['package_zip'] == final['package_zip']


def test_batch_package_groups_submission_files_with_two_digit_numbering(batch_env, monkeypatch):
    originals = [
        '1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx',
        '2. 고등학생 진로상담 경험 및 자기이해 수준_세종.xlsx',
    ]
    requests = []
    for index, original in enumerate(originals, 1):
        upload_name = f'upload-{index}.xlsx'
        pd.DataFrame({'값': [index]}).to_excel(batch_env.uploads / upload_name, index=False)
        requests.append({'file_name': upload_name, 'original_filename': original, 'target_rows': 2})

    batch = batch_env.client.post('/api/v1/batches', json={'requests': requests}).json()

    def run(job_id, request):
        sequence = request.original_filename.split('.', 1)[0]
        dataset_name = request.original_filename.split('. ', 1)[1].rsplit('.', 1)[0]
        root = batch_env.outputs / f'{job_id}_{dataset_name}'
        original_dir = root / '원본데이터_세종'
        synthetic_dir = root / '합성데이터_세종'
        review_dir = root / '심의자료_세종'
        for directory in (original_dir, synthetic_dir, review_dir):
            directory.mkdir(parents=True)
        (original_dir / request.original_filename).write_text('original', encoding='utf-8')
        (synthetic_dir / f'{sequence}. {dataset_name}.xlsx').write_text('synthetic', encoding='utf-8')
        (review_dir / f'{sequence}. 원본데이터 명세서({dataset_name}).hwpx').write_text('review', encoding='utf-8')
        job_zip = batch_env.outputs / f'{job_id}.zip'
        with ZipFile(job_zip, 'w') as archive:
            archive.writestr('legacy.txt', 'legacy')
        with batch_env.sessions() as db:
            repo = JobRepository(db)
            job = repo.get_by_id(job_id)
            job.status = 'completed'
            job.progress = 100
            job.package_dir = str(root)
            job.package_zip = str(job_zip)
            job.package_folders = {
                '원본데이터': str(original_dir),
                '합성데이터': str(synthetic_dir),
                '심의자료': str(review_dir),
            }
            repo.save(job)

    monkeypatch.setattr(synthesis_service.SynthesisService, '_run_pipeline', run)
    BatchService._run_batch(batch['id'])
    final = BatchService.get(batch['id'])

    with ZipFile(final['package_zip']) as archive:
        names = set(archive.namelist())

    assert '원본데이터_세종/01. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx' in names
    assert '합성데이터_세종/01. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx' in names
    assert '심의자료_세종/01. 원본데이터 명세서(고등학생 진로수업 경험과 진로정보 인식_세종).hwpx' in names
    assert '원본데이터_세종/02. 고등학생 진로상담 경험 및 자기이해 수준_세종.xlsx' in names
    assert '합성데이터_세종/02. 고등학생 진로상담 경험 및 자기이해 수준_세종.xlsx' in names
    assert '심의자료_세종/02. 원본데이터 명세서(고등학생 진로상담 경험 및 자기이해 수준_세종).hwpx' in names
    assert not any(name.endswith('.zip') for name in names)


def test_canceled_waiting_jobs_are_not_run(batch_env, monkeypatch):
    uploaded = upload_files(batch_env, 3).json()['files']
    batch = BatchService.start([SynthesisRequest(file_name=f['filename']) for f in uploaded])
    batch_env.client.post(f"/api/v1/batches/{batch['id']}/cancel")
    executed = []
    monkeypatch.setattr(synthesis_service.SynthesisService, '_run_pipeline', lambda *args: executed.append(args))
    BatchService._run_batch(batch['id'])
    final = BatchService.get(batch['id'])
    assert not executed and final['canceled'] == 3 and final['status'] == 'canceled'


def test_restart_marks_unfinished_jobs_and_limits_validate_before_creation(batch_env):
    uploaded = upload_files(batch_env, 1).json()['files'][0]
    request = {'file_name': uploaded['filename']}
    assert batch_env.client.post('/api/v1/batches', json={'requests': [request] * 21}).status_code == 422
    assert not batch_env.submitted
    batch = BatchService.start([SynthesisRequest(**request)])
    BatchService.recover_interrupted()
    recovered = BatchService.get(batch['id'])
    assert recovered['status'] == 'failed' and recovered['failed'] == 1
    assert '서버 재시작' in recovered['jobs'][0]['error']


def test_two_real_pipelines_produce_independent_hangul_packages(batch_env):
    requests = []
    for index in range(2):
        name = f'data-{index}.csv'
        pd.DataFrame({'value': [x + index for x in range(20)], 'amount': [x * x for x in range(20)]}).to_csv(batch_env.uploads / name, index=False)
        requests.append(SynthesisRequest(file_name=name, model_type='statistical', target_rows=3,
                                         sampling_batch_size=5, max_sampling_attempts=5))
    batch = BatchService.start(requests)
    BatchService._run_batch(batch['id'])
    final = BatchService.get(batch['id'])
    assert final['status'] == 'completed', final
    assert len({job['package_dir'] for job in final['jobs']}) == 2
    for job in final['jobs']:
        assert job['assessment_passed'] is False
        assert job['assessment_score'] is None and job['reid_risk'] is None
        with ZipFile(job['package_zip']) as archive:
            assert len([n for n in archive.namelist() if n.endswith('.hwpx')]) == 3
    assert Path(final['package_zip']).exists()


def test_api_upload_and_batch_apply_notebook_defaults_and_respect_user_overrides(batch_env, monkeypatch):
    from synthetic_engine.profiling.notebook_presets import PRESETS
    _, cats, nums, *_ = PRESETS[1]
    frame = pd.DataFrame({**{c: ['a', 'b', 'c'] for c in cats}, **{c: [1, None, 3] for c in nums}})
    frame.to_csv(batch_env.uploads / 'housing.csv', index=False)
    profile = batch_env.client.get('/api/v1/datasets/profile', params={'file_name': 'housing.csv'}).json()
    assert profile['notebook_preset']['options']['preserve_null_columns'] == ['소득분위']
    info_types = {column['name']: column['information_type'] for column in profile['columns']}
    assert info_types['소득분위'] == '준식별자'
    assert set(info_types.values()) <= {'준식별자', '일반정보'}
    seen = []
    class Probe:
        def __init__(self, config): seen.append(config)
        def execute(self, **kwargs): raise RuntimeError('stop after configuration capture')
    monkeypatch.setattr(synthesis_service, 'SyntheticPipeline', Probe)
    response = batch_env.client.post('/api/v1/batches', json={'requests': [
        {'file_name': 'housing.csv'}, {'file_name': 'housing.csv', 'epochs': 2, 'duplicate_policy': 'strict'}]})
    assert response.status_code == 200
    BatchService._run_batch(response.json()['id'])
    assert seen[0].model_type == 'ctgan' and seen[0].epochs == 50 and seen[0].batch_size == 64
    assert seen[0].duplicate_policy == 'balanced'
    assert seen[1].epochs == 2 and seen[1].duplicate_policy == 'strict'


def test_profile_returns_unique_value_preview_beyond_first_five(batch_env):
    values = [f'응답-{index}' for index in range(8)]
    pd.DataFrame({'응답문항': values}).to_csv(batch_env.uploads / 'survey.csv', index=False)

    profile = batch_env.client.get('/api/v1/datasets/profile', params={'file_name': 'survey.csv'}).json()
    column = profile['columns'][0]

    assert column['unique_values_total'] == 8
    assert column['samples'] == values
    assert column['samples_truncated'] is False
