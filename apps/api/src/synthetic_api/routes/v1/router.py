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

api_router = APIRouter()
api_router.include_router(datasets_router)
api_router.include_router(synthesis_router)
api_router.include_router(jobs_router)
api_router.include_router(files_router)
api_router.include_router(review_router)
api_router.include_router(dummy_router)
api_router.include_router(batches_router)
api_router.include_router(relational_router)
api_router.include_router(time_series_router)
api_router.include_router(glossary_router, prefix="/glossary", tags=["glossary"])
