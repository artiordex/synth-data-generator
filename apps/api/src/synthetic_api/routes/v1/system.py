"""
파일명: system.py
경로: apps/api/src/synthetic_api/routes/v1/system.py
목적: 시스템 문서와 라이브러리 관리 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
import datetime
import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Query
from synthetic_api.core.config import settings

router = APIRouter(prefix="/system", tags=["system"])

EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "dist", ".git", ".idea", ".vscode",
    "storage", "__pycache__", ".system_generated", ".gemini", "brain", ".user_uploaded", ".pytest_cache"
}

LIBRARY_DESCRIPTIONS: Dict[str, str] = {
    # Frontend Dependencies
    "react": "선언적 컴포넌트 기반 웹 사용자 인터페이스 라이브러리",
    "react-dom": "React 가상 DOM의 브라우저 DOM 렌더링 엔진",
    "lucide-react": "고품질 커스텀 벡터 아이콘 셋 (UI 버튼, 인디케이터, 메뉴)",
    "marked": "초고속 GFM(GitHub Flavored Markdown) 및 표준 마크다운 파서·컴파일러",
    "clsx": "조건부 CSS 클래스 네임 문자열 결합 유틸리티",
    "tailwind-merge": "Tailwind CSS 유틸리티 클래스 충돌 방지 및 안전한 병합",
    "@tanstack/react-virtual": "대용량 표 데이터 가상화 스크롤 (화면 버벅임 없는 대규모 행 렌더링)",
    "dompurify": "HTML/마크다운 렌더링 XSS 보안 정제 및 악성 스크립트 실행 방지 (공공기관 보안 필수)",
    "papaparse": "초고속 브라우저 CSV/TSV 파서 및 파일 인코딩(EUC-KR, UTF-8) 자동 감지",
    "recharts": "원본 vs 합성 데이터 분포 비교 및 다변량 통계 상관관계 인터랙티브 차트",
    "jszip": "다중 파일 및 대량 변환 결과물 브라우저 단 ZIP 압축 아카이브 생성",
    "file-saver": "브라우저 클라이언트 사이드 즉시 파일 다운로드 트리거",
    
    # Frontend Dev & Build Tools
    "vite": "차세대 초고속 프론트엔드 빌드 툴 및 HMR(Hot Module Replacement) 개발 서버",
    "typescript": "정적 타입 체킹 및 ECMAScript 최신 문법 컴파일러",
    "tailwindcss": "유틸리티 퍼스트 CSS 프레임워크 (디자인 토큰, 다크모드, 반응형 레이아웃)",
    "postcss": "CSS 변환 및 최적화 파이프라인 엔진",
    "autoprefixer": "브라우저 호환성을 위한 CSS 벤더 프리픽스 자동 추가 도구",
    "@vitejs/plugin-react": "Vite용 공식 React Fast Refresh 빌드 플러그인",
    "@types/react": "React 코어에 대한 TypeScript 타입 정의",
    "@types/react-dom": "React DOM에 대한 TypeScript 타입 정의",
    "@types/dompurify": "DOMPurify TypeScript 타입 정의",
    "@types/papaparse": "PapaParse TypeScript 타입 정의",
    "@types/jszip": "JSZip TypeScript 타입 정의",
    "@types/file-saver": "FileSaver TypeScript 타입 정의",
    "tree-node-cli": "프로젝트 디렉토리 구조 트리 시각화 CLI 도구",
    
    # Python - Data & AI Synthesis
    "sdv": "다변량 통계 및 딥러닝 기반 합성 데이터 생성 프레임워크 (CTGAN, TVAE, GaussianCopula)",
    "synthetic-engine": "식약처 사내 데이터 생성 엔진 코어 (가명처리, 합성엔진, 프라이버시 평가)",
    "torch": "PyTorch CPU 최적화 텐서 연산 및 딥러닝 신경망 백엔드",
    "anonymeter": "프라이버시 재식별 위험도(Singling-out, Linkability, Inference) 정량 평가",
    "faker": "한국형(ko_KR) 주소, 성명, 주민등록번호, 연락처 등 가명 데이터 생성",
    "numpy": "고성능 N차원 수치 배열 및 선형대수 연산",
    "scikit-learn": "머신러닝 데이터 전처리, 차원 축소 및 통계 분포 모델링",
    
    # Python - OCR & Computer Vision
    "rapidocr-onnxruntime": "초고속 PaddleOCR 기반 ONNX 가속 한글/영문 텍스트 및 BBox 인식 엔진",
    "easyocr": "PyTorch 기반 한국어·영어 고정밀 딥러닝 광학 문자 인식(OCR) 엔진",
    "opencv-python-headless": "컴퓨터 비전 이미지 처리 및 모폴로지 연산 기반 표(Table) 윤곽선/셀 그리드 검출",
    "opencv-python": "OpenCV 컴퓨터 비전 코어 엔진",
    "scipy": "과학 계산 및 스캔본 문서 미세 기울기(Skew) 자동 보정(Deskewing) 알고리즘",
    "pillow-heif": "아이폰/모바일 촬영 스캔본(HEIC/HEIF) 고화질 무손실 디코딩",
    "piexif": "스마트폰 스캔 사진 EXIF 방향 메타데이터 분석 및 자동 회전 정규화",
    "python-pptx": "파워포인트(PPTX) 프레젠테이션 슬라이드 파싱, 텍스트·도형·서식 및 이미지 추출/변환",
    "xlsxwriter": "고속 Excel 스프레드시트 포맷팅 및 서식 작성",
    "kiwipiepy": "초고속 C++ 한국어 형태소 분석기 및 개인식별정보(PII) 인명·지명·기관명 정밀 추출",
    "statsmodels": "합성데이터 다변량 통계 가설 검정(KS-test, Chi-square) 및 p-value 정밀 분석",
    "duckdb": "초고속 인메모리 임베디드 OLAP SQL 분석 엔진 (대용량 데이터 고속 프로파일링)",
    "rapidfuzz": "C++ 가속 레벤슈타인 문자열 유사도 분석 및 OCR 문자 오차율(CER) 정밀 측정",
    
    # Python - Document Processing & Conversion
    "python-hwpx": "한국 한글 표준 HWPX(Open 한글) XML 구조 생성, 테이블 조작 및 문서 바인딩",
    "pyhwp": "레거시 HWP 5.0 바이너리 문서 분석, OLE2 복합 포맷 파싱 및 텍스트/테이블 복원",
    "pymupdf": "초고속 PDF 텍스트/레이아웃 추출 및 페이지 렌더링 (fitz)",
    "pdfplumber": "PDF 내 테이블 좌표/셀 경계선 정밀 분석 및 텍스트 박스 추출",
    "python-docx": "MS Word(DOCX) XML 구조 파싱 및 스타일 추출",
    "mammoth": "Word(DOCX) 문서를 클린 HTML/Markdown으로 변환",
    "pypdf": "PDF 페이지 분할, 병합 및 메타데이터 처리",
    "openpyxl": "Excel(XLSX) 스프레드시트 셀 서식, 다중 시트 읽기/쓰기",
    "pyarrow": "Apache Parquet 고성능 대용량 컬럼형 데이터 I/O",
    "pandas": "정형 데이터 테이블 변환, 피벗, 필터링 및 전처리",
    "beautifulsoup4": "비표준 HTML/XML 파싱 및 웹 문서 구조 분석",
    "lxml": "고성능 C기반 XML/HTML 파서 및 XPath 쿼리 엔진",
    "html5lib": "HTML5 표준 준수 비정형 HTML 파싱 및 자동 보정",
    "pillow": "이미지 포맷 변환, 메타데이터 보존 및 리사이징 (PIL)",
    "weasyprint": "HTML/CSS 기반 표준 인쇄용 PDF 렌더링",
    "xhtml2pdf": "HTML+CSS를 PDF로 변환하는 경량 렌더러",
    "tabulate": "터미널 및 마크다운 텍스트 테이블 자동 포맷팅",
    "markdown": "Python 마크다운 파싱 및 HTML 변환",
    "playwright": "헤드리스 브라우저 기반 복합 웹 문서 렌더링",
    "pywin32": "Windows OS 네이티브 Win32/COM API 바인딩",
    "olefile": "구버전 한글(HWP 5.0) 및 OLE 복합 바이너리 문서 스트림 파싱",
    "reportlab": "PDF 문서 동적 생성, 폰트 임베딩 및 벡터 그래픽 렌더링",
    
    # Python - Backend & Infrastructure
    "fastapi": "고성능 비동기 REST API 웹 프레임워크 및 OpenAPI 3.1 Swagger 자동 생성",
    "uvicorn": "고속 비동기 ASGI 웹 서버",
    "pydantic": "런타임 데이터 스키마 유효성 검증 및 직렬화",
    "pydantic-settings": "환경변수 및 설정 파일 자동 매핑 관리",
    "sqlalchemy": "ORM 및 SQLite 내장 데이터베이스 트랜잭션 관리",
    "python-multipart": "대용량 스트리밍 파일 업로드/다운로드 처리",
    "httpx": "비동기 HTTP 클라이언트",
    "pytest": "자동화 단위 테스트 및 통합 테스트 러너",
}

EXCLUDED_MARKDOWN_FILES = {"README.md", "AGENTS.md"}

DOCUMENT_DISPLAY_NAMES: Dict[str, str] = {
    "저장소작업지침.md": "저장소 작업 지침",
    "개발이력.md": "시스템 개발 이력",
    "라이브러리목록.md": "프로젝트 사용 라이브러리 및 오픈소스 목록",
    "프로젝트안내.md": "범용 AI 합성데이터 생성 및 심의 패키지 플랫폼 안내",
    "apps/api/백엔드API안내.md": "백엔드 API 패키지 안내",
    "packages/synthetic_engine/합성엔진안내.md": "합성 엔진 패키지 안내",
    "docs/코드주석작성지침.md": "코드 주석 작성 지침",
    "docs/화면설계지침.md": "화면 설계 지침",
    "docs/architecture/아키텍처.md": "프로젝트 아키텍처",
    "docs/architecture/공통모듈화계획.md": "공통 모듈화 및 도메인 분리 계획",
    "docs/architecture/개선작업목록.md": "기능 개선 작업 목록",
    "docs/일괄처리.md": "최대 20개 파일 일괄 처리",
    "docs/사내망Nginx운영.md": "사내망 Nginx 운영",
    "docs/노트북연동.md": "노트북 기능 반영",
    "docs/심의자료생성및배포.md": "심의자료 자동 생성과 모노레포 운영",
    "docs/세종교육데이터명세.md": "세종 교육데이터 합성 데이터 명세서",
    "docs/문서목록.md": "프로젝트 Markdown 문서 목록",
    "docs/설문_합성데이터_최종산출물/설문_전국3대지역_합성결과_요약보고서.md": "전국 3대 지역 설문 합성 결과 요약보고서",
}

DOCUMENT_PATH_ALIASES = {
    "AGENTS.md": "저장소작업지침.md",
    "CHANGELOG.md": "개발이력.md",
    "LIBRARIES.md": "라이브러리목록.md",
    "README.md": "프로젝트안내.md",
    "apps/api/README.md": "apps/api/백엔드API안내.md",
    "packages/synthetic_engine/README.md": "packages/synthetic_engine/합성엔진안내.md",
}

def sync_and_generate_libraries_markdown() -> str:
    """package.json, package-lock.json, pyproject.toml을 분석하여 라이브러리목록.md를 자동 갱신합니다."""
    root = settings.ROOT_DIR.resolve()
    web_pkg_path = root / "apps" / "web" / "package.json"
    root_pkg_path = root / "package.json"
    api_pyproject_path = root / "apps" / "api" / "pyproject.toml"

    web_deps: Dict[str, str] = {}
    web_dev_deps: Dict[str, str] = {}
    if web_pkg_path.exists():
        try:
            data = json.loads(web_pkg_path.read_text(encoding="utf-8"))
            web_deps = data.get("dependencies", {})
            web_dev_deps = data.get("devDependencies", {})
        except Exception:
            pass

    root_dev_deps: Dict[str, str] = {}
    if root_pkg_path.exists():
        try:
            data = json.loads(root_pkg_path.read_text(encoding="utf-8"))
            root_dev_deps = data.get("devDependencies", {})
        except Exception:
            pass

    engine_pyproject_path = root / "packages" / "synthetic_engine" / "pyproject.toml"

    python_deps: List[str] = []
    python_dep_names = set()
    for ppath in [api_pyproject_path, engine_pyproject_path]:
        if ppath.exists():
            try:
                import tomllib
                data = tomllib.loads(ppath.read_text(encoding="utf-8"))
                for item in data.get("project", {}).get("dependencies", []):
                    clean = item.strip()
                    pkg_name = re.sub(r"\[.*\]", "", re.split(r"[><=~;!]", clean)[0].strip()).lower()
                    if clean and pkg_name not in python_dep_names:
                        python_deps.append(clean)
                        python_dep_names.add(pkg_name)
            except Exception:
                pass

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# 프로젝트 사용 라이브러리 및 오픈소스 목록")
    md.append("")
    md.append(f"> **자동 동기화 일시**: `{now_str}`")
    md.append("> 이 문서는 `package.json`, `package-lock.json`, `pyproject.toml`의 의존성을 기반으로 자동 갱신됩니다. 패키지를 추가하면 다음 동기화 시 설명과 버전이 반영됩니다.")
    md.append("")

    # 1. Web Core UI
    md.append("## 1. 웹 프론트엔드 핵심 UI (`apps/web` - package.json)")
    for name, ver in sorted(web_deps.items()):
        desc = LIBRARY_DESCRIPTIONS.get(name, "NPM 프론트엔드 런타임 의존성")
        md.append(f"- **`{name}`** (`{ver}`) : {desc}")
    md.append("")

    # 2. Frontend Dev & Build
    md.append("## 2. 웹 빌드 툴 & 컴파일러 (`devDependencies`)")
    all_dev = {**web_dev_deps, **root_dev_deps}
    for name, ver in sorted(all_dev.items()):
        desc = LIBRARY_DESCRIPTIONS.get(name, "NPM 개발 및 빌드 의존성")
        md.append(f"- **`{name}`** (`{ver}`) : {desc}")
    md.append("")

    # 3. Python Backend & Data Engine
    md.append("## 3. 백엔드 API & 데이터 합성·변환 엔진 (`apps/api` - pyproject.toml)")
    for dep in sorted(python_deps):
        pkg_base = re.split(r"[><=~;!]", dep)[0].strip()
        pkg_name = re.sub(r"\[.*\]", "", pkg_base).strip()
        desc = LIBRARY_DESCRIPTIONS.get(pkg_name, LIBRARY_DESCRIPTIONS.get(pkg_base, "Python 데이터 처리 및 백엔드 의존성"))
        md.append(f"- **`{dep}`** : {desc}")
    md.append("")

    # 4. Monorepo Architecture
    md.append("## 4. 모노레포 워크스페이스 구조 및 모듈 역할")
    md.append("- **`apps/web`** : React 18 + TypeScript + Vite + Tailwind CSS 기반 고성능 반응형 웹 스튜디오")
    md.append("- **`apps/api`** : FastAPI + SQLite 기반 비동기 백엔드 RESTful API 서버")
    md.append("- **`packages/synthetic_engine`** : 다변량 통계(SDV) 및 프라이버시(Anonymeter) 합성 엔진 코어")
    md.append("- **`packages/contracts`** : 프론트엔드-백엔드 공유 스키마 및 API 계약 인터페이스")
    md.append("")

    final_content = "\n".join(md)

    # 라이브러리목록.md 저장
    try:
        (root / "라이브러리목록.md").write_text(final_content, encoding="utf-8")
    except Exception:
        pass

    return final_content

def scan_all_markdown_docs():
    docs = []
    root = settings.ROOT_DIR.resolve()

    # 라이브러리목록.md 동기화
    sync_and_generate_libraries_markdown()

    for p in root.rglob("*.md"):
        try:
            rel = p.relative_to(root)
            rel_posix = rel.as_posix()
            parts = rel.parts
            if rel_posix in EXCLUDED_MARKDOWN_FILES:
                continue
            if any(part in EXCLUDED_DIRS for part in parts):
                continue
            if any(part.startswith(".") for part in parts):
                continue

            content = p.read_text(encoding="utf-8", errors="ignore")
            title = p.name
            for line in content.splitlines():
                line_str = line.strip()
                if line_str.startswith("# "):
                    title = line_str.replace("# ", "").strip()
                    break

            # Categorization
            if rel_posix.startswith("docs/"):
                category = "📁 docs/ 기술 가이드 및 산출물"
            elif rel_posix in ["개발이력.md", "라이브러리목록.md", "프로젝트안내.md", "저장소작업지침.md"]:
                category = "⭐ 핵심 시스템 문서"
            elif "apps/" in rel_posix or "packages/" in rel_posix:
                category = "📦 패키지 및 모듈"
            else:
                category = "📄 기타 문서"

            stat = p.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            display_name = DOCUMENT_DISPLAY_NAMES.get(
                rel_posix,
                rel_posix if (rel_posix != p.name and p.name.lower() == "readme.md") else p.name,
            )
            docs.append({
                "id": rel_posix,
                "path": rel_posix,
                "name": display_name,
                "title": title,
                "category": category,
                "is_docs_dir": rel_posix.startswith("docs/"),
                "size_bytes": stat.st_size,
                "updated_at": mtime
            })
        except Exception:
            continue

    def sort_key(d):
        priority = {
            "개발이력.md": 1,
            "라이브러리목록.md": 2,
            "프로젝트안내.md": 3,
            "저장소작업지침.md": 4
        }
        # Put core docs first, then docs/ folder, then packages, then other
        cat_priority = {
            "⭐ 핵심 시스템 문서": 1,
            "📁 docs/ 기술 가이드 및 산출물": 2,
            "📦 패키지 및 모듈": 3,
            "📄 기타 문서": 4
        }
        return (priority.get(d["id"], 99), cat_priority.get(d["category"], 99), d["path"])

    docs.sort(key=sort_key)
    return docs

@router.get("/docs", summary="저장소 내 전체 마크다운(.md) 문서 목록 조회", description="프로젝트 저장소 내에 작성된 모든 기술 문서, 매뉴얼, 개발이력 마크다운(.md) 파일 목록을 스캔하여 반환합니다.")
async def list_docs():
    """모든 프로젝트 마크다운 문서 목록을 조회합니다."""
    return {"docs": scan_all_markdown_docs()}

@router.get("/doc", summary="단일 마크다운 문서 내용 조회", description="지정한 상대 경로의 마크다운(.md) 문서 원본 텍스트 및 메타데이터를 조회합니다.")
async def get_doc(path: str = Query(..., description="조회할 마크다운 파일 상대 경로")):
    """지정한 마크다운 문서의 내용과 메타데이터를 안전하게 조회합니다."""
    root = settings.ROOT_DIR.resolve()

    path = DOCUMENT_PATH_ALIASES.get(path, path)
    if path == "라이브러리목록.md":
        sync_and_generate_libraries_markdown()

    target = (root / path).resolve()

    # Directory traversal prevention
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 파일 경로입니다.")

    if not target.is_file() or target.suffix.lower() != ".md":
        raise HTTPException(status_code=404, detail="마크다운 문서를 찾을 수 없습니다.")

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
        stat = target.stat()
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        
        # Extract title
        title = target.name
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("# "):
                title = line_str.replace("# ", "").strip()
                break

        rel_posix = target.relative_to(root).as_posix()
        return {
            "id": rel_posix,
            "path": rel_posix,
            "name": DOCUMENT_DISPLAY_NAMES.get(rel_posix, target.name),
            "title": title,
            "content": content,
            "size_bytes": stat.st_size,
            "updated_at": mtime
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 읽기 오류: {str(e)}")

@router.get("/changelog", summary="시스템 개발이력 조회", description="개발이력.md 파일의 버전별 업데이트 및 변경 기록을 조회합니다.")
async def get_changelog():
    p = settings.ROOT_DIR / "개발이력.md"
    if p.exists():
        content = p.read_text(encoding="utf-8", errors="ignore")
    else:
        content = "# 시스템 개발 이력\n\n- 개발이력.md 파일이 존재하지 않습니다."
    return {"content": content}

@router.get("/libraries", summary="사내 데이터 생성기 전체 의존성 라이브러리 명세 조회", description="Python 백엔드와 TypeScript 프론트엔드에 설치된 모든 오픈소스 라이브러리의 버전, 라이선스, 역할 설명을 조회합니다.")
async def get_libraries():
    content = sync_and_generate_libraries_markdown()
    return {"content": content}

@router.post("/sync-libraries", summary="라이브러리목록.md 동기화 갱신", description="pyproject.toml 및 package-lock.json 파일을 파싱하여 라이브러리목록.md를 최신 상태로 재동기화합니다.")
async def sync_libraries():
    content = sync_and_generate_libraries_markdown()
    return {"status": "success", "content": content}
