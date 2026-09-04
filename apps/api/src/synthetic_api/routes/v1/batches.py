from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from synthetic_api.domain.models.job import SynthesisRequest
from synthetic_api.application.services.batch_service import BatchService

router = APIRouter(prefix='/batches', tags=['batches'])


class BatchRequest(BaseModel):
    requests: list[SynthesisRequest] = Field(min_length=1, max_length=20)


@router.post('')
def start_batch(request: BatchRequest):
    try:
        return BatchService.start(request.requests)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get('')
def list_batches():
    return BatchService.list_recent()


@router.get('/{batch_id}')
def get_batch(batch_id: str):
    try:
        return BatchService.get(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post('/{batch_id}/cancel')
def cancel_batch(batch_id: str):
    try:
        return BatchService.cancel(batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
