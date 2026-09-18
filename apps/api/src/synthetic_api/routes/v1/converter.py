# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: converter.py
# 경로: apps/api/src/synthetic_api/routes/v1/converter.py
# 목적: 파일 업로드 및 포맷 변환 REST API 엔드포인트를 제공함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-17
# =============================================================================
"""HTTP boundary for conversion rules, jobs and history."""
from typing import Optional
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.concurrency import run_in_threadpool
from synthetic_api.application.services import document_conversion_service as service
from synthetic_api.application.services.document_conversion_service import DocumentConversionService, ConversionError
from synthetic_api.application.services.conversion_rules import ConversionRuleError, catalog, normalize_source, source_kind
from synthetic_api.application.services.public_data_conversion import read_source, recommend_names

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
    dataset_profile: str = Form('auto'),
    field_names: Optional[str] = Form(None),
    field_names_confirmed: bool = Form(False),
    sheet_name: Optional[str] = Form(None),
    record_path: Optional[str] = Form(None),
):
    try:
        try:
            names = json.loads(field_names) if field_names is not None else None
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail='field_names는 원천 컬럼명과 영문명을 연결하는 JSON 객체여야 합니다.') from exc
        return await run_in_threadpool(DocumentConversionService.convert, file, target_format,
                                       encoding, table_name, engine, strict,
                                       dataset_profile, names, field_names_confirmed, sheet_name, record_path)
    except ConversionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


# 데이터 값은 외부 AI로 전달하지 않고 영문 컬럼명 추천·수정 초안을 반환함
@router.post('/field-names', summary='CSV·엑셀 영문 변수명 추천')
async def suggest_field_names(
    file: UploadFile = File(...), encoding: str = Form('utf-8'),
    sheet_name: Optional[str] = Form(None), use_ai: bool = Form(True),
):
    try:
        raw = await file.read(100 * 1024 * 1024 + 1)
        source = await run_in_threadpool(read_source, raw, file.filename or '', encoding, sheet_name)
        result = await run_in_threadpool(recommend_names, source['headers'], use_ai)
        return dict(result, rows_count=len(source['rows']), sheets=source['sheets'], sheet_name=source['sheet_name'])
    except (ValueError, OSError, UnicodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail='입력 파일을 읽을 수 없습니다. CSV·엑셀 파일 형식과 손상 여부를 확인하세요.') from exc
    finally:
        await file.close()


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
