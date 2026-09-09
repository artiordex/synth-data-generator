# =============================================================================
# 파일명: main.py
# 경로: apps/api/src/synthetic_api/main.py
# 목적: FastAPI 애플리케이션과 서버 수명주기를 구성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
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
    """서버 시작과 종료 시 공통 작업을 처리함"""
    from synthetic_api.application.services.batch_service import BatchService
    BatchService.recover_interrupted()
    yield


TAGS_METADATA = [
    {
        "name": "document-privacy",
        "description": "문서(PDF, HWP, HWPX) 원본 서식 유지 개인정보 검사, 텍스트 치환 및 가명처리 API",
    },
    {
        "name": "datasets",
        "description": "정형 데이터셋(CSV, Excel, Parquet 등) 업로드, 프로파일링 및 k-익명성 기반 가명화 API",
    },
    {
        "name": "synthesis",
        "description": "단일 테이블 AI 모델(CTGAN, TVAE, Copula, Statistical) 축소 비교 및 합성 파이프라인 실행 API",
    },
    {
        "name": "jobs",
        "description": "데이터 합성 작업(Job) 상태 추적, 원본/합성 컬럼 분포 비교 및 심의 리포트 조회 API",
    },
    {
        "name": "batches",
        "description": "다중 데이터셋 일괄(배치) 합성 작업 시작, 상태 조회 및 취소 API",
    },
    {
        "name": "files",
        "description": "합성 데이터셋, 가명화 파일, 심의 리포트 등 산출물 안전 다운로드 API",
    },
    {
        "name": "review",
        "description": "개인정보 보호 및 데이터 가명처리 단계별 감사 로그(Audit Log) 조회 API",
    },
    {
        "name": "dummy",
        "description": "표준 데이터 도메인 카탈로그 및 DDL/JSON 스키마 기반 규칙형 더미 데이터 생성 API",
    },
    {
        "name": "relational-synthesis",
        "description": "멀티테이블 관계형 데이터(PK-FK 참조 무결성 보장) HMA 및 터보 샘플러 합성 API",
    },
    {
        "name": "time-series-synthesis",
        "description": "개체 식별자 및 시간 축 패턴을 보존하는 패널/시계열 데이터 합성 API",
    },
    {
        "name": "history",
        "description": "합성, 가명화, 더미 생성, 파일 변환 등 시스템 통합 작업 이력 조회 및 선택 삭제 API",
    },
    {
        "name": "converter",
        "description": "HWP, HWPX, PDF, Word, Excel, CSV 등 범용 문서 및 정형 데이터 고품질 상호 변환 API",
    },
    {
        "name": "survey-synthesis",
        "description": "다중 모듈 설문조사 데이터 결합, 리커트 척도 순서성 보존 및 설문 합성데이터 패키지 생성 API",
    },
    {
        "name": "system",
        "description": "시스템 변경이력(Changelog), 마크다운 문서 및 오픈소스 라이브러리 명세 관리 API",
    },
    {
        "name": "glossary",
        "description": "인공지능, 딥러닝, 프라이버시 보호 및 합성데이터 도메인 전문 용어사전 API",
    },
]

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description="식약처 사내 데이터 생성기 v2.1.0 공식 RESTful API 명세서",
    version=settings.VERSION,
    openapi_tags=TAGS_METADATA,
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

@app.get("/health", include_in_schema=False)
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

@app.get("/{full_path:path}", include_in_schema=False)
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
