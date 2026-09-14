# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: files.py
# 경로: apps/api/src/synthetic_api/routes/v1/files.py
# 목적: 원본 및 결과 파일 업로드, 다운로드 파일 관리 API 엔드포인트를 제공함
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-14
# =============================================================================
from fastapi import APIRouter, HTTPException

from fastapi.responses import FileResponse, Response

from pathlib import Path

from pathlib import Path

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file



import mimetypes

router = APIRouter(prefix="/files", tags=["files"])


# 생성된 결과 파일 또는 원본 파일을 클라이언트에 안전하게 스트리밍 다운로드함
@router.get("/download", summary="산출물 파일 안전 다운로드", description="합성 데이터, 가명화 파일, 원본 문서 등 저장소 내의 파일을 안전하게 제공합니다.")
async def download_file(path: str):
    p = Path(path)
    if not p.is_absolute():
        p = settings.ROOT_DIR / path
    p = confined_file(p, [settings.OUTPUT_DIR, settings.STORAGE_DIR])
    media_type, _ = mimetypes.guess_type(p.name)
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type=media_type or "application/octet-stream"
    )


# 다운로드 요청 대상 파일의 존재 여부와 접근 유효성을 사전 검증함
@router.head("/download", summary="산출물 파일 다운로드 가능 여부 확인")
async def check_download_file(path: str):
    p = Path(path)
    if not p.is_absolute():
        p = settings.ROOT_DIR / path
    p = confined_file(p, [settings.OUTPUT_DIR, settings.STORAGE_DIR])
    return Response(headers={
        "Content-Length": str(p.stat().st_size),
    })
