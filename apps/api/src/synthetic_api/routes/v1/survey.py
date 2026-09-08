# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from synthetic_api.core.config import settings
from synthetic_api.core.logging import logger
from synthetic_api.infrastructure.file_access import confined_file
from synthetic_engine import SurveyFusionEngine, SurveyModuleMeta, read_table


router = APIRouter(prefix="/survey", tags=["survey-synthesis"])

SURVEY_JOBS: Dict[str, Dict[str, Any]] = {}


class SurveyInspectRequest(BaseModel):
    file_names: List[str] = Field(min_length=2, max_length=30)


class SurveyGenerateRequest(BaseModel):
    file_names: List[str] = Field(min_length=2, max_length=30)
    target_rows: int = Field(default=1000, ge=10, le=100000)
    model_type: str = Field(default="ctgan")
    epochs: Optional[int] = Field(default=30, ge=1)
    batch_size: Optional[int] = Field(default=64, ge=10)
    pac: Optional[int] = Field(default=1, ge=1)
    seed: int = Field(default=42, ge=0)
    target_region: Optional[str] = None
    apply_logic_rules: bool = True
    preserve_likert_order: bool = True
    protect_k_anonymity: bool = True
    dp_enabled: bool = False
    eps: float = Field(default=1.0, ge=0.01)
    department_name: str = "설문조사 분석팀"
    project_purpose: str = "다중 모듈 설문 합성데이터 증강 및 분석"


def _load_survey_tables(file_names: List[str]) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    for fn in file_names:
        path = settings.UPLOAD_DIR / Path(fn).name
        if not path.exists():
            path = Path(fn)
        if not path.exists():
            raise FileNotFoundError(f"업로드 파일을 찾을 수 없습니다: {fn}")
        key = Path(fn).stem
        candidate, suffix = key, 2
        while candidate in tables:
            candidate, suffix = f"{key}_{suffix}", suffix + 1
        tables[candidate] = read_table(path)
    return tables


@router.post("/inspect")
def inspect_survey_modules(req: SurveyInspectRequest):
    """
    다중 설문 파일들을 업로드한 후 공통 키, 1:1 행 매핑 정합성, 조건부 분기 규칙, 리커트 척도를 자동 분석합니다.
    """
    try:
        tables = _load_survey_tables(req.file_names)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"데이터 로드 실패: {exc}")

    try:
        inspect_res = SurveyFusionEngine.inspect_modules(tables)
        return {
            "modules": inspect_res.modules,
            "common_keys": inspect_res.common_keys,
            "is_aligned": inspect_res.is_aligned,
            "total_rows": inspect_res.total_rows,
            "total_columns": inspect_res.total_columns,
            "preview_columns": inspect_res.preview_columns,
            "sample_preview": inspect_res.sample_preview,
            "detected_rules": inspect_res.detected_rules,
            "likert_columns_count": inspect_res.likert_columns_count,
            "likert_column_names": inspect_res.likert_column_names,
            "k_anonymity_risk": inspect_res.k_anonymity_risk,
            "available_regions": inspect_res.available_regions,
        }
    except Exception as exc:
        logger.exception(f"Survey inspection failed: {exc}")
        raise HTTPException(status_code=500, detail=f"설문 모듈 분석 오류: {exc}")


