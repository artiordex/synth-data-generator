"""
파일명: datasets.py
경로: apps/api/src/synthetic_api/routes/v1/datasets.py
목적: 데이터 업로드·프로파일링·가명화 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from pathlib import Path
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
import pandas as pd

from synthetic_api.application.services.dataset_service import DatasetService
from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file
from synthetic_engine.profiling.pseudonym_input import read_pseudonym_input
from synthetic_engine import read_table, scan_pii_columns, ColumnPlan, apply_pii, evaluate_klt, export_pseudonymized_document

router = APIRouter(prefix="/datasets", tags=["datasets"])

class PseudonymizeRequest(BaseModel):
    file_name: str
    pii_actions: Dict[str, str] = {}  # col_name -> "faker" | "mask" | "hash" | "drop"
    export_format: str = "csv"  # csv, xlsx, tsv, json, parquet, pdf, hwp, hwpx, docx, md, txt
    project_id: str = Field(default="default", min_length=1, max_length=100)
    token_key_version: str = Field(default="v1", min_length=1, max_length=30)
    quasi_identifiers: list[str] = Field(default_factory=list)
    sensitive_columns: list[str] = Field(default_factory=list)
    k_threshold: int = Field(default=5, ge=2, le=100)
    l_threshold: int = Field(default=2, ge=2, le=100)
    t_threshold: float = Field(default=0.2, gt=0, le=1)

@router.post("/upload", summary="단일 원본 데이터 파일 업로드", description="CSV, XLSX, TSV, Parquet, JSON 등 원본 데이터 파일을 서버에 안전하게 업로드합니다.")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        res = DatasetService.save_upload_file(file.file, file.filename)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile", summary="데이터셋 프로파일링 및 PII 자동 탐지", description="업로드된 데이터셋의 컬럼 유형, 결측치, 통계량 및 개인정보(PII) 포함 여부를 정밀 분석합니다.")
async def profile_dataset(file_name: str, pseudonym: bool = False):
    try:
        confined_file(settings.UPLOAD_DIR / file_name, settings.UPLOAD_DIR)
        res = DatasetService.inspect_file(file_name, pseudonym=pseudonym)
        return res
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-batch", summary="복수 데이터셋 일괄 업로드 및 프로파일링", description="최대 20개의 데이터셋 파일을 한 번에 업로드하고 각각의 프로파일 정보를 일괄 분석합니다.")
def upload_batch(files: list[UploadFile] = File(...)):
    if not 1 <= len(files) <= 20:
        raise HTTPException(status_code=422, detail="한 번에 1~20개 파일을 선택하세요.")
    results = []
    for file in files:
        try:
            if Path(file.filename or '').suffix.lower() not in {
                '.csv', '.xlsx', '.xls', '.tsv', '.txt', '.json', '.jsonl', '.parquet', '.pq',
                '.pdf', '.hwp', '.hwpx', '.doc', '.docx', '.md'
            }:
                raise ValueError('CSV, XLSX, XLS, TSV, JSON, Parquet, PDF, HWP, HWPX, DOCX, MD 파일을 지원합니다.')
            saved = DatasetService.save_upload_file(file.file, file.filename, unique=True)
            profile = DatasetService.inspect_file(saved['filename'])
            results.append({**saved, 'profile': profile, 'error': None})
        except Exception as exc:
            results.append({'original_filename': file.filename, 'error': str(exc)})
        finally:
            file.file.close()
    return {'files': results}

@router.post("/pseudonymize", summary="정형 데이터 가명화 처리 및 다중 포맷 내보내기", description="컬럼별 가명처리 기법(Faker, 마스킹, 해시, 삭제, 토큰화)을 적용하고 프라이버시 평가 지표를 산출하여 원하는 포맷으로 내보냅니다.")
def pseudonymize_dataset(req: PseudonymizeRequest):
    src_path = confined_file(settings.UPLOAD_DIR / req.file_name, settings.UPLOAD_DIR)
    if src_path.suffix.lower() in {'.pdf', '.hwp', '.hwpx'}:
        raise HTTPException(status_code=422, detail='이 문서는 원본 서식 유지 편집으로 처리해야 합니다. /document-privacy API를 사용하세요.')
    allowed_formats = {'csv', 'xlsx', 'tsv', 'json', 'parquet', 'pdf', 'hwpx', 'docx', 'md', 'txt'}
    if req.export_format not in allowed_formats:
        raise HTTPException(status_code=422, detail='지원하지 않는 출력 형식입니다. HWP 입력은 HWPX로 내보내세요.')

    try:
        raw_df = read_pseudonym_input(src_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 로드 실패: {str(e)}")

    pii_detected = scan_pii_columns(raw_df)

    pii_plan: Dict[str, Dict[str, Any]] = {}
    for col, action in req.pii_actions.items():
        if col not in raw_df.columns or action not in {'faker', 'mask', 'hash', 'drop', 'token'}:
            raise HTTPException(status_code=422, detail='처리 항목 또는 처리방법이 올바르지 않습니다.')
        if col in raw_df.columns:
            pii_info = pii_detected.get(col, {})
            pii_type = pii_info.get("faker") or pii_info.get("type") or "unstructured_text"
            pii_plan[col] = {"action": action, "faker": pii_type, "pii_type": pii_type}

    plan = ColumnPlan(
        categorical=[],
        numerical=[],
        ignored=[],
        pii=pii_plan,
        rules={}
    )

    try:
        pseudo_df, summary = apply_pii(
            raw_df, plan, project_id=req.project_id, key_version=req.token_key_version)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가명화 처리 실패: {str(e)}")
    if not len(pseudo_df.columns):
        raise HTTPException(status_code=422, detail='출력할 항목이 하나 이상 필요합니다.')

    pseudo_dir = settings.OUTPUT_DIR / "pseudonymized"
    pseudo_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    stem = Path(req.file_name).stem
    fmt = req.export_format.lower().strip()
    ext_map = {
        "xlsx": "xlsx", "xls": "xlsx",
        "tsv": "tsv",
        "json": "json",
        "parquet": "parquet", "pq": "parquet",
        "pdf": "pdf",
        "hwp": "hwp",
        "hwpx": "hwpx",
        "hwpt": "hwpt",
        "docx": "docx", "doc": "docx",
        "md": "md",
        "txt": "txt",
    }
    out_ext = ext_map.get(fmt, "csv")
    out_name = f"pseudonymized_{stem}_{uid}.{out_ext}"
    out_path = pseudo_dir / out_name

    try:
        export_pseudonymized_document(
            pseudo_df,
            target_fmt=fmt,
            output_path=out_path,
            original_filename=src_path.name,
            original_filepath=None,
            replacements=None
        )
        if not out_path.is_file() or not out_path.stat().st_size:
            raise ValueError('출력 파일을 생성하지 못했습니다.')
        if fmt == 'pdf' and out_path.read_bytes()[:4] != b'%PDF':
            raise ValueError('유효한 PDF 파일이 아닙니다.')
        if fmt in {'docx', 'hwpx', 'xlsx'}:
            import zipfile
            with zipfile.ZipFile(out_path) as archive:
                expected = {'docx': 'word/document.xml', 'hwpx': 'Contents/section0.xml', 'xlsx': 'xl/workbook.xml'}[fmt]
                if expected not in archive.namelist():
                    raise ValueError('출력 형식 검증에 실패했습니다.')
    except Exception as exc:
        out_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f'내보내기 실패: {exc}') from exc
    download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
    privacy_metrics = evaluate_klt(
        pseudo_df, req.quasi_identifiers, req.sensitive_columns,
        k_threshold=req.k_threshold, l_threshold=req.l_threshold, t_threshold=req.t_threshold)

    # Record history
    hist_file = pseudo_dir / "pseudonym_history.json"
    history_list = []
    if hist_file.exists():
        try:
            import json
            with hist_file.open("r", encoding="utf-8") as f:
                history_list = json.load(f)
        except Exception:
            history_list = []

    from datetime import datetime
    history_entry = {
        "id": uid,
        "file_name": out_name,
        "original_file": req.file_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_count": len(pseudo_df),
        "columns_count": len(pseudo_df.columns),
        "pii_summary": summary,
        "privacy_metrics": privacy_metrics,
        "project_id": req.project_id,
        "export_format": fmt.upper(),
        "download_url": download_url
    }
    history_list.insert(0, history_entry)
    # keep last 50
    history_list = history_list[:50]
    try:
        import json
        with hist_file.open("w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {
        "status": "success",
        "file_name": out_name,
        "download_url": download_url,
        "rows_count": len(pseudo_df),
        "columns": list(pseudo_df.columns),
        "summary": summary,
        "privacy_metrics": privacy_metrics,
        "original_preview": raw_df.head(15).fillna("").to_dict(orient="records"),
        "pseudonymized_preview": pseudo_df.head(15).fillna("").to_dict(orient="records")
    }

@router.get("/pseudonymize/history", summary="가명화 처리 이력 조회", description="최근 수행된 가명화 작업 목록과 파일 다운로드 정보를 조회합니다.")
async def get_pseudonym_history():
    pseudo_dir = settings.OUTPUT_DIR / "pseudonymized"
    hist_file = pseudo_dir / "pseudonym_history.json"
    if not hist_file.exists():
        return []
    try:
        import json
        with hist_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

