"""Persistent groups of existing synthesis jobs, processed one file at a time."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

from synthetic_api.core.config import settings
from synthetic_api.domain.models.job import SynthesisRequest
from synthetic_api.infrastructure.db.models import BatchEntity
from synthetic_api.infrastructure.db.session import SessionLocal
from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository
from .synthesis_service import SynthesisService, CANCEL_FLAGS

_WORKER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="batch-synthesis")
TERMINAL = {"completed", "failed", "canceled"}


class BatchService:
    @staticmethod
    def list_recent():
        with SessionLocal() as db:
            ids = [row.id for row in db.query(BatchEntity)
                   .order_by(BatchEntity.created_at.desc()).limit(50).all()]
        return [BatchService.get(batch_id) for batch_id in ids]

    @staticmethod
    def start(requests: list[SynthesisRequest]):
        if not 1 <= len(requests) <= 20:
            raise ValueError("한 번에 1~20개 파일을 처리할 수 있습니다.")
        root = settings.UPLOAD_DIR.resolve()
        for request in requests:
            candidate = (root / request.file_name).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                raise ValueError(f"업로드 파일을 찾을 수 없습니다: {request.file_name}")
        batch_id = f"batch-{uuid.uuid4().hex}"
        items = []
        for request in requests:
            job = SynthesisService.create_job(request)
            CANCEL_FLAGS[job.id] = False
            items.append({'job_id': job.id, 'request': request.model_dump()})
        with SessionLocal() as db:
            db.add(BatchEntity(id=batch_id, items_json=json.dumps(items, ensure_ascii=False)))
            db.commit()
        _WORKER.submit(BatchService._run_batch, batch_id)
        return BatchService.get(batch_id)

    @staticmethod
    def get(batch_id):
        with SessionLocal() as db:
            batch = db.get(BatchEntity, batch_id)
            if batch is None:
                raise FileNotFoundError("일괄 작업을 찾을 수 없습니다.")
            repo = JobRepository(db)
            jobs = [repo.get_by_id(item['job_id']) for item in json.loads(batch.items_json)]
            if any(job is None for job in jobs):
                raise ValueError("일괄 작업의 파일별 이력이 누락되었습니다.")
            done = sum(job.status in TERMINAL for job in jobs)
            progress = int(sum(100 if j.status in TERMINAL else j.progress for j in jobs) / len(jobs))
            return {'id': batch.id, 'status': batch.status, 'created_at': str(batch.created_at),
                    'total': len(jobs), 'finished': done,
                    'completed': sum(j.status == 'completed' for j in jobs),
                    'failed': sum(j.status == 'failed' for j in jobs),
                    'canceled': sum(j.status == 'canceled' for j in jobs),
                    'progress': min(progress, 99) if batch.status in {'pending', 'processing'} else progress,
                    'jobs': [j.model_dump() for j in jobs], 'package_zip': batch.package_zip, 'error': batch.error}

    @staticmethod
    def cancel(batch_id):
        snapshot = BatchService.get(batch_id)
        for job in snapshot['jobs']:
            if job['status'] not in TERMINAL:
                SynthesisService.cancel_job(job['id'])
        return BatchService.get(batch_id)

    @staticmethod
    def _run_batch(batch_id):
        with SessionLocal() as db:
            batch = db.get(BatchEntity, batch_id)
            items = json.loads(batch.items_json)
            batch.status = 'processing'
            db.commit()
        try:
            for item in items:
                job_id = item['job_id']
                with SessionLocal() as db:
                    job = JobRepository(db).get_by_id(job_id)
                if job.status in TERMINAL:
                    CANCEL_FLAGS.pop(job_id, None)
                    continue
                try:
                    SynthesisService._run_pipeline(job_id, SynthesisRequest.model_validate(item['request']))
                except Exception as exc:
                    # An unexpected failure in one runner must not skip later files.
                    with SessionLocal() as db:
                        repo = JobRepository(db)
                        job = repo.get_by_id(job_id)
                        job.status, job.error, job.message = 'failed', str(exc), f'오류 발생: {exc}'
                        repo.save(job)
                finally:
                    CANCEL_FLAGS.pop(job_id, None)
            snapshot = BatchService.get(batch_id)
            status = ('completed' if snapshot['completed'] == snapshot['total'] else
                      'completed_with_errors' if snapshot['completed'] else
                      'failed' if snapshot['failed'] else 'canceled')
            target = settings.OUTPUT_DIR / f'{batch_id}.zip'
            temporary = target.with_suffix('.zip.tmp')
            try:
                with ZipFile(temporary, 'w', compression=ZIP_STORED) as archive:
                    for index, job in enumerate(snapshot['jobs'], 1):
                        if job['status'] == 'completed' and job['package_zip']:
                            path = Path(job['package_zip']).resolve()
                            if not path.is_relative_to(settings.OUTPUT_DIR.resolve()):
                                raise ValueError('출력 폴더 밖의 파일은 묶을 수 없습니다.')
                            archive.write(path, f'{index:02d}_{path.name}')
                    manifest = {**snapshot, 'status': status, 'progress': 100}
                    archive.writestr('처리결과.json', json.dumps(manifest, ensure_ascii=False, indent=2))
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            with SessionLocal() as db:
                batch = db.get(BatchEntity, batch_id)
                batch.status, batch.package_zip = status, str(target)
                db.commit()
        except Exception as exc:
            with SessionLocal() as db:
                batch = db.get(BatchEntity, batch_id)
                batch.status, batch.error = 'failed', str(exc)
                db.commit()

    @staticmethod
    def recover_interrupted():
        """Make interrupted groups explicit after process restart, never re-run silently."""
        with SessionLocal() as db:
            for batch in db.query(BatchEntity).filter(BatchEntity.status.in_(['pending', 'processing'])).all():
                repo = JobRepository(db)
                for item in json.loads(batch.items_json):
                    job = repo.get_by_id(item['job_id'])
                    if job and job.status not in TERMINAL:
                        job.status = 'failed'
                        job.error = job.message = '서버 재시작으로 중단되었습니다. 해당 파일을 다시 실행하세요.'
                        repo.save(job)
                batch.status, batch.error = 'failed', '서버 재시작으로 중단된 일괄 작업입니다.'
            db.commit()
