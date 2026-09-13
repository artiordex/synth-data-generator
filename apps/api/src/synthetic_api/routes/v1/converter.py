# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: converter.py
# 경로: apps/api/src/synthetic_api/routes/v1/converter.py
# 목적: 파일 업로드 및 포맷 변환 REST API 엔드포인트를 제공함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
"""HTTP boundary for conversion rules, jobs and history."""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.concurrency import run_in_threadpool
from synthetic_api.application.services import document_conversion_service as service
from synthetic_api.application.services.document_conversion_service import DocumentConversionService, ConversionError
from synthetic_api.application.services.conversion_rules import ConversionRuleError, catalog, normalize_source, source_kind

router = APIRouter(prefix="/converter", tags=["converter"])


# 입력 포맷별 허용 대상 포맷 및 미리보기 모드 매트릭스를 반환함
@router.get("/rules", summary="변환 규칙 조회", description="입력 포맷별 허용 대상 포맷과 미리보기 모드를 반환합니다.")
async def get_conversion_rules(source_format: Optional[str] = None):
    """Return the same compatibility matrix used by the conversion endpoint."""
    try:
        if source_format:
            source = normalize_source(source_format)
            source_kind(source)
            return {"source": source, "rules": catalog()[source]}
        return {"rules": catalog()}
    except ConversionRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# 원본 파일과 대상 포맷 옵션을 전달받아 비동기 문서 변환을 수행함
@router.post("/convert", summary="문서 및 정형 데이터 포맷 상호 변환")
async def convert_file(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    encoding: Optional[str] = Form("utf-8"),
    table_name: Optional[str] = Form("converted_data"),
    engine: str = Form("legacy"),
    strict: bool = Form(False),
):
    try:
        return await run_in_threadpool(DocumentConversionService.convert, file, target_format,
                                       encoding, table_name, engine, strict)
    except ConversionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


# 과거 수행된 문서 및 데이터 변환 작업 이력 목록을 조회함
@router.get("/history", summary="문서/데이터 변환 작업 이력 조회")
async def get_converter_history():
    return await run_in_threadpool(DocumentConversionService.history)


# 레거시 헬퍼 모듈 속성 참조를 서비스 구현체로 위임함
def __getattr__(name):
    # Keep legacy helper imports working while implementations live in the service.
    if name.startswith("_") and hasattr(service, name):
        return getattr(service, name)
    raise AttributeError(name)
