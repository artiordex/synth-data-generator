"""
파일명: synthesis.py
경로: apps/api/src/synthetic_api/routes/v1/synthesis.py
목적: 단일 합성 모델 비교·실행·취소 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from synthetic_api.domain.models.job import JobStatus, SynthesisRequest

from synthetic_api.application.services.synthesis_service import SynthesisService

from synthetic_api.routes.dependencies import get_job_repo

from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository
from synthetic_api.core.config import settings
from pydantic import BaseModel, Field
from pathlib import Path
from time import perf_counter
from synthetic_engine import (read_table, build_column_plan, prepare_training_frame,
                              get_synthesizer, evaluate)



router = APIRouter(prefix="/synthesis", tags=["synthesis"])


class CompareModelsRequest(BaseModel):
    file_name: str
    candidates: list[str] = Field(default_factory=lambda: ["statistical", "gaussian_copula", "ctgan", "tvae"])
    sample_rows: int = Field(default=300, ge=50, le=1000)


@router.post("/compare-models", summary="합성 모델(Statistical, Copula, CTGAN, TVAE) 축소 벤치마크 및 비교", description="Statistical, Gaussian Copula, CTGAN, TVAE 모델을 샘플 데이터로 축소 학습하여 분포 적합도, 상관관계 보존 점수를 측정하고 최적 모델을 추천합니다.")
def compare_models(req: CompareModelsRequest):
    path = settings.UPLOAD_DIR / Path(req.file_name).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="업로드 파일을 찾을 수 없습니다.")
    source = read_table(path)
    raw = source.sample(n=min(1000, len(source)), random_state=42)
    plan = build_column_plan({}, raw)
    training = prepare_training_frame(raw, plan, [])
    rows = min(req.sample_rows, max(len(training), 50))
    allowed = {"statistical", "gaussian_copula", "ctgan", "tvae"}
    leaderboard = []
    for name in req.candidates:
        if name not in allowed:
            continue
        started = perf_counter()
        try:
            kwargs = {"epochs": 5, "batch_size": 50, "enable_gpu": False} if name in {"ctgan", "tvae"} else {}
            if name == "ctgan": kwargs["pac"] = 1
            model = get_synthesizer(name, **kwargs)
            model.fit(training, plan)
            synthetic = model.sample(rows)
            report = evaluate(training, synthetic, plan, run_anonymeter_eval=False)
            distribution = 1.0 - float(report["utility"]["jsd_mean"])
            correlation = float(report["utility"]["correlation"].get("overall_correlation_score", 0))
            score = max(0.0, min(1.0, distribution * 0.6 + correlation * 0.4))
            leaderboard.append({"model_type": name, "status": "completed", "score": round(score, 4),
                                "distribution_quality": round(distribution, 4), "correlation_score": round(correlation, 4),
                                "duration_seconds": round(perf_counter() - started, 3)})
        except Exception as exc:
            leaderboard.append({"model_type": name, "status": "failed", "score": None,
                                "duration_seconds": round(perf_counter() - started, 3), "error": str(exc)})
    leaderboard.sort(key=lambda item: item["score"] if item["score"] is not None else -1, reverse=True)
    recommended = next((item["model_type"] for item in leaderboard if item["status"] == "completed"), None)
    return {"recommended_model": recommended, "sample_rows": rows, "leaderboard": leaderboard,
            "note": "축소 학습 비교 결과입니다. 최종 실행 후 전체 안전성·유용성 평가를 다시 확인하세요."}



@router.post("/start", response_model=JobStatus, summary="합성 데이터 생성 파이프라인 비동기 실행", description="지정한 데이터셋과 설정 파라미터(모델 종류, 행 수, 차분 프라이버시 등)를 바탕으로 데이터 합성 백그라운드 작업을 생성하고 시작합니다.")

async def start_synthesis(req: SynthesisRequest):

    try:

        job = SynthesisService.create_job(req)

        SynthesisService.start_pipeline_async(job.id, req)

        return job

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/cancel/{job_id}", summary="진행 중인 합성 작업 취소", description="실행 중이거나 대기 중인 데이터 합성 작업(Job)을 중단 처리합니다.")

async def cancel_synthesis(job_id: str):

    ok = SynthesisService.cancel_job(job_id)

    if not ok:

        raise HTTPException(status_code=400, detail="작업을 취소할 수 없거나 이미 완료되었습니다.")

    return {"status": "canceled", "job_id": job_id}
