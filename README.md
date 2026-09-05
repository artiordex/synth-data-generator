# 🛡️ 범용 AI 합성데이터 생성 & 심의 패키지 플랫폼

현재 한글(HWPX) 자동 생성, uv 모노레포 실행, Render 배포 및 폴더 정리 기준은
[운영 가이드](docs/review-documents-and-deployment.md)를 참고하세요.

> **데이터 합성·평가와 심의위원회 한글(HWPX) 문서 자동 생성을 지원하는 플랫폼. uv/npm 모노레포이며 Render Docker 배포를 사용합니다.**

---

## 🌟 핵심 기능 (Key Features)

1. **차분 프라이버시 (Laplace Differential Privacy)**
   - 프라이버시 예산(\(\epsilon\)) 기반의 엄격한 수학적 라플라스 노이즈 주입으로 개인정보 유출을 원천 방어합니다.
2. **Anonymeter 3대 재식별 위험 평가 (EU GDPR 29조 표준)**
   - **단일식별 위험(Singling-Out)**, **연결성 위험(Linkability)**, **속성추론 위험(Inference)**을 시뮬레이션하여 0.00~1.00 수치로 정밀 산출합니다.
3. **통계적 분포 유사도 (JSD & Wasserstein)**
   - Jensen-Shannon 발산(JSD)을 통해 전 컬럼의 원본 대비 결합 확률 분포 보존율을 다각도로 정량화합니다.
4. **심의위원회 한글 문서(HWPX) 자동 생성**
   - 원본 HWP를 한글에서 변환한 HWPX 템플릿을 복제해 **원본데이터 명세서**, **합성데이터 명세서**, **안전성 및 유용성 측정결과서**의 셀에 값을 입력합니다. 글꼴·테두리·수식을 유지하고, 데이터 컬럼에 따라 표와 병합 행을 늘립니다. `storage/templates/*.hwpx`가 필요합니다.
5. **한국형 PII 10종 자동 감지 및 Faker 가명화**
   - 이름, 주민등록번호, 휴대전화, 이메일, 주소, 계좌번호 등을 정규식 및 패턴으로 자동 탐지하여 일관된 가명 레코드로 대체합니다.
6. **하이브리드 AI 합성 엔진 지원**
   - **터보 통계 샘플러 (Statistical Sampler, 1~3초 초고속)**, **가우시안 코퓰라 (Gaussian Copula)**, **CTGAN (조건부 생성 신경망)**, **TVAE (변분 오토인코더)**를 목적에 따라 선택할 수 있습니다.
7. **데이터 지식 사전 (Data Dictionary)**
   - 프론트엔드 내에 차분 프라이버시, Anonymeter 지표, 머신러닝 아키텍처, 행정 규제 해설을 담은 대화형 용어 사전을 내장하였습니다.
8. **SHA-256 데이터 무결성 추적 & 감사 로그**
   - 원본 및 합성 파일의 고유 암호화 해시 및 실행 디바이스 정보를 자동 기록하여 데이터 위변조를 방지합니다.
9. **프로젝트 일관 가명 토큰 & k/l/t 평가**
   - 여러 파일의 동일 값을 프로젝트·컬럼 단위 HMAC 토큰으로 일관되게 치환하고, 사용자가 지정한 준식별자와 민감정보로 k-익명성·l-다양성·t-근접성을 계산합니다.
10. **관계형 및 시계열 합성**
   - 여러 테이블의 PK/FK를 자동 탐지해 참조 무결성을 유지하며 생성하고, 개체별 관측 순서와 시간 간격을 유지하는 시계열·패널 합성을 지원합니다.
11. **스키마 기반 더미데이터**
   - DDL, JSON Schema, OpenAPI JSON을 가져와 컬럼과 제약조건을 구성하고 정상·경계·오류·혼합 테스트 시나리오를 생성합니다.
12. **모델 자동 비교**
   - 네 가지 단일 테이블 모델을 축소 학습해 분포·상관관계·실행시간을 비교하고 적합한 모델을 자동 선택합니다.

---

## 📂 프로젝트 아키텍처

```text
work/
├─ apps/
│  ├─ web/                         # React 18 + Vite + TypeScript 프론트엔드
│  │  ├─ src/                      # Feature 슬라이스 (dictionary, dataset, profiling, synthesis, validation, export)
│  │  └─ dist/                     # 정적 웹 번들
│  └─ api/                         # FastAPI 프로젝트 (pyproject.toml, tests)
│     └─ src/synthetic_api/         # main.py, routes, application, domain, infrastructure, core
├─ packages/
│  ├─ synthetic_engine/            # AI 합성 / DP 노이즈 / Anonymeter / HWP 빌더 코어 패키지
│  └─ contracts/                   # 공통 인터페이스 스키마 및 DTO
├─ storage/                        # 데이터 격리 저장소 (uploads, outputs, temp, local/app.db)
├─ docs/
│  └─ reference/                   # 구현 근거로 보존하는 원본 노트북
├─ tests/                          # E2E 파이프라인 통합 테스트 (test_full_pipeline.py)
├─ scripts/dev/                    # run_dev.bat, run_tests.bat
├─ infra/nginx/                    # 사내망 Nginx 리버스 프록시 설정
└─ run_server.bat / server.py      # 원클릭 단일 실행 호환 진입점
```

---

## 🚀 빠른 시작 (Quick Start)

### 방법 1. 원클릭 통합 실행 (가장 간편한 방법)
윈도우 환경에서 `run_server.bat` 파일을 더블 클릭하거나 콘솔에서 실행합니다:

```cmd
run_server.bat
```

* **웹 대시보드**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **대화형 API 문서 (Swagger)**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

### 방법 2. 프론트엔드 HMR 핫 리로딩 개발 모드
```cmd
scripts\dev\run_dev.bat
```
* **프론트엔드 Vite Dev 서버**: [http://localhost:5173](http://localhost:5173)
* **백엔드 API 서버**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 방법 3. 사내망 Docker + Nginx 운영

```powershell
docker compose up -d --build
```

사내 PC에서는 `http://서버의-사내-IP`로 접속한다. Nginx가 80번 포트에서 웹과
API를 통합 서버로 전달하며, 애플리케이션의 8000번 포트는 서버 로컬에서만 접근할
수 있다. Windows 방화벽 설정과 운영 명령은
[사내망 Nginx 운영 가이드](docs/intranet-nginx.md)를 참고한다.

---

## 🧪 테스트 실행

```bash
# 전체 워크스페이스 단위 및 E2E 테스트
uv run --locked --all-packages python -m pytest -v
```

---

## 📄 라이선스
MIT License
