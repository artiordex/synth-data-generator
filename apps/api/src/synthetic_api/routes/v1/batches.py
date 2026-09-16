# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: batches.py
# 경로: apps/api/src/synthetic_api/routes/v1/batches.py
# 목적: 배치 합성 작업 요청 접수 및 상태 조회 API 엔드포인트를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from synthetic_api.domain.models.job import SynthesisRequest
from synthetic_api.application.services.batch_service import BatchService

router = APIRouter(prefix='/batches', tags=['batches'])


class BatchRequest(BaseModel):
    requests: list[SynthesisRequest] = Field(min_length=1, max_length=20)


# 여러 데이터셋에 대한 합성 요청을 전달받아 일괄(배치) 작업을 시작함
@router.post('', summary='일괄(배치) 합성 작업 시작', description='여러 데이터셋에 대한 합성 요청을 전달받아 일괄(배치) 작업을 시작합니다.')
def start_batch(request: BatchRequest):
    try:
        return BatchService.start(request.requests)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# 최근 등록 및 실행된 일괄(배치) 합성 작업 목록을 조회함
@router.get('', summary='일괄 작업 목록 조회', description='최근 등록 및 실행된 일괄(배치) 합성 작업 목록을 조회합니다.')
def list_batches():
    return BatchService.list_recent()


# 특정 일괄 작업 ID의 하위 작업(Job) 목록과 진행 상태를 조회함
@router.get('/{batch_id}', summary='단일 일괄 작업 상세 조회', description='특정 일괄 작업 ID의 하위 작업(Job) 목록과 진행 상태를 조회합니다.')
def get_batch(batch_id: str):
    try:
        return BatchService.get(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# 진행 중인 일괄(배치) 작업과 해당 하위 작업들을 즉시 취소함
@router.post('/{batch_id}/cancel', summary='일괄 작업 취소', description='진행 중인 일괄(배치) 작업과 해당 하위 작업들을 즉시 취소합니다.')
def cancel_batch(batch_id: str):
    try:
        return BatchService.cancel(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# 일괄 작업의 통합 순서 넘버링 문서 ZIP을 다운로드함
@router.get('/{batch_id}/download-documents', summary='일괄 처리 문서 ZIP 다운로드', description='원천데이터, 합성데이터, 심의자료 문서가 순서대로 넘버링된 단일 압축파일을 다운로드합니다.')
def download_batch_documents(batch_id: str):
    from pathlib import Path
    from fastapi.responses import FileResponse
    try:
        snapshot = BatchService.get(batch_id)
        zip_path = snapshot.get('documents_zip') or snapshot.get('package_zip')
        if not zip_path or not Path(zip_path).is_file():
            raise HTTPException(status_code=404, detail="다운로드할 일괄 문서 파일이 아직 준비되지 않았거나 없습니다.")
        path = Path(zip_path).resolve()
        filename = f"일괄처리문서_{batch_id}.zip"
        return FileResponse(path=str(path), filename=filename, media_type="application/zip")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

