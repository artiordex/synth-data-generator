from fastapi import APIRouter, HTTPException

from fastapi.responses import FileResponse

from pathlib import Path

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file



router = APIRouter(prefix="/files", tags=["files"])



@router.get("/download")

async def download_file(path: str):

    p = Path(path)

    if not p.is_absolute():

        p = settings.ROOT_DIR / path

        

    p = confined_file(p, settings.OUTPUT_DIR)

        

    return FileResponse(

        path=str(p),

        filename=p.name,

        media_type="application/octet-stream"

    )
