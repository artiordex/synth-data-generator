"""
파일명: router.py
경로: apps/api/src/synthetic_api/routes/v1/router.py
목적: 버전 1 API 라우터를 기능별 라우터로 조합함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from fastapi import APIRouter
from .datasets import router as datasets_router
from .synthesis import router as synthesis_router
from .jobs import router as jobs_router
from .files import router as files_router
from .review import router as review_router
from .dummy import router as dummy_router
from .glossary import router as glossary_router
from .batches import router as batches_router
from .relational import router as relational_router
from .time_series import router as time_series_router
from .history import router as history_router
from .converter import router as converter_router
from .survey import router as survey_router
from .system import router as system_router
from .document_privacy import router as document_privacy_router

api_router = APIRouter()
api_router.include_router(document_privacy_router)
api_router.include_router(datasets_router)
api_router.include_router(synthesis_router)
api_router.include_router(jobs_router)
api_router.include_router(files_router)
api_router.include_router(review_router)
api_router.include_router(dummy_router)
api_router.include_router(batches_router)
api_router.include_router(relational_router)
api_router.include_router(time_series_router)
api_router.include_router(history_router)
api_router.include_router(converter_router)
api_router.include_router(survey_router)
api_router.include_router(system_router)
api_router.include_router(glossary_router, prefix="/glossary", tags=["glossary"])

