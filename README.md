# 🛡️ 범용 AI 합성데이터 생성 & 공공 AI-Ready 표준화 플랫폼

공공데이터 및 행정문서의 **AI 친화도(AI-Ready) 표준 진단 및 다종 공문서(HWPX·DOCX·ODT·MD) 자동 가이드 생성**, **공공문서(HWPX·DOCX·PDF) 정형 데이터 변환**, **차분 프라이버시(DP) 기반 AI 합성데이터 생성 및 심의위원회 HWPX 보고서 패키징**을 통합 제공하는 모노레포 플랫폼입니다.

---

## 🌟 핵심 기능

### 1. 공공데이터 AI 친화도(AI-Ready) 가이드 스튜디오 (NEW)
- **파일데이터(CSV·XLSX·TSV) 및 API(JSON·XML) 표준 평가**: 행정안전부 공공데이터 관리지침 및 W3C 표준 기준 적합도 진단
- **DCAT 3.0 / Dublin Core / DQV / RAI 표준 메타데이터 자동 추론**: 16대 정부 표준 분류, 공간범위, 갱신주기, 키워드, AI 윤리 검토 항목 자동 완성
- **전체 산출물 7종 일괄 ZIP 번들 및 체계적 명명 규칙 제공**:
  - 사람이 읽는 가이드 문서 3종: `{파일명}_가이드.hwpx`, `{파일명}_가이드.docx`, `{파일명}_가이드.md`
  - 기계 가독 메타데이터 3종: `{파일명}_메타데이터.json`, `{파일명}_메타데이터.xml`, `{파일명}_메타데이터.jsonld`
  - 데이터 품질 진단 보고서: `{파일명}_품질보고서.md`

```text
📦 {파일명}_전체산출물.zip
├── {파일명}_가이드.hwpx        # 한글 표준 공문서
├── {파일명}_가이드.docx        # MS Word 공문서
├── {파일명}_가이드.md          # 마크다운 가이드 전문
├── {파일명}_메타데이터.json    # 표준 정형 JSON 스키마
├── {파일명}_메타데이터.xml     # 정부 XSD 스키마 검증 XML
├── {파일명}_메타데이터.jsonld  # W3C DCAT 3.0 / schema.org 연계 메타데이터
└── {파일명}_품질보고서.md      # 결측치·이상치 데이터 준비도 진단 보고서
```

### 2. 공공문서 데이터 변환기 (Gov Document Converter) (NEW)
- **HWPX / DOCX / PDF 정형화**: 행정문서 본문 내 데이터 표, 파라미터 정의서, 개요 표를 자동 식별·추출하여 AI 학습 및 데이터 분석용 CSV/JSON으로 변환
- **PDF 95%+ 고정밀 서식 보존 변환 (v2.1.0)**: PyMuPDF + pdfplumber 하이브리드 분석으로 원본 서식을 시각적으로 완벽 재현한 Excel(서식 시트 / 정형 표 시트 / 상담 카드 시트 3종 자동 생성) 및 HWPX/HTML 변환

### 3. 데이터셋 비교 및 정합성 검증 스튜디오 (NEW)
- 원본 데이터셋과 변환/합성 데이터셋 간 스키마, 컬럼 통계, 결측치, 데이터 타입 및 값 일치율 자동 비교 분석

### 4. 하이브리드 AI 합성데이터 생성 & 차분 프라이버시
- **라플라스 차분 프라이버시(DP)**: 수학적 프라이버시 예산(\(\epsilon\)) 기반 노이즈 주입으로 원천적 재식별 차단
- **4대 합성 모델 지원**: 터보 통계 샘플러(1~3초), Gaussian Copula, CTGAN(생성 신경망), TVAE(변분 오토인코더)
- **Anonymeter 3대 재식별 위험 평가**: 단일식별(Singling-Out), 연결성(Linkability), 속성추론(Inference) 위험도 정밀 산출

### 5. 18종 한국형 개인정보(PII) 자동 감지 및 스마트 가명화
- 주민등록번호, 전화번호, 계좌번호, 이메일 등 18종 PII 탐지 및 성별·형식 보존형 마스킹
- 복합 텍스트 내 인라인(Inline) 개인정보 자동 비식별화 및 사전-사후 변경점 하이라이트

### 6. 공공 심의위원회 한글(HWPX) 문서 자동 생성
- 원본데이터 명세서, 합성데이터 명세서, 안전성·유용성 결과서 3종 HWPX 서식 자동 바인딩

---

## 📂 프로젝트 구조

```text
work/
├─ apps/
│  ├─ web/                         # React 18 + Vite + TypeScript 프론트엔드
│  │  └─ src/features/
│  │     ├─ aiguide/               # AI 친화도 가이드 스튜디오 (HWPX/DOCX/MD/ZIP)
│  │     ├─ converter/             # 공공문서 변환 & 데이터셋 비교 스튜디오
│  │     ├─ synthesis/             # AI 합성데이터 생성 엔진
│  │     └─ pseudopii/             # 한국형 PII 비식별화 스튜디오
│  └─ api/                         # FastAPI 백엔드 (Python 3.12, pyproject.toml)
│     └─ src/synthetic_api/
│        ├─ application/services/  # AI 가이드, 문서 변환, 합성 파이프라인
│        └─ routes/v1/             # RESTful API 엔드포인트
├─ packages/
│  ├─ synthetic_engine/            # DP / Anonymeter / AI 모델 코어 패키지
│  └─ contracts/                   # 공통 스키마 및 DTO
├─ docs/                           # 상세 가이드 및 아키텍처 문서
└─ run_server.bat                  # 원클릭 통합 실행 배치 파일
```

---

## 🚀 빠른 시작

### 1. 원클릭 통합 실행 (권장)
윈도우 환경에서 `run_server.bat` 파일을 실행합니다:
```cmd
run_server.bat
```
- **웹 대시보드**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Swagger API 문서**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

### 2. 프론트엔드 HMR 핫 리로딩 개발 모드
```cmd
scripts\dev\run_dev.bat
```
- **프론트엔드 Vite Dev 서버**: [http://localhost:5173](http://localhost:5173)
- **백엔드 API 서버**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📖 관련 주요 지침 문서
- [프로젝트 상세 안내](docs/프로젝트안내.md)
- [프로젝트 Markdown 문서 목록 (전체 색인)](docs/문서목록.md)
- [저장소 작업 지침](docs/저장소작업지침.md)
- [깃 커밋 및 사전 검증 규격](docs/깃 커밋 조건.md)
- [코드 주석 작성 지침](docs/코드주석작성지침.md)
- [시스템 개발 이력](docs/개발이력.md)
