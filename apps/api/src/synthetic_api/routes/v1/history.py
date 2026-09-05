import json

from fastapi import APIRouter, HTTPException

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.db.models import AuditLogEntity, BatchEntity, JobEntity
from synthetic_api.infrastructure.db.session import SessionLocal


router = APIRouter(prefix="/history", tags=["history"])


@router.delete("")
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
