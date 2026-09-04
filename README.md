# 데이터 세이프랩

FastAPI, SDV/CTGAN 딥러닝 엔진, 그리고 가벼운 SQLite 작업 관리자가 통합된 인하우스 합성데이터 생성 웹 서비스입니다.

---

## 🌟 주요 기능

1. **대화형 웹 대시보드 (Web UI)**
   - 브라우저에서 CSV / Excel 파일 최대 20개 드래그 & 드롭 업로드
   - PII(개인정보) 자동 탐지 및 Faker 기반 가명화 처리
   - CTGAN / TVAE / Gaussian Copula / 통계 샘플링 모델 선택 및 파라미터 조절
   - 파일별 컬럼 선택 및 자동 컬럼 추론 또는 노트북 방식(CAT_COLS / NUM_COLS) 직접 지정 선택
   - PAC, 결측 의미 보존 옵션 지원
   - 실시간 진행률 프로그레스 바 (0% → 100%)
   - 단독식별률(Single-Out Rate) 및 통계 유사도(JSD) 평가 리포트 차트
   - 합성데이터 상위 10행 미리보기 및 CSV / Excel / ZIP 묶음 즉시 다운로드
   - 부서명 기준 제출 패키지 자동 생성

2. **경량 SQLite 기반 작업 이력 관리**
   - 별도의 DB 서버 설치 없이 `app.db` 파일 하나로 작업 이력(작업 ID, 생성일, 모델, 평가 점수) 보관
   - 이전 작업 결과 언제든 재다운로드 및 삭제 가능

3. **사용 라이브러리**
   - 합성 모델: `sdv`의 CTGAN / TVAE / Gaussian Copula
   - 빠른 대체 생성: 내장 통계 샘플링
   - PII 가명화: `Faker`
   - 데이터 입출력: `pandas`, `openpyxl`
   - 웹/API: `FastAPI`, `Uvicorn`
   - 작업 이력: 내장 `SQLite`

---

## 🚀 빠른 시작 (웹 서비스 실행)

### 1) 의존성 설치

권장 방식은 `uv`입니다. 이 프로젝트는 Python 실행 환경 폴더를 `.uv`로 사용하도록 TypeScript 실행 래퍼에서 설정합니다.

```bash
npm run uv:sync
```

기존 `pip` 방식도 사용할 수 있습니다.

```bash
pip install -r python_engine/requirements.txt
```

### 2) 웹 서비스 시작

* **방법 1 (윈도우 배치 파일 더블 클릭)**:
  `run_server.bat` 실행

* **방법 2 (Python 명령어)**:
  ```bash
  # Windows PowerShell
  $env:UV_PROJECT_ENVIRONMENT=".uv"; uv run server.py
  ```

* **방법 3 (NPM 스크립트)**:
  ```bash
  npm run web
  ```

### 3) 브라우저 접속
* **웹 대시보드**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **REST API 대화형 문서(Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📂 프로젝트 구조

```text
c:\식약처\work\
├── server.py                       # FastAPI 웹 서버 + SQLite 관리 + 백그라운드 파이프라인
├── run_server.bat                  # 윈도우 1클릭 실행 배치 파일
├── app.db                          # SQLite 데이터베이스 (작업 이력 자동 저장)
├── uploads/                        # 업로드된 원본 파일 보관함
├── outputs/                        # 부서명 기준 제출 패키지 보관함
├── python_engine/
│   ├── run.py                      # 실제 SDV/CTGAN/통계 합성 및 평가 엔진
│   ├── requirements.txt            # 파이썬 의존성 패키지 목록
│   └── config.example.json         # CLI 실행용 설정 예시
└── src/
    ├── run-python.ts               # CLI 합성 실행 래퍼
    ├── run-web.ts                  # 웹 서비스 실행 래퍼
    └── uv-sync.ts                  # .uv 환경 동기화
```

---

## 📦 산출물 구조

작업이 완료되면 다음 구조로 제출 패키지가 생성됩니다.

```text
outputs/
└── 부서명/
    └── 작업ID_원본파일명/
        ├── 원본데이터/
        │   ├── 원본 업로드 파일
        │   └── 원본데이터 명세서(...).hwp
        ├── 합성데이터/
        │   ├── 작업ID_synthetic.csv
        │   ├── 작업ID_synthetic.xlsx
        │   └── 합성데이터 명세서(...).hwp
        └── 심의위원회 심의자료/
            ├── 작업ID_synthetic_evaluation_report.json
            └── 합성데이터 안전성 및 유용성 측정결과서(...).hwp
```

---

## ✅ 자동 평가 기준

합성 완료 시 평가 리포트 JSON에 `assessment` 항목이 자동 생성됩니다.

| 구분 | 기준 | 통과 | 검토 필요 | 실패 |
|---|---|---:|---:|---:|
| 개인정보 | 재식별 위험률(Single-Out) | 0.05 이하 | 0.15 이하 | 0.15 초과 |
| 개인정보 | 미처리 PII 후보 | 0개 | 기탐지/가명화 컬럼만 존재 | 신규 미처리 후보 존재 |
| 품질 | 통계 분포 유사도(JSD 평균) | 0.05 이하 | 0.10 이하 | 0.10 초과 |
| 품질 | 결측률 변화 평균 | 0.05 이하 | 0.15 이하 | 0.15 초과 |
| 품질 | 범주값 유효성 위반률 | 0.01 이하 | 0.05 이하 | 0.05 초과 |
| 품질 | 수치 범위 위반률 | 0.01 이하 | 0.05 이하 | 0.05 초과 |

종합 판정은 `통과 / 검토 필요 / 실패`와 100점 기준 점수로 표시됩니다. 이 기준은 내부 자동 점검용이며, 법적 익명성 보증이나 최종 심의 승인을 대체하지 않습니다.

---

## 🧩 노트북 코드 반영 방식

`합성데이터_수행_코드.ipynb`의 공통 로직은 범용 엔진으로 통합했습니다.

| 노트북 요소 | 서비스 반영 |
|---|---|
| `CTGANSynthesizer` 학습/샘플링 | CTGAN 옵션으로 제공 |
| `CAT_COLS`, `NUM_COLS` 직접 지정 | 합성 옵션의 `노트북 방식 직접 지정`으로 제공 |
| `EPOCHS`, `BATCH_SIZE`, `PAC` | 화면 파라미터로 제공 |
| `single_out_rate_binned` | 개인정보 안전성 평가로 통합 |
| 범주형/수치형 JSD | 품질 평가로 통합 |
| `소득분위_적용` 같은 결측 의미 플래그 | `결측 의미 보존` 옵션으로 범용화 |

데이터셋 경로와 파일명처럼 노트북 안에 고정되어 있던 값은 웹 업로드와 부서별 제출 패키지 구조로 대체했습니다.

---

## 🔬 CLI 기반 배치 실행

설정 파일을 직접 지정하여 CLI로 동작시킬 수도 있습니다.

```bash
npm run engine -- python_engine/config.example.json
```
