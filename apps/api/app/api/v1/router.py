from fastapi import APIRouter
from .datasets import router as datasets_router
from .synthesis import router as synthesis_router
from .jobs import router as jobs_router
from .files import router as files_router
from .review import router as review_router

api_router = APIRouter()
api_router.include_router(datasets_router)
api_router.include_router(synthesis_router)
api_router.include_router(jobs_router)
api_router.include_router(files_router)
api_router.include_router(review_router)
