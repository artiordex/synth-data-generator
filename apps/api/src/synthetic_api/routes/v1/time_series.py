from pathlib import Path
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from synthetic_api.core.config import settings
from synthetic_engine import PanelTimeSeriesSynthesizer, read_table

router = APIRouter(prefix="/time-series", tags=["time-series-synthesis"])

class TimeSeriesRequest(BaseModel):
    file_name: str
    entity_column: str
    time_column: str
    target_entities: int | None = Field(default=None, ge=1, le=100000)
    seed: int = 42

@router.post("/generate")
def generate_time_series(req: TimeSeriesRequest):
    path = settings.UPLOAD_DIR / Path(req.file_name).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="업로드 파일을 찾을 수 없습니다.")
    try:
        raw = read_table(path)
        output = PanelTimeSeriesSynthesizer(req.seed).sample(
            raw, entity_column=req.entity_column, time_column=req.time_column,
            target_entities=req.target_entities)
        name = f"timeseries-{uuid.uuid4().hex[:8]}.csv"
        target = settings.OUTPUT_DIR / name
        output.to_csv(target, index=False, encoding="utf-8-sig")
        lengths = output.groupby(req.entity_column).size()
        return {"status": "completed", "rows": len(output), "entities": int(lengths.size),
                "min_observations": int(lengths.min()), "max_observations": int(lengths.max()),
                "columns": list(output.columns), "preview": output.head(10).fillna("").to_dict(orient="records"),
                "download_url": f"/api/v1/files/download?path={target.as_posix()}"}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

