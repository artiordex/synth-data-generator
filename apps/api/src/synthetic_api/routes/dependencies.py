# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: dependencies.py
# 경로: apps/api/src/synthetic_api/routes/dependencies.py
# 목적: API 엔드포인트 의존성 주입(Dependency Injection) 팩토리를 제공함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from fastapi import Depends

from sqlalchemy.orm import Session

from synthetic_api.infrastructure.db.session import get_db

from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository

from synthetic_api.infrastructure.repositories.audit_repo_impl import AuditRepository



# 합성 작업 repo 정보를 조회하여 반환함
def get_job_repo(db: Session = Depends(get_db)) -> JobRepository:

    return JobRepository(db)



# 감사 로그 repo 정보를 조회하여 반환함
def get_audit_repo(db: Session = Depends(get_db)) -> AuditRepository:

    return AuditRepository(db)
