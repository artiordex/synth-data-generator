"""
파일명: batches.py
경로: apps/api/src/synthetic_api/routes/v1/batches.py
목적: 합성 작업 일괄 실행 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from synthetic_api.domain.models.job import SynthesisRequest
from synthetic_api.application.services.batch_service import BatchService

router = APIRouter(prefix='/batches', tags=['batches'])


class BatchRequest(BaseModel):
    requests: list[SynthesisRequest] = Field(min_length=1, max_length=20)


@router.post('', summary='일괄(배치) 합성 작업 시작', description='여러 데이터셋에 대한 합성 요청을 전달받아 일괄(배치) 작업을 시작합니다.')
def start_batch(request: BatchRequest):
    try:
        return BatchService.start(request.requests)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get('', summary='일괄 작업 목록 조회', description='최근 등록 및 실행된 일괄(배치) 합성 작업 목록을 조회합니다.')
def list_batches():
    return BatchService.list_recent()


@router.get('/{batch_id}', summary='단일 일괄 작업 상세 조회', description='특정 일괄 작업 ID의 하위 작업(Job) 목록과 진행 상태를 조회합니다.')
def get_batch(batch_id: str):
    try:
        return BatchService.get(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post('/{batch_id}/cancel', summary='일괄 작업 취소', description='진행 중인 일괄(배치) 작업과 해당 하위 작업들을 즉시 취소합니다.')
def cancel_batch(batch_id: str):
    try:
        return BatchService.cancel(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
