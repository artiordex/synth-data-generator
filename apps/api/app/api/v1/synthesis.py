from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.domain.models.job import JobStatus, SynthesisRequest
from app.application.services.synthesis_service import SynthesisService
from app.api.dependencies import get_job_repo
from app.infrastructure.repositories.job_repo_impl import JobRepository

router = APIRouter(prefix="/synthesis", tags=["synthesis"])

@router.post("/start", response_model=JobStatus)
async def start_synthesis(req: SynthesisRequest):
    try:
        job = SynthesisService.create_job(req)
        SynthesisService.start_pipeline_async(job.id, req)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{job_id}")
async def cancel_synthesis(job_id: str):
    ok = SynthesisService.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail="작업을 취소할 수 없거나 이미 완료되었습니다.")
    return {"status": "canceled", "job_id": job_id}
