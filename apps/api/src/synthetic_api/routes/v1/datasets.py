from pathlib import Path
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
import pandas as pd

from synthetic_api.application.services.dataset_service import DatasetService
from synthetic_api.core.config import settings
from synthetic_engine import read_table, scan_pii_columns, ColumnPlan, apply_pii, evaluate_klt

router = APIRouter(prefix="/datasets", tags=["datasets"])

class PseudonymizeRequest(BaseModel):
    file_name: str
    pii_actions: Dict[str, str] = {}  # col_name -> "faker" | "mask" | "hash" | "drop"
    export_format: str = "csv"  # csv, xlsx
    project_id: str = Field(default="default", min_length=1, max_length=100)
    token_key_version: str = Field(default="v1", min_length=1, max_length=30)
    quasi_identifiers: list[str] = Field(default_factory=list)
    sensitive_columns: list[str] = Field(default_factory=list)
    k_threshold: int = Field(default=5, ge=2, le=100)
    l_threshold: int = Field(default=2, ge=2, le=100)
    t_threshold: float = Field(default=0.2, gt=0, le=1)

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        res = DatasetService.save_upload_file(file.file, file.filename)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
async def profile_dataset(file_name: str):
    try:
        res = DatasetService.inspect_file(file_name)
        return res
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-batch")
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

@router.post("/pseudonymize")
async def pseudonymize_dataset(req: PseudonymizeRequest):
    src_path = settings.UPLOAD_DIR / req.file_name
    if not src_path.exists():
        src_path = Path(req.file_name)
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="원본 파일을 찾을 수 없습니다.")

    try:
        raw_df = read_table(src_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 로드 실패: {str(e)}")

    pii_detected = scan_pii_columns(raw_df)

    pii_plan: Dict[str, Dict[str, Any]] = {}
    for col, action in req.pii_actions.items():
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

    pseudo_dir = settings.OUTPUT_DIR / "pseudonymized"
    pseudo_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    stem = Path(req.file_name).stem
    fmt = req.export_format.lower()

    if fmt in ("xlsx", "xls"):
        out_name = f"pseudonymized_{stem}_{uid}.xlsx"
        out_path = pseudo_dir / out_name
        pseudo_df.to_excel(out_path, index=False)
    elif fmt == "tsv":
        out_name = f"pseudonymized_{stem}_{uid}.tsv"
        out_path = pseudo_dir / out_name
        pseudo_df.to_csv(out_path, sep="\t", index=False, encoding="utf-8-sig")
    elif fmt == "json":
        out_name = f"pseudonymized_{stem}_{uid}.json"
        out_path = pseudo_dir / out_name
        pseudo_df.to_json(out_path, orient="records", force_ascii=False, indent=2)
    elif fmt in ("parquet", "pq"):
        out_name = f"pseudonymized_{stem}_{uid}.parquet"
        out_path = pseudo_dir / out_name
        pseudo_df.to_parquet(out_path, index=False)
    else:
        out_name = f"pseudonymized_{stem}_{uid}.csv"
        out_path = pseudo_dir / out_name
        pseudo_df.to_csv(out_path, index=False, encoding="utf-8-sig")
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

@router.get("/pseudonymize/history")
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

