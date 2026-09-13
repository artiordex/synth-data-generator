# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: audit.py
# 경로: apps/api/src/synthetic_api/domain/models/audit.py
# 목적: 개인정보 처리 및 데이터 변환 감사 로그 도메인 모델임
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AuditLogEntry(BaseModel):
    id: Optional[int] = None
    job_id: str
    action: str
    actor: str = 'system'
    detail: str = ''
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
