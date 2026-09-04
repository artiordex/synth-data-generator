# 심의자료 자동 생성과 모노레포 운영

## 한글 문서

원본 HWP 3종을 설치된 한글에서 HWPX로 변환하고, 작업마다 그 템플릿을
복제해 지정된 셀에 값을 입력한다. 빈 문서에서 양식을 다시 만들지 않는다.
원본의 글꼴·문단 스타일·테두리·수식·그림·용지 설정을 유지한다. 데이터가
늘어나는 표만 원본 행과 셀을 복제하며, 예시·개인정보 처리계획·결과평가 제목은 표와 함께
새 페이지에서 시작한다. 따라서 내용량에 따른 쪽 수와 행 높이는 달라질 수 있다.
한글에서 편집할 수 있는 HWPX 3종, HTML 확인본 3종, 입력내용 JSON이
작업별 `심의위원회 심의자료` 폴더와 전체 ZIP에 포함된다.

| 항목 | 입력 근거 |
| --- | --- |
| 데이터명 | 화면 입력 또는 원본 파일명 |
| 유형·규모 | 실제 원본/합성 행·열 수와 확장자 |
| 특이사항 | 화면 입력 또는 결측·중복·식별자 후보 탐지 현황 |
| 정보 개요 | 화면 입력과 실제 데이터 구조 |
| 정보 상세 | 전체 컬럼의 자료형, 결측 수, 고유값 수; 의미 정의는 담당자 확인 |
| 정보 분류 | 탐지 후보 또는 API의 항목별 입력; 미분류를 일반정보로 단정하지 않음 |
| 원본 예시 | 실제 처음 5행의 구조·결측 여부; 원본값 비공개 |
| 합성 예시 | 실제 출력 처음 5행; 식별자 후보 값 비공개 |
| 개인정보 처리계획 | 화면 입력 및 실제 컬럼별 삭제/마스킹/해시/가상 생성/출력 제외 |
| 측정결과 | 같은 파이프라인 실행의 지표; 실패·생략·NaN은 미측정 |

정보 상세 표는 전체 컬럼 수에 따라 늘어난다. 정보 개요는 분류 종류별로 집계하고,
개인정보 처리계획은 원본의 다단 헤더와 데이터셋명 세로 병합을 유지하며
병합 행 수를 조정한다. 한글에서 긴 세로 병합 셀이 잘리지 않도록 개인정보 표는
8개 항목 단위로 원본 머리글을 반복하고 새 페이지로 나눈다. 정보 상세 표는
여러 쪽으로 이어진다. 예시는 원본 표의 8개 열 단위로 표를 복제하고,
현재 항목 수에 맞춰 열 폭을 균등하게 조정한다. 측정결과는 전체 및 열별 지표 행을 추가한다.
자동으로 알 수 없는 수집 근거, 보유기간, 접근권한, 제공범위, 파기절차는
담당자 입력을 사용하며 미입력 시 확인 필요를 표시한다.
원본 예시를 포함한 모든 산출물은 심의 전 담당자 검토 대상이다.

화면의 **심의자료 한글 문서 입력**에서 데이터명, 특이사항, 정보 개요,
개인정보 처리계획을 작성한 뒤 합성을 실행하고 ZIP을 받는다.
항목별 의미와 분류는 `/api/v1/synthesis/start`의 추가 입력도 지원한다:

```json
{
  "review_metadata": {
    "dataset_name": "설문 응답",
    "overview": "수집 출처 및 기간",
    "special_notes": "특이사항",
    "privacy_plan": "보유·접근·제공·파기 계획",
    "columns": {
      "응답점수": {"description": "만족도 1~5점", "information_type": "일반정보"}
    }
  }
}
```

가상 데이터로 양식 예시 생성:

```powershell
uv run --locked --all-packages python scripts/create_review_example.py
```

결과: `storage/outputs/review-example/`. HTML은 내용 확인본이며 한글 앱의
실제 페이지 렌더링과 동일하지 않다.

`storage/templates/원본데이터 명세서.hwpx`, `합성데이터 명세서.hwpx`,
`측정결과서.hwpx`는 실행에 필요한 기준 템플릿이므로 삭제하면 안 된다.
누락 또는 예상과 다른 표 구조는 명시적인 오류로 처리한다.
원본 HWP를 수정한 경우 한글이 설치된 Windows에서
`./scripts/convert_review_templates.ps1`을 실행하고, 파일 접근 창을 승인한다.
변환한 HWPX 3종을 소스와 함께 배포한다. Render에서는 한글/COM을 사용하지 않는다.
`scripts/render_review_check.ps1`은 Windows 한글을 이용한 개발용 PDF 검증 도구다.

