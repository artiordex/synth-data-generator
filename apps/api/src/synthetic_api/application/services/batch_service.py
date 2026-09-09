"""
파일명: batch_service.py
경로: apps/api/src/synthetic_api/application/services/batch_service.py
목적: 여러 합성 작업의 일괄 실행과 결과 패키징을 관리함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
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
from .job_runtime import TERMINAL_JOB_STATUSES, clear_runtime_job, is_terminal, register_cancelable
from .synthesis_service import SynthesisService
from synthetic_engine.exporters.package_exporter import (
    numbered_submission_filename,
    safe_path_part,
    split_leading_sequence,
    submission_folder_name,
)

_WORKER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="batch-synthesis")
TERMINAL = TERMINAL_JOB_STATUSES


class BatchService:
    """여러 합성 작업을 하나의 일괄 작업으로 관리함"""

    @staticmethod
    def list_recent():
        """최근 일괄 작업 목록을 조회함"""
        with SessionLocal() as db:
            ids = [row.id for row in db.query(BatchEntity)
                   .order_by(BatchEntity.created_at.desc()).limit(50).all()]
        return [BatchService.get(batch_id) for batch_id in ids]

    @staticmethod
    def start(requests: list[SynthesisRequest]):
        """합성 요청 목록을 일괄 작업으로 등록하고 실행함"""
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
            register_cancelable(job.id)
            items.append({'job_id': job.id, 'request': request.model_dump()})
        with SessionLocal() as db:
            db.add(BatchEntity(id=batch_id, items_json=json.dumps(items, ensure_ascii=False)))
            db.commit()
        _WORKER.submit(BatchService._run_batch, batch_id)
        return BatchService.get(batch_id)

    @staticmethod
    def get(batch_id):
        """일괄 작업과 하위 작업의 현재 상태를 조회함"""
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
        """일괄 작업에 포함된 실행 중 작업을 취소함"""
        snapshot = BatchService.get(batch_id)
        for job in snapshot['jobs']:
            if job['status'] not in TERMINAL:
                SynthesisService.cancel_job(job['id'])
        return BatchService.get(batch_id)

    @staticmethod
    def _run_batch(batch_id):
        """일괄 작업을 순차 실행하고 결과 ZIP을 생성함"""
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
                if is_terminal(job.status):
                    clear_runtime_job(job_id)
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
                    clear_runtime_job(job_id)
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
                            if not BatchService._write_submission_files_to_batch_zip(archive, job, index):
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
    def _write_submission_files_to_batch_zip(archive: ZipFile, job: dict, index: int) -> bool:
        """Write one completed job as numbered files under grouped submission folders."""
        original_filename = Path(job.get('original_filename') or f"data-{index}.xlsx").name
        _, dataset_name = split_leading_sequence(Path(original_filename).stem)
        dataset_name = safe_path_part(dataset_name, "데이터")
        package_folders = job.get('package_folders') or {}
        package_root = Path(job.get('package_dir') or "").resolve() if job.get('package_dir') else None
        output_root = settings.OUTPUT_DIR.resolve()

        sources = [
            ("원본데이터", package_folders.get("원본데이터")),
            ("합성데이터", package_folders.get("합성데이터")),
            ("심의자료", package_folders.get("심의자료") or package_folders.get("심의위원회 심의자료")),
        ]
        wrote_any = False
        for kind, configured_path in sources:
            source_dir = Path(configured_path).resolve() if configured_path else None
            if (not source_dir or not source_dir.is_dir()) and package_root and package_root.is_dir():
                candidates = [p for p in package_root.iterdir() if p.is_dir() and (p.name == kind or p.name.startswith(f"{kind}_"))]
                source_dir = candidates[0].resolve() if candidates else None
            if not source_dir or not source_dir.is_dir():
                continue
            if not source_dir.is_relative_to(output_root):
                raise ValueError('출력 폴더 밖의 파일은 묶을 수 없습니다.')
            archive_folder = submission_folder_name(kind, dataset_name)
            for file_path in sorted((p for p in source_dir.iterdir() if p.is_file()), key=lambda p: p.name):
                archive.write(file_path, f"{archive_folder}/{numbered_submission_filename(file_path.name, index)}")
                wrote_any = True
        return wrote_any

    @staticmethod
    def recover_interrupted():
        """서버 재시작으로 중단된 일괄 작업을 실패 상태로 기록함"""
        """Make interrupted groups explicit after process restart, never re-run silently."""
        with SessionLocal() as db:
            for batch in db.query(BatchEntity).filter(BatchEntity.status.in_(['pending', 'processing'])).all():
                repo = JobRepository(db)
                for item in json.loads(batch.items_json):
                    job = repo.get_by_id(item['job_id'])
                    if job and not is_terminal(job.status):
                        job.status = 'failed'
                        job.error = job.message = '서버 재시작으로 중단되었습니다. 해당 파일을 다시 실행하세요.'
                        repo.save(job)
                batch.status, batch.error = 'failed', '서버 재시작으로 중단된 일괄 작업입니다.'
            db.commit()
