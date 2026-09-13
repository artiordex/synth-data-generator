# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: review.py
# 경로: apps/api/src/synthetic_api/routes/v1/review.py
# 목적: 생성 데이터 품질 검증 및 승인/반려 리뷰 API 엔드포인트를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException

from typing import List

from synthetic_api.domain.models.audit import AuditLogEntry

from synthetic_api.routes.dependencies import get_audit_repo

from synthetic_api.infrastructure.repositories.audit_repo_impl import AuditRepository



router = APIRouter(prefix="/review", tags=["review"])



# 감사 로그 로그 기록 정보를 조회하여 반환함
@router.get("/audit-logs/{job_id}", response_model=List[AuditLogEntry], summary="합성 작업 감사 로그(Audit Log) 조회", description="특정 합성 작업에 대해 수행된 단계별 보안 및 가명처리 감사 로그를 시간순으로 조회합니다.")

# 데이터 합성 및 변환 작업의 감사(Audit) 로그 목록을 조회함
async def get_audit_logs(job_id: str, repo: AuditRepository = Depends(get_audit_repo)):

    return repo.list_by_job(job_id)
