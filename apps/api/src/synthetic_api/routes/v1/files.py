"""
파일명: files.py
경로: apps/api/src/synthetic_api/routes/v1/files.py
목적: 허용된 저장소의 파일 다운로드 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from fastapi import APIRouter, HTTPException

from fastapi.responses import FileResponse

from pathlib import Path

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file



router = APIRouter(prefix="/files", tags=["files"])



@router.get("/download", summary="산출물 파일 안전 다운로드", description="합성 데이터, 가명화 파일, 심의 리포트 등 저장소 내의 결과물 파일을 안전하게 다운로드합니다.")

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
