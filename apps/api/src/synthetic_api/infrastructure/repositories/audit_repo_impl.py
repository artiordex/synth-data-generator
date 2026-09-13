# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: audit_repo_impl.py
# 경로: apps/api/src/synthetic_api/infrastructure/repositories/audit_repo_impl.py
# 목적: 감사 로그 데이터베이스 저장 및 조회 레포지토리 구현체임
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from typing import List

from sqlalchemy.orm import Session

from synthetic_api.infrastructure.db.models import AuditLogEntity

from synthetic_api.domain.models.audit import AuditLogEntry



class AuditRepository:

    # AuditRepository 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, db: Session):

        self.db = db



    # log 작업을 수행함
    def log(self, entry: AuditLogEntry) -> AuditLogEntry:

        entity = AuditLogEntity(

            job_id=entry.job_id,

            action=entry.action,

            actor=entry.actor,

            detail=entry.detail

        )

        self.db.add(entity)

        self.db.commit()

        self.db.refresh(entity)

        return AuditLogEntry(

            id=entity.id,

            job_id=entity.job_id,

            action=entity.action,

            actor=entity.actor,

            detail=entity.detail,

            created_at=str(entity.created_at)

        )



    # list by 합성 작업 작업을 수행함
    def list_by_job(self, job_id: str) -> List[AuditLogEntry]:

        entities = self.db.query(AuditLogEntity).filter(AuditLogEntity.job_id == job_id).order_by(AuditLogEntity.created_at.asc()).all()

        return [

            AuditLogEntry(

                id=e.id,

                job_id=e.job_id,

                action=e.action,

                actor=e.actor,

                detail=e.detail,

                created_at=str(e.created_at)

            ) for e in entities

        ]
