import os
import uuid
import shutil
import threading
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from synthetic_api.core.config import settings
from synthetic_api.core.logging import logger
from synthetic_api.domain.models.job import JobStatus, SynthesisRequest
from synthetic_api.infrastructure.db.session import SessionLocal
from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository
from synthetic_api.infrastructure.repositories.audit_repo_impl import AuditRepository
from synthetic_api.domain.models.audit import AuditLogEntry

from synthetic_engine import (
    SyntheticPipeline,
    SynthesisConfig
)

ACTIVE_TASKS = {}
CANCEL_FLAGS = {}

class SynthesisService:
    @staticmethod
    def create_job(req: SynthesisRequest) -> JobStatus:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        job = JobStatus(
            id=job_id,
            status="pending",
            progress=0,
            message="작업 대기열 등록됨",
            original_filename=Path(req.original_filename or req.file_name).name,
            file_path=str(settings.UPLOAD_DIR / req.file_name),
            department_name=req.department_name,
            project_purpose=req.project_purpose,
            model_type=req.model_type,
            target_rows=req.target_rows,
            eps=req.eps,
            quality_threshold=req.quality_threshold
        )
        
        db = SessionLocal()
        try:
            repo = JobRepository(db)
            audit = AuditRepository(db)
            repo.save(job)
            audit.log(AuditLogEntry(
                job_id=job_id,
                action="JOB_CREATED",
                actor="user",
                detail=f"모델={req.model_type}, 생성수={req.target_rows}, DP={req.dp_enabled}(eps={req.eps})"
            ))
        finally:
            db.close()
            
        return job

    @staticmethod
    def start_pipeline_async(job_id: str, req: SynthesisRequest):
        CANCEL_FLAGS[job_id] = False
        t = threading.Thread(target=SynthesisService._run_pipeline, args=(job_id, req), daemon=True)
        ACTIVE_TASKS[job_id] = t
        t.start()

    @staticmethod
    def cancel_job(job_id: str) -> bool:
        if job_id in CANCEL_FLAGS:
            CANCEL_FLAGS[job_id] = True
            db = SessionLocal()
            try:
                repo = JobRepository(db)
                job = repo.get_by_id(job_id)
                if job and job.status not in {"completed", "failed", "canceled"}:
                    job.status = "canceled"
                    job.message = "사용자에 의해 작업이 취소되었습니다."
                    repo.save(job)
            finally:
                db.close()
            return True
        return False

    @staticmethod
    def _run_pipeline(job_id: str, req: SynthesisRequest):
        db = SessionLocal()
        repo = JobRepository(db)
        audit = AuditRepository(db)
        
        def update_progress(pct: int, msg: str):
            if CANCEL_FLAGS.get(job_id, False):
                raise InterruptedError("Job canceled by user")
            job = repo.get_by_id(job_id)
            if job:
                job.status = "processing"
                job.progress = pct
                job.message = msg
                repo.save(job)

        try:
            logger.info(f"Starting synthesis job {job_id} for {req.file_name}")
            update_progress(5, "작업 환경 및 입력 데이터 준비 중...")
            
            src_path = Path(settings.UPLOAD_DIR / req.file_name)
            if not src_path.exists():
                src_path = Path(req.file_name)
            if not src_path.exists():
                raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {src_path}")

            from synthetic_engine.profiling.notebook_presets import notebook_settings
            from synthetic_engine.profiling.analyzer import read_table
            preset = notebook_settings(read_table(src_path))['options']
            config = SynthesisConfig(
                model_type=req.model_type,
                sample_rows=req.target_rows,
                epochs=req.epochs or preset.get('epochs', 30),
                batch_size=req.batch_size or preset.get('batch_size', 64),
                pac=req.pac or preset.get('pac', 1),
                duplicate_policy=req.duplicate_policy,
                seed=req.seed,
                sampling_batch_size=req.sampling_batch_size,
                max_sampling_attempts=req.max_sampling_attempts,
                enable_gpu=req.enable_gpu,
                dp_enabled=req.dp_enabled,
                dp_epsilon=req.eps
            )

            pipeline = SyntheticPipeline(config=config)
            result = pipeline.execute(
                input_path=src_path,
                output_dir=settings.OUTPUT_DIR,
                job_id=job_id,
                original_filename=Path(req.original_filename or req.file_name).name,
                department_name=req.department_name,
                selected_columns=req.selected_columns,
                project_purpose=req.project_purpose,
                review_metadata=req.review_metadata.model_dump() if req.review_metadata else None,
                categorical_columns=req.categorical_columns,
                numerical_columns=req.numerical_columns,
                preserve_null_columns=req.preserve_null_columns,
                evaluation_excluded_columns=req.evaluation_excluded_columns,
                conditions=req.conditions,
                constraints=req.constraints,
                progress_callback=update_progress
            )

            report = result.get("report", {})
            assessment = report.get("auto_assessment", {})
            package_dirs = result.get("package_dirs", {})
            hwp_files = result.get("hwp_files", {})

            # Create ZIP bundle
            zip_base = str(package_dirs["root"])
            shutil.make_archive(zip_base, "zip", root_dir=package_dirs["root"])
            zip_path = f"{zip_base}.zip"

            if CANCEL_FLAGS.get(job_id, False):
                raise InterruptedError("Job canceled by user")

            job = repo.get_by_id(job_id)
            if job:
                job.status = "completed"
                job.progress = 100
                job.message = '생성 완료 · ' + ('자동 점검 통과' if assessment.get('passed') else '검토 필요')
                job.quality_score = float(report.get("overall_quality", 0.85))
                job.reid_risk = report.get('reid_risk')
                job.assessment_passed = bool(assessment.get('passed', False))
                job.assessment_grade = assessment.get('grade')
                job.assessment_score = assessment.get('score')
                job.package_dir = str(package_dirs.get("root", ""))
                job.package_zip = zip_path
                job.package_folders = {
                    "원본데이터": str(package_dirs.get("original", "")),
                    "합성데이터": str(package_dirs.get("synthetic", "")),
                    "심의위원회 심의자료": str(package_dirs.get("review", ""))
                }
                job.file_sha256 = result.get("raw_hash", "")
                repo.save(job)

            audit.log(AuditLogEntry(
                job_id=job_id,
                action="JOB_COMPLETED",
                actor="system",
                detail=f"등급={job.assessment_grade}, 품질={job.quality_score}, 위험={job.reid_risk}"
            ))
            logger.info(f"Job {job_id} successfully completed")

        except InterruptedError:
            logger.warning(f"Job {job_id} was interrupted by user")
            job = repo.get_by_id(job_id)
            if job:
                job.status = "canceled"
                job.message = "사용자에 의해 작업이 취소되었습니다."
                repo.save(job)
        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")
            job = repo.get_by_id(job_id)
            if job:
                job.status = "failed"
                job.message = f"오류 발생: {str(e)}"
                job.error = str(e)
                repo.save(job)
            audit.log(AuditLogEntry(
                job_id=job_id,
                action="JOB_FAILED",
                actor="system",
                detail=str(e)
            ))
        finally:
            db.close()
            ACTIVE_TASKS.pop(job_id, None)
            CANCEL_FLAGS.pop(job_id, None)
