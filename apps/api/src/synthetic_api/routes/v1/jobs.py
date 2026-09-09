"""
파일명: jobs.py
경로: apps/api/src/synthetic_api/routes/v1/jobs.py
목적: 합성 작업 상태와 평가 결과 조회 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
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

@router.get("", response_model=List[JobStatus], summary="전체 합성 작업 목록 조회", description="등록된 모든 합성 작업(Job)의 상태, 진행률, 생성일시 목록을 조회합니다.")
async def list_jobs(repo: JobRepository = Depends(get_job_repo)):
    return repo.list_all()

@router.get("/{job_id}", response_model=JobStatus, summary="단일 합성 작업 상세 조회", description="작업 ID로 특정 합성 작업의 세부 진행 상태, 산출물 경로, 오류 메시지 등을 조회합니다.")
async def get_job(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job

@router.get("/{job_id}/distributions", summary="원본 vs 합성 데이터 컬럼 분포 비교 데이터 조회", description="원본 데이터와 생성된 합성 데이터의 각 컬럼별 히스토그램 및 빈도수 분포 데이터를 조회합니다.")
async def get_job_distributions(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    # 1. Try reading precomputed distributions from evaluation report json
    review_folder = (job.package_folders.get("심의자료") or job.package_folders.get("심의위원회 심의자료")) if job.package_folders else None
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

@router.get("/{job_id}/assessment", summary="합성 데이터 품질 및 안전성 심의 평가 리포트 조회", description="자동 생성된 심의위원회 평가 리포트(품질 점수, 안전성, 유용성, 가드레일 통과 여부)를 조회합니다.")
async def get_job_assessment(job_id: str, repo: JobRepository = Depends(get_job_repo)):
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    review_folder = (job.package_folders.get("심의자료") or job.package_folders.get("심의위원회 심의자료")) if job.package_folders else None
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