## uv / npm 모노레포

`uv`는 패키지 관리자이며 기본 가상환경 경로는 `.venv`다. `.uv`는 이 저장소의
기존 스크립트에서 임의로 지정했던 환경 이름이며 필수 구조가 아니다.
Python은 루트 `pyproject.toml` + `uv.lock`, 프런트엔드는 npm workspaces와
루트 `package-lock.json`을 기준으로 관리한다.

```powershell
uv sync --locked --all-packages
npm ci
npm run build
uv run --locked --all-packages server.py
uv run --locked --all-packages python -m pytest
```

uv가 PATH에 설치되어 있어야 한다. `run_server.bat`은 uv를 먼저 찾으며,
현재 환경에만 설치된 `.venv/Scripts/uv.exe`도 보조 경로로 지원한다.

```text
apps/api/src/synthetic_api/ FastAPI Python 패키지
  routes/                   HTTP 라우터와 의존성
  application/              서비스 실행 흐름
  domain/                   업무 모델과 인터페이스
  infrastructure/           DB·저장소 구현
  core/                     설정·로그·공통 기능
  main.py                   앱 조립 및 실행
apps/api/tests/             API 테스트
apps/api/pyproject.toml      API 패키지 정의
apps/web/                   React 웹 앱
packages/synthetic_engine/  데이터 합성·평가·문서 생성
packages/contracts/         공통 TypeScript 타입
storage/templates/          필수 HWPX 템플릿 및 원본 HWP
storage/uploads,outputs/    실행 중 생성되는 데이터
storage/local/              로컬 SQLite 데이터베이스
scripts/                    로컬 실행·예시 생성 도구
tests/                      통합 테스트
Dockerfile + render.yaml    Render 배포 진입점
```

## 정리 후보 — 삭제하지 않음

- `storage/templates`의 HWP 6개는 SHA-256 기준 3쌍의 중복 파일이다.
  짧은 표준 파일명 3개를 기준으로 모을 수 있다. 루트에도 사본을 둘 필요는 없다.
- `.venv`, `.uv`, `node_modules`, `__pycache__`, `.pytest_cache`, `apps/web/dist`:
  생성물/캐시다. 소스 관리·배포 이미지에 포함하지 않는다. 환경은 한 곳만 사용한다.
- `infra/docker`, `infra/nginx`, `docker-compose.yml`: 로컬 API/웹 분리 실행용이다.
  Render의 통합 Docker 배포에는 사용하지 않는다. 분리 실행을 폐기할 때 정리 가능하다.
- `experiments/samples`, `experiments/notebooks`: 실험용으로 유지 가능하며 배포에서 제외한다.
- `apps/web/src/types/index.ts`와 `packages/contracts/src/index.ts`: 중복 타입 정의다.
  추후 앱이 contracts 패키지를 직접 가져오도록 통합할 수 있다.
- `exporters/hwp_exporter.py`: 이전 고정 문자열 치환 방식의 호환 코드다.
  새 파이프라인은 `review_documents.py`를 사용한다.

## Render

루트 `render.yaml`이 루트 `Dockerfile`을 사용한다. Docker 빌드에서 `npm ci`로
웹을 빌드하고 `uv sync --locked --all-packages --no-dev`로 API/엔진을 설치한다.
FastAPI가 웹 정적 파일과 API를 같은 서비스에서 제공하며 `$PORT`로 수신한다.
실행 대상은 `synthetic_api.main:app`이다. `ROOT_DIR=/app`으로 작업 경로를 명시한다.
개발자 업로드·산출물·SQLite·실험 데이터를 이미지에 복사하지 않는다.

현재 Blueprint의 `plan: free`는 유지했다. Render의 기본 파일시스템은 임시이며
재시작/재배포 후 업로드·산출물·SQLite가 사라질 수 있다. 운영 보관이 필요하면
유료 디스크 또는 외부 저장소/DB 구성을 별도로 적용해야 한다.
배포 설정 수정은 서비스에 실제 배포했다는 의미가 아니다.

참고: [uv Docker](https://docs.astral.sh/uv/guides/integration/docker/),
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/),
[Render 디스크](https://render.com/docs/disks),
[HWPX 라이브러리](https://github.com/airmang/python-hwpx).
