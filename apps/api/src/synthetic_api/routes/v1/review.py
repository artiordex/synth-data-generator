"""
파일명: review.py
경로: apps/api/src/synthetic_api/routes/v1/review.py
목적: 합성 작업 감사 로그 조회 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from fastapi import APIRouter, Depends, HTTPException

from typing import List

from synthetic_api.domain.models.audit import AuditLogEntry

from synthetic_api.routes.dependencies import get_audit_repo

from synthetic_api.infrastructure.repositories.audit_repo_impl import AuditRepository



router = APIRouter(prefix="/review", tags=["review"])



@router.get("/audit-logs/{job_id}", response_model=List[AuditLogEntry], summary="합성 작업 감사 로그(Audit Log) 조회", description="특정 합성 작업에 대해 수행된 단계별 보안 및 가명처리 감사 로그를 시간순으로 조회합니다.")

async def get_audit_logs(job_id: str, repo: AuditRepository = Depends(get_audit_repo)):

    return repo.list_by_job(job_id)
