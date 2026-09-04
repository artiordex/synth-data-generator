from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/download")
async def download_file(path: str):
    p = Path(path)
    if not p.is_absolute():
        p = settings.ROOT_DIR / path
        
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="application/octet-stream"
    )
