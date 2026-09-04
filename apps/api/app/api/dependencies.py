from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.job_repo_impl import JobRepository
from app.infrastructure.repositories.audit_repo_impl import AuditRepository

def get_job_repo(db: Session = Depends(get_db)) -> JobRepository:
    return JobRepository(db)

def get_audit_repo(db: Session = Depends(get_db)) -> AuditRepository:
    return AuditRepository(db)
