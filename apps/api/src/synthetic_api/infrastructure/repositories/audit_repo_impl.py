from typing import List

from sqlalchemy.orm import Session

from synthetic_api.infrastructure.db.models import AuditLogEntity

from synthetic_api.domain.models.audit import AuditLogEntry



class AuditRepository:

    def __init__(self, db: Session):

        self.db = db



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
