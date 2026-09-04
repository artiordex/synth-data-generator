from fastapi import APIRouter, Depends, HTTPException

from typing import List

from synthetic_api.domain.models.audit import AuditLogEntry

from synthetic_api.routes.dependencies import get_audit_repo

from synthetic_api.infrastructure.repositories.audit_repo_impl import AuditRepository



router = APIRouter(prefix="/review", tags=["review"])



@router.get("/audit-logs/{job_id}", response_model=List[AuditLogEntry])

async def get_audit_logs(job_id: str, repo: AuditRepository = Depends(get_audit_repo)):

    return repo.list_by_job(job_id)
