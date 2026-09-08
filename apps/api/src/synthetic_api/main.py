import os
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from synthetic_api.core.config import settings
from synthetic_api.core.logging import setup_logging
from synthetic_api.infrastructure.db.session import engine, Base
from synthetic_api.routes.v1.router import api_router
from synthetic_api.infrastructure.file_access import confined_file

# Initialize database schema
Base.metadata.create_all(bind=engine)
setup_logging()

@asynccontextmanager
async def lifespan(app):
    from synthetic_api.application.services.batch_service import BatchService
    BatchService.recover_interrupted()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/api/v1/docs", include_in_schema=False)
@app.get("/api/docs", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.get(f"{settings.API_V1_PREFIX}/openapi.json", include_in_schema=False)
async def redirect_to_openapi():
    return RedirectResponse(url="/openapi.json")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

web_dist = settings.ROOT_DIR / "apps" / "web" / "dist"
assets_dir = web_dist / "assets"

if assets_dir.exists() and assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    requested_file = web_dist / full_path
    if full_path and requested_file.exists() and requested_file.is_file():
        return FileResponse(str(confined_file(requested_file, web_dist)))
        
    index_file = web_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
        
    return {
        "status": "healthy",
        "message": "API Server is running. Build frontend with 'npm run build' in apps/web to serve web UI.",
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }

def start():
    uvicorn.run(
        "synthetic_api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["apps/api/src", "packages/synthetic_engine", "."],
    )

if __name__ == "__main__":
    start()
