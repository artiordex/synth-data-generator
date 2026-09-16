# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: batch_service.py
# 경로: apps/api/src/synthetic_api/application/services/batch_service.py
# 목적: 다중 합성 작업의 일괄 실행 및 상태 관리 서비스를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
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

    # list recent 작업을 수행함
    @staticmethod
    def list_recent():
        """
        @description 최근 등록된 일괄(배치) 합성 작업 목록을 최대 50건 조회함
        @return: 조회된 일괄 작업 세부 정보 딕셔너리 리스트를 반환함
        """
        with SessionLocal() as db:
            ids = [row.id for row in db.query(BatchEntity)
                   .order_by(BatchEntity.created_at.desc()).limit(50).all()]
        return [BatchService.get(batch_id) for batch_id in ids]

    # start 작업을 수행함
    @staticmethod
    def start(requests: list[SynthesisRequest]):
        """
        @description 1~20개의 합성 요청을 일괄 작업으로 등록하고 백그라운드 워커에서 실행함
        @param requests: 일괄 처리할 SynthesisRequest 객체 리스트임
        @return: 생성된 배치 ID 및 하위 작업 요약 딕셔너리를 반환함
        @throws ValueError: 요청 개수 범위를 초과하거나 대상 파일이 존재하지 않는 경우 발생함
        """
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

    # get 작업을 수행함
    @staticmethod
    def get(batch_id):
        """
        @description 일괄 작업 및 소속 하위 작업들의 실시간 진행 상태와 통계를 집계 조회함
        @param batch_id: 조회할 일괄 작업 고유 식별자임
        @return: 하위 작업 목록 및 종합 진행률 딕셔너리를 반환함
        @throws FileNotFoundError: 해당 배치 ID가 존재하지 않는 경우 발생함
        """
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
                    'jobs': [j.model_dump() for j in jobs],
                    'package_zip': batch.package_zip,
                    'documents_zip': getattr(batch, 'documents_zip', None) or batch.package_zip,
                    'error': batch.error}

    # cancel 작업을 수행함
    @staticmethod
    def cancel(batch_id):
        """
        @description 일괄 작업에 포함된 모든 미완료 하위 작업을 일괄 취소함
        @param batch_id: 취소할 일괄 작업 고유 식별자임
        @return: 갱신된 일괄 작업 상태 스냅샷을 반환함
        """
        snapshot = BatchService.get(batch_id)
        for job in snapshot['jobs']:
            if job['status'] not in TERMINAL:
                SynthesisService.cancel_job(job['id'])
        return BatchService.get(batch_id)

    # 일괄(배치) 작업 작업을 실행함
    @staticmethod
    def _run_batch(batch_id):
        """
        @description 백그라운드 스레드에서 배치 내 하위 작업들을 순차 실행하고 산출물 ZIP을 패키징함
        @param batch_id: 실행할 일괄 작업 고유 식별자임
        """
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
            target_docs = settings.OUTPUT_DIR / f'{batch_id}_documents.zip'
            temporary_docs = target_docs.with_suffix('.zip.tmp')
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

                # 일괄 문서 단일 묶음 ZIP (원천, 합성, 심의자료 순서별 일괄 넘버링)
                with ZipFile(temporary_docs, 'w', compression=ZIP_STORED) as docs_archive:
                    for index, job in enumerate(snapshot['jobs'], 1):
                        if job['status'] == 'completed':
                            BatchService._write_unified_documents_to_batch_zip(docs_archive, job, index)
                    docs_manifest = {**snapshot, 'status': status, 'progress': 100, 'package_type': 'unified_documents'}
                    docs_archive.writestr('처리결과.json', json.dumps(docs_manifest, ensure_ascii=False, indent=2))
                temporary_docs.replace(target_docs)
            finally:
                temporary.unlink(missing_ok=True)
                temporary_docs.unlink(missing_ok=True)
            with SessionLocal() as db:
                batch = db.get(BatchEntity, batch_id)
                batch.status, batch.package_zip = status, str(target)
                batch.documents_zip = str(target_docs)
                db.commit()
        except Exception as exc:
            with SessionLocal() as db:
                batch = db.get(BatchEntity, batch_id)
                batch.status, batch.error = 'failed', str(exc)
                db.commit()

    # submission 파일 목록 to 일괄(배치) 작업 zip 데이터를 파일에 기록함
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

    # 일괄 문서 단일 아카이브 파일 기록 (원천데이터/합성데이터/심의자료 폴더 안에 순서 넘버링)
    @staticmethod
    def _write_unified_documents_to_batch_zip(archive: ZipFile, job: dict, index: int) -> bool:
        """각 폴더(원본데이터, 합성데이터, 심의자료) 안에 처리 순서 넘버링된 파일을 기록함.

        구조:
          원본데이터/01_파일명.xlsx, 02_파일명.xlsx ...
          합성데이터/01_파일명.xlsx, 02_파일명.xlsx ...
          심의자료/01_원본데이터명세서(파일명).hwpx, 01_합성데이터명세서(파일명).hwpx ...
        """
        original_filename = Path(job.get('original_filename') or f"data-{index}.xlsx").name
        _, raw_stem = split_leading_sequence(Path(original_filename).stem)
        dataset_name = safe_path_part(raw_stem, "데이터")
        package_folders = job.get('package_folders') or {}
        package_root = Path(job.get('package_dir') or "").resolve() if job.get('package_dir') else None
        output_root = settings.OUTPUT_DIR.resolve()

        wrote_any = False

        def resolve_source_dir(key_candidates: list[str], folder_prefix: str) -> "Path | None":
            """package_folders 또는 package_root 탐색으로 소스 디렉터리를 찾음."""
            configured = next((package_folders.get(k) for k in key_candidates if package_folders.get(k)), None)
            d = Path(configured).resolve() if configured else None
            if (not d or not d.is_dir()) and package_root and package_root.is_dir():
                candidates = [p for p in package_root.iterdir()
                              if p.is_dir() and (p.name == folder_prefix or p.name.startswith(f"{folder_prefix}_"))]
                d = candidates[0].resolve() if candidates else None
            return d if d and d.is_dir() and d.is_relative_to(output_root) else None

        # 1. 원본데이터 폴더 → 원본데이터/{index:02d}_{원본파일명}
        raw_dir = resolve_source_dir(["원본데이터"], "원본데이터")
        if raw_dir:
            for file_path in sorted((p for p in raw_dir.iterdir() if p.is_file()), key=lambda p: p.name):
                _, clean_stem = split_leading_sequence(file_path.stem)
                arc_name = f"원본데이터/{index:02d}_{safe_path_part(clean_stem, '데이터')}{file_path.suffix}"
                archive.write(file_path, arc_name)
                wrote_any = True

        # 2. 합성데이터 폴더 → 합성데이터/{index:02d}_{합성파일명}
        synth_dir = resolve_source_dir(["합성데이터"], "합성데이터")
        if synth_dir:
            for file_path in sorted((p for p in synth_dir.iterdir() if p.is_file()), key=lambda p: p.name):
                _, clean_stem = split_leading_sequence(file_path.stem)
                arc_name = f"합성데이터/{index:02d}_{safe_path_part(clean_stem, '데이터')}{file_path.suffix}"
                archive.write(file_path, arc_name)
                wrote_any = True

        # 3. 심의자료 폴더 → 심의자료/{index:02d}_{문서종류}
        review_dir = resolve_source_dir(["심의자료", "심의위원회 심의자료"], "심의자료")
        if review_dir:
            for file_path in sorted((p for p in review_dir.iterdir() if p.is_file()), key=lambda p: p.name):
                _, clean_stem = split_leading_sequence(file_path.stem)
                clean_name = safe_path_part(clean_stem, '문서')
                # 심의 문서 종류 판별 — 기존 파일명에 종류가 들어 있으므로 그대로 유지하고 앞에 번호만 붙임
                if "원본데이터 명세서" in clean_name or "원본데이터명세서" in clean_name:
                    doc_label = f"원본데이터 명세서({dataset_name})"
                elif "합성데이터 명세서" in clean_name or "합성데이터명세서" in clean_name:
                    doc_label = f"합성데이터 명세서({dataset_name})"
                elif "측정결과서" in clean_name or "평가서" in clean_name:
                    doc_label = f"안전성 및 유용성 측정결과서({dataset_name})"
                else:
                    doc_label = clean_name
                arc_name = f"심의자료/{index:02d}_{doc_label}{file_path.suffix}"
                archive.write(file_path, arc_name)
                wrote_any = True

        # Fallback: package_folders 미구성 시 개별 package_zip 내부 파일 추출
        if not wrote_any and job.get('package_zip'):
            p_zip = Path(job['package_zip']).resolve()
            if p_zip.is_file() and p_zip.is_relative_to(output_root):
                try:
                    with ZipFile(p_zip, 'r') as inner_zip:
                        for member in inner_zip.infolist():
                            if not member.is_dir() and not member.filename.endswith('.json'):
                                mem_path = Path(member.filename)
                                _, clean_stem = split_leading_sequence(mem_path.stem)
                                fn = member.filename
                                if "원본데이터" in fn or "원본" in fn:
                                    folder = "원본데이터"
                                elif "합성데이터" in fn or "합성" in fn:
                                    folder = "합성데이터"
                                elif "심의" in fn:
                                    folder = "심의자료"
                                else:
                                    folder = "기타"
                                arc_name = f"{folder}/{index:02d}_{safe_path_part(clean_stem, '문서')}{mem_path.suffix}"
                                archive.writestr(arc_name, inner_zip.read(member))
                                wrote_any = True
                except Exception:
                    pass
                if not wrote_any:
                    archive.write(p_zip, f"기타/{index:02d}_{p_zip.name}")
                    wrote_any = True

        return wrote_any


    # recover interrupted 작업을 수행함
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
