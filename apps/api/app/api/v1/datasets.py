from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
from app.application.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])

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