def _run_survey_synthesis_task(job_id: str, req: SurveyGenerateRequest):
    try:
        SURVEY_JOBS[job_id]["status"] = "processing"
        SURVEY_JOBS[job_id]["progress"] = 10
        SURVEY_JOBS[job_id]["message"] = "설문 모듈 로드 및 통합 와이드 테이블 구성 중..."

        tables = _load_survey_tables(req.file_names)
        inspect_res = SurveyFusionEngine.inspect_modules(tables)
        fused_raw, module_metas = SurveyFusionEngine.fuse_tables(tables, inspect_res.common_keys)

        def progress_cb(pct: int, msg: str):
            SURVEY_JOBS[job_id]["progress"] = pct
            SURVEY_JOBS[job_id]["message"] = msg

        # 조건부 지역 설정 (다지역 풀링 시 특정 지역 샘플링)
        conditions = None
        if req.target_region and req.target_region != "전체" and "지역" in fused_raw.columns:
            # 원본 데이터 내 매칭되는 지역명 탐색 (공백 유연 처리)
            for r_val in fused_raw["지역"].dropna().unique():
                if str(r_val).strip() == req.target_region.strip():
                    conditions = {"지역": r_val}
                    break
            if not conditions:
                conditions = {"지역": req.target_region}

        # 합성 생성 실행 (분기 규칙 교정 & 리커트 순서 보존 적용)
        fused_syn, extra_meta = SurveyFusionEngine.synthesize_fused_survey(
            fused_raw=fused_raw,
            target_rows=req.target_rows,
            model_type=req.model_type,
            epochs=req.epochs or 30,
            batch_size=req.batch_size or 64,
            pac=req.pac or 1,
            seed=req.seed,
            apply_logic_rules=req.apply_logic_rules,
            preserve_likert_order=req.preserve_likert_order,
            protect_k_anonymity=req.protect_k_anonymity,
            conditions=conditions,
            custom_rules=inspect_res.detected_rules,
            progress_callback=progress_cb
        )

        progress_cb(88, "개별 설문 모듈별 역분할(Split) 및 엑셀 저장 중...")
        split_tables = SurveyFusionEngine.split_synthesized(fused_syn, module_metas)

        # 결과 저장 디렉토리 생성
        job_dir = settings.OUTPUT_DIR / f"survey_{job_id}"
        syn_dir = job_dir / "합성데이터"
        report_dir = job_dir / "품질보고서"
        syn_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        # 1. 개별 파일 저장
        split_files_info = []
        for meta in module_metas:
            sub_df = split_tables[meta.file_key]
            out_fname = meta.original_filename if meta.original_filename.endswith(".xlsx") else f"{meta.original_filename}.xlsx"
            out_file_path = syn_dir / out_fname
            sub_df.to_excel(out_file_path, index=False, sheet_name=meta.sheet_name)
            split_files_info.append({
                "file_key": meta.file_key,
                "filename": out_fname,
                "rows": len(sub_df),
                "columns": len(sub_df.columns),
                "download_url": f"/api/v1/survey/file/{job_id}/{out_fname}"
            })

        # 2. 통합 전체 와이드 파일 저장
        fused_fname = "00_통합_전체설문_합성데이터.xlsx"
        fused_path = syn_dir / fused_fname
        fused_syn.to_excel(fused_path, index=False, sheet_name="통합_설문합성데이터")
        split_files_info.insert(0, {
            "file_key": "통합_전체데이터",
            "filename": fused_fname,
            "rows": len(fused_syn),
            "columns": len(fused_syn.columns),
            "download_url": f"/api/v1/survey/file/{job_id}/{fused_fname}"
        })

        # 3. 종합 품질 및 무결성 평가 리포트 생성 (JSON + 다중 시트 Excel 평가서)
        eval_metrics = SurveyFusionEngine.evaluate_survey_synthesis(
            fused_raw, fused_syn, inspect_res.common_keys, inspect_res.detected_rules
        )
        report_file_path = report_dir / "설문_합성품질_평가결과.json"
        with open(report_file_path, "w", encoding="utf-8") as rf:
            json.dump({**eval_metrics, "extra_meta": extra_meta}, rf, ensure_ascii=False, indent=2)

        # 심의용 적정성 평가서 엑셀 생성
        report_excel_fname = "00_설문_합성품질_적정성_평가서.xlsx"
        report_excel_path = report_dir / report_excel_fname
        SurveyFusionEngine.generate_excel_compliance_report(eval_metrics, fused_raw, fused_syn, report_excel_path)
        
        # 다운로드 편의를 위해 합성데이터 디렉토리에도 복사
        shutil.copy(report_excel_path, syn_dir / report_excel_fname)

        # 4. ZIP 압축 파일 생성
        zip_path = job_dir / f"설문_합성데이터_패키지_{job_id}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(job_dir):
                for f in files:
                    if f.endswith(".zip"):
                        continue
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(job_dir)
                    zip_file.write(full_p, rel_p)

        SURVEY_JOBS[job_id]["status"] = "completed"
        SURVEY_JOBS[job_id]["progress"] = 100
        SURVEY_JOBS[job_id]["message"] = "설문 통합 합성 및 논리 무결성 검증 완료"
        SURVEY_JOBS[job_id]["tables"] = split_files_info
        SURVEY_JOBS[job_id]["quality"] = eval_metrics
        SURVEY_JOBS[job_id]["logic_integrity"] = eval_metrics.get("logic_integrity", {})
        SURVEY_JOBS[job_id]["k_anonymity"] = eval_metrics.get("k_anonymity", {})
        SURVEY_JOBS[job_id]["extra_meta"] = extra_meta
        SURVEY_JOBS[job_id]["download_url"] = f"/api/v1/survey/download/{job_id}"
        SURVEY_JOBS[job_id]["report_download_url"] = f"/api/v1/survey/file/{job_id}/{report_excel_fname}"
        SURVEY_JOBS[job_id]["zip_path"] = str(zip_path)
        logger.info(f"Survey synthesis job {job_id} completed with multi-region & compliance report.")

    except Exception as exc:
        logger.exception(f"Survey synthesis job {job_id} failed: {exc}")
        SURVEY_JOBS[job_id]["status"] = "failed"
        SURVEY_JOBS[job_id]["progress"] = 0
        SURVEY_JOBS[job_id]["message"] = f"오류 발생: {exc}"
        SURVEY_JOBS[job_id]["error"] = str(exc)


@router.post("/generate")
def generate_survey_synthesis(req: SurveyGenerateRequest):
    job_id = f"survey-{uuid.uuid4().hex[:8]}"
    SURVEY_JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "작업 시작 대기 중...",
        "target_rows": req.target_rows,
        "model_type": req.model_type,
        "file_count": len(req.file_names),
        "target_region": req.target_region,
        "apply_logic_rules": req.apply_logic_rules,
        "preserve_likert_order": req.preserve_likert_order,
    }

    t = threading.Thread(target=_run_survey_synthesis_task, args=(job_id, req), daemon=True)
    t.start()

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "설문 통합 합성 및 무결성 보정 작업이 등록되었습니다."
    }


@router.get("/status/{job_id}")
def get_survey_job_status(job_id: str):
    job = SURVEY_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="존재하지 않는 작업 ID입니다.")
    return job


@router.get("/download/{job_id}")
def download_survey_package(job_id: str):
    job = SURVEY_JOBS.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=404, detail="작업이 완료되지 않았거나 존재하지 않습니다.")

    zip_path = confined_file(Path(job.get("zip_path", "")), settings.OUTPUT_DIR)

    return FileResponse(
        path=zip_path,
        filename=f"설문_합성데이터_패키지_{job_id}.zip",
        media_type="application/zip"
    )


@router.get("/file/{job_id}/{filename}")
def download_survey_single_file(job_id: str, filename: str):
    job = SURVEY_JOBS.get(job_id)
    if not job or job.get('status') != 'completed':
        raise HTTPException(status_code=404, detail="완료된 작업을 찾을 수 없습니다.")
    job_dir = settings.OUTPUT_DIR / f"survey_{job_id}" / "합성데이터"
    file_path = confined_file(confined_file(job_dir / filename, settings.OUTPUT_DIR), job_dir)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
