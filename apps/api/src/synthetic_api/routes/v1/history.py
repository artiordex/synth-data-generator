"""
파일명: history.py
경로: apps/api/src/synthetic_api/routes/v1/history.py
목적: 통합 작업 이력 조회·삭제 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
import json

from fastapi import APIRouter, HTTPException

from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.db.models import AuditLogEntity, BatchEntity, JobEntity
from synthetic_api.infrastructure.db.session import SessionLocal


router = APIRouter(prefix="/history", tags=["history"])


class DeleteHistoryItem(BaseModel):
    type: str
    id: str
    filename: Optional[str] = None


class DeleteSelectedHistoryRequest(BaseModel):
    items: List[DeleteHistoryItem]


@router.post("/delete-selected", summary="선택한 작업 이력 항목 삭제", description="체크박스로 선택한 특정 합성 작업, 배치, 가명화, 더미, 변환 이력 항목들을 데이터베이스 및 이력 파일에서 삭제합니다.")
def delete_selected_history(req: DeleteSelectedHistoryRequest):
    """Delete selectively chosen history items."""
    job_ids_to_delete = []
    batch_ids_to_delete = []
    pseudo_ids = set()
    dummy_ids = set()
    conv_ids = set()

    for it in req.items:
        t = it.type
        raw_id = it.id
        if raw_id.startswith("synth-"):
            raw_id = raw_id[len("synth-"):]
        elif raw_id.startswith("pseudo-"):
            raw_id = raw_id[len("pseudo-"):]
        elif raw_id.startswith("dummy-"):
            raw_id = raw_id[len("dummy-"):]
        elif raw_id.startswith("conv-"):
            raw_id = raw_id[len("conv-"):]

        if t in ("synthetic", "job"):
            job_ids_to_delete.append(raw_id)
        elif t == "batch":
            batch_ids_to_delete.append(raw_id)
        elif t == "pseudo":
            pseudo_ids.add(raw_id)
            if it.filename:
                pseudo_ids.add(it.filename)
        elif t == "dummy":
            dummy_ids.add(raw_id)
            if it.filename:
                dummy_ids.add(it.filename)
        elif t == "converter":
            conv_ids.add(raw_id)
            if it.filename:
                conv_ids.add(it.filename)

    deleted_counts = {
        "jobs": 0,
        "batches": 0,
        "pseudo": 0,
        "dummy": 0,
        "converter": 0,
    }

    with SessionLocal() as db:
        if job_ids_to_delete:
            db.query(AuditLogEntity).filter(AuditLogEntity.job_id.in_(job_ids_to_delete)).delete(synchronize_session=False)
            deleted_jobs = db.query(JobEntity).filter(JobEntity.id.in_(job_ids_to_delete)).delete(synchronize_session=False)
            deleted_counts["jobs"] = deleted_jobs
        if batch_ids_to_delete:
            deleted_batches = db.query(BatchEntity).filter(BatchEntity.id.in_(batch_ids_to_delete)).delete(synchronize_session=False)
            deleted_counts["batches"] = deleted_batches
        db.commit()

    def _filter_json_file(file_path: Path, target_set: set) -> int:
        if not file_path.exists() or not target_set:
            return 0
        try:
            entries = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                return 0
            original_len = len(entries)
            filtered = [
                e for e in entries
                if str(e.get("id", "")) not in target_set
                and str(e.get("file_name", "")) not in target_set
                and str(e.get("output_filename", "")) not in target_set
            ]
            file_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
            return original_len - len(filtered)
        except Exception:
            return 0

    if pseudo_ids:
        deleted_counts["pseudo"] = _filter_json_file(
            settings.OUTPUT_DIR / "pseudonymized" / "pseudonym_history.json", pseudo_ids
        )
    if dummy_ids:
        deleted_counts["dummy"] = _filter_json_file(
            settings.OUTPUT_DIR / "dummy" / "dummy_history.json", dummy_ids
        )
    if conv_ids:
        deleted_counts["converter"] = _filter_json_file(
            settings.OUTPUT_DIR / "converted" / "converter_history.json", conv_ids
        )

    return {"status": "success", "deleted": deleted_counts}


@router.delete("", summary="전체 작업 이력 초기화", description="진행 중인 작업이 없는 상태에서 모든 합성/가명화/더미/변환 이력 인덱스를 초기화합니다(생성된 원본 파일은 보존).")
def clear_all_history():
    """Clear history indexes while preserving generated files and templates."""
    with SessionLocal() as db:
        running_jobs = db.query(JobEntity).filter(JobEntity.status.in_(["pending", "processing"])).count()
        running_batches = db.query(BatchEntity).filter(BatchEntity.status.in_(["pending", "processing"])).count()
        if running_jobs or running_batches:
            raise HTTPException(status_code=409, detail="진행 중인 작업이 있어 이력을 삭제할 수 없습니다.")

        counts = {
            "jobs": db.query(JobEntity).count(),
            "audit_logs": db.query(AuditLogEntity).count(),
            "batches": db.query(BatchEntity).count(),
        }
        db.query(AuditLogEntity).delete(synchronize_session=False)
        db.query(BatchEntity).delete(synchronize_session=False)
        db.query(JobEntity).delete(synchronize_session=False)
        db.commit()

    for history_file in (
        settings.OUTPUT_DIR / "pseudonymized" / "pseudonym_history.json",
        settings.OUTPUT_DIR / "dummy" / "dummy_history.json",
        settings.OUTPUT_DIR / "converted" / "converter_history.json",
    ):
        if history_file.exists():
            try:
                entries = json.loads(history_file.read_text(encoding="utf-8"))
                counts[history_file.stem] = len(entries) if isinstance(entries, list) else 0
            except (json.JSONDecodeError, OSError):
                counts[history_file.stem] = 0
            history_file.write_text("[]\n", encoding="utf-8")

    return {"status": "cleared", "deleted": counts, "generated_files_preserved": True}
