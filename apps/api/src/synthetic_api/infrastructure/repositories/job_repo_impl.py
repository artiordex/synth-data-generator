import json

from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from synthetic_api.infrastructure.db.models import JobEntity

from synthetic_api.domain.models.job import JobStatus



class JobRepository:

    def __init__(self, db: Session):

        self.db = db



    def save(self, job: JobStatus) -> JobStatus:

        entity = self.db.query(JobEntity).filter(JobEntity.id == job.id).first()

        if not entity:

            entity = JobEntity(id=job.id)

            self.db.add(entity)

        

        entity.status = job.status

        entity.progress = job.progress

        entity.message = job.message

        entity.original_filename = job.original_filename

        entity.file_path = job.file_path

        entity.file_sha256 = job.file_sha256

        entity.department_name = job.department_name

        entity.project_purpose = job.project_purpose

        entity.model_type = job.model_type

        entity.target_rows = job.target_rows

        entity.eps = job.eps

        entity.quality_threshold = job.quality_threshold

        entity.quality_score = job.quality_score

        entity.reid_risk = job.reid_risk

        entity.assessment_passed = job.assessment_passed

        entity.assessment_grade = job.assessment_grade

        entity.assessment_score = job.assessment_score

        entity.package_dir = job.package_dir

        entity.package_zip = job.package_zip

        if job.package_folders:

            entity.package_folders_json = json.dumps(job.package_folders, ensure_ascii=False)

        entity.error = job.error

        

        self.db.commit()

        self.db.refresh(entity)

        return self._to_domain(entity)



    def get_by_id(self, job_id: str) -> Optional[JobStatus]:

        entity = self.db.query(JobEntity).filter(JobEntity.id == job_id).first()

        if not entity:

            return None

        return self._to_domain(entity)



    def list_all(self, limit: int = 50) -> List[JobStatus]:

        entities = self.db.query(JobEntity).order_by(JobEntity.created_at.desc()).limit(limit).all()

        return [self._to_domain(e) for e in entities]



    def _to_domain(self, entity: JobEntity) -> JobStatus:

        folders = None

        if entity.package_folders_json:

            try:

                folders = json.loads(entity.package_folders_json)

            except Exception:

                pass

        return JobStatus(

            id=entity.id,

            status=entity.status,

            progress=entity.progress,

            message=entity.message,

            original_filename=entity.original_filename,

            file_path=entity.file_path,

            file_sha256=entity.file_sha256,

            department_name=entity.department_name,

            project_purpose=entity.project_purpose,

            model_type=entity.model_type,

            target_rows=entity.target_rows,

            eps=entity.eps,

            quality_threshold=entity.quality_threshold,

            quality_score=entity.quality_score,

            reid_risk=entity.reid_risk,

            assessment_passed=entity.assessment_passed,

            assessment_grade=entity.assessment_grade,

            assessment_score=entity.assessment_score,

            package_dir=entity.package_dir,

            package_zip=entity.package_zip,

            package_folders=folders,

            error=entity.error,

            created_at=str(entity.created_at),

            updated_at=str(entity.updated_at)

        )
