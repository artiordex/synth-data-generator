import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
import pandas as pd

from synthetic_api.domain.models.job import JobStatus
from synthetic_api.routes.dependencies import get_job_repo
from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository
from synthetic_engine import compute_column_distributions, read_table, infer_columns, build_column_plan

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

@router.get("/{job_id}/distributions")
async def get_job_distributions(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    # 1. Try reading precomputed distributions from evaluation report json
    review_folder = job.package_folders.get("심의위원회 심의자료") if job.package_folders else None
    if review_folder:
        rev_path = Path(review_folder)
        if rev_path.exists():
            for report_file in rev_path.glob("*evaluation_report.json"):
                try:
                    with report_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    dists = data.get("column_distributions") or data.get("utility", {}).get("column_distributions")
                    if dists:
                        return {"job_id": job_id, "columns": dists}
                except Exception:
                    pass

    # 2. Fallback: on-the-fly calculation from original & synthetic files if available
    try:
        orig_folder = job.package_folders.get("원본데이터") if job.package_folders else None
        synth_folder = job.package_folders.get("합성데이터") if job.package_folders else None
        
        orig_csv = next(Path(orig_folder).glob("*.csv"), None) if orig_folder and Path(orig_folder).exists() else None
        synth_csv = next(Path(synth_folder).glob("*.csv"), None) if synth_folder and Path(synth_folder).exists() else None

        if orig_csv and synth_csv:
            orig_df = read_table(orig_csv)
            synth_df = read_table(synth_csv)
            plan = build_column_plan({}, orig_df)
            dists = compute_column_distributions(orig_df, synth_df, plan)
            return {"job_id": job_id, "columns": dists}
    except Exception as e:
        pass

    return {"job_id": job_id, "columns": []}

@router.get("/{job_id}/assessment")
async def get_job_assessment(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    review_folder = job.package_folders.get("심의위원회 심의자료") if job.package_folders else None
    if not review_folder:
        return {"job_id": job_id, "assessment": None}

    rev_path = Path(review_folder)
    if not rev_path.exists():
        return {"job_id": job_id, "assessment": None}

    for report_file in rev_path.glob("*evaluation_report.json"):
        try:
            with report_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "job_id": job_id,
                "assessment": data.get("auto_assessment") or data.get("assessment"),
                "quality_score": data.get("quality_score") or data.get("overall_quality"),
                "safety": data.get("safety", {}),
                "utility": data.get("utility", {}),
                "guardrails": data.get("guardrails", {}),
                "config": data.get("config", {}),
            }
        except Exception:
            pass

    return {"job_id": job_id, "assessment": None}
