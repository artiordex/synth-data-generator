from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.domain.models.job import JobStatus
from app.api.dependencies import get_job_repo
from app.infrastructure.repositories.job_repo_impl import JobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=List[JobStatus])
async def list_jobs(repo: JobRepository = Depends(get_job_repo)):
    return repo.list_all()

@router.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job
