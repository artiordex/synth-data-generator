# 심의자료 자동 생성과 모노레포 운영

## 한글 문서

원본 HWP 3종을 설치된 한글에서 HWPX로 변환하고, 작업마다 그 템플릿을
복제해 지정된 셀에 값을 입력한다. 빈 문서에서 양식을 다시 만들지 않는다.
원본의 글꼴·문단 스타일·테두리·수식·그림·용지 설정을 유지한다. 데이터가
늘어나는 표만 원본 행과 셀을 복제한다. 원본 예시는 정보 상세 뒤 한 줄 간격으로,
결과평가는 측정 결과 다음에 이어진다. 개인정보 처리계획은 새 페이지에서 시작한다.
따라서 내용량에 따른 쪽 수와 행 높이는 달라질 수 있다.
한글에서 편집할 수 있는 HWPX 3종, HTML 확인본 3종, 입력내용 JSON이
작업별 `심의위원회 심의자료` 폴더와 전체 ZIP에 포함된다.

| 항목 | 입력 근거 |
| --- | --- |
| 데이터명 | 화면 입력 또는 원본 파일명 |
| 유형·규모 | 실제 원본/합성 행·열 수와 확장자 |
| 특이사항 | 화면 입력 또는 결측·중복·식별자 후보 탐지 현황 |
| 정보 개요 | 화면 입력과 실제 데이터 구조 |
| 정보 상세 | 전체 컬럼의 자료형, 정보영역, 짧은 항목 설명; 공통 항목은 원본·합성 문서에 동일 설명 사용 |
| 정보 분류 | 자동 분석 또는 API의 항목별 입력; `준식별자`와 `일반정보`로 정규화 |
| 원본 예시 | 실제 첫 1행 공개, `※N행 중 1행` 표시; 빈 데이터는 0행 |
| 합성 예시 | 실제 합성 출력 처음 5행과 생성 행 수; 5행 미만이면 실제 표시 행 수 |
| 개인정보 처리계획 | 표 상단은 제목만, 처리방법은 `그대로 사용` / `유지`, 비고는 `원본데이터 증강생성 (N행 → M행)` |
| 측정결과 | 구별 위험도(구간화 원본 중복 비율), 일차원 분포 유사성(JSD) 두 줄; 실패·생략·NaN은 미측정 |

정보 상세 표는 전체 컬럼 수에 따라 늘어난다. 정보 개요는 분류 종류별로 집계하고,
개인정보 처리계획은 원본의 다단 헤더와 데이터셋명 세로 병합을 유지하며
병합 행 수를 조정한다. 한글에서 긴 세로 병합 셀이 잘리지 않도록 개인정보 표는
8개 항목 단위로 원본 머리글을 반복하고 새 페이지로 나눈다.
HTML 확인본에서는 페이지별 개인정보 표를 하나로 합쳐 데이터셋명과 비고를 한 번만 표시한다.
한글의 표 구조는 이 HTML 처리의 영향을 받지 않는다. 정보 상세 표는
여러 쪽으로 이어진다. 예시는 표당 최대 8개 열을 기준으로 균등 분할한다.
12개 열은 6·6, 11개 열은 6·5로 나누며 표 안의 열 폭도 균등하게 조정한다.
처리계획의 고정 문구는 제출 서식용이며 실제 생성 설정을 변경하지 않는다.
N과 M은 각각 실제 원본·합성 행 수다. 추가 처리계획 설명은 문서에 출력하지 않는다.
측정결과 표는 소수 둘째 자리로 표시하며, 아주 작은 양수는 0으로 보이지 않도록 `<0.01`로 표시한다.
세부 Anonymeter·열별 JSD 지표는 평가 JSON에 유지한다. 총평은 데이터명·모델·대표 측정값으로
작성하며, 값이 없거나 실패한 결과를 0 또는 적정 판정으로 대체하지 않는다.
원본 예시를 포함한 모든 산출물은 심의 전 담당자 검토 대상이다.

서식과 문구는 `docs/심의자료_세종`, `심의자료_전남광주`, `심의자료_충남`의
원본·합성 명세서와 측정결과서를 참고했다. 참고 문서를 모델에 재학습시키는 방식이 아니라,
기존 HWPX 템플릿에 실행 결과를 바인딩하는 방식이다. 수식·그림은 유지하고 구별 위험도의
설명은 실제 구현인 구간화 중복 비율에 맞춘다. 이 비율은 재식별 확률 자체가 아니다.

항목 설명은 담당자 입력, 규칙 기반 설명, 모호한 항목의 OpenAI 보정 순으로 정한다.
현재 운영 모델은 `gpt-5-nano`이며 동일 생성 결과를 두 명세서가 재사용하므로 중복 호출하지 않는다.
목표는 10~20자의 한국어 명사구다. 30자를 넘거나 불필요한 서술형인 GPT 응답은
사용하지 않고 규칙 설명을 사용한다. API 미설정·실패 시에도 규칙 설명으로 문서를 생성한다.

정보영역은 심의자료 표준에 맞춰 `준식별자`와 `일반정보` 두 값만 사용한다.
업로드 프로파일과 HWPX 문서는 같은 자동 분류 규칙을 적용한다. 자동 분석은
컬럼명과 실제 값 패턴을 함께 본다. 이름, 전화, 이메일, 주소, 지역, 성별,
연령대, 학교, 직급, 부서, 학력, 소득, 가구, 장애처럼 개인 구분이나 조합
식별에 쓰일 수 있는 항목은 `준식별자`로 분류한다. 컬럼명이 `항목A`처럼
모호하더라도 값이 `세종/충남`, `남/여`, `10대/20대`, `일반고/특성화고`,
`고졸/대졸`, `1분위/2분위`, `관리자/사무 종사자` 같은 패턴이면
`준식별자`로 분류한다. 경험, 참여, 만족도, 희망, 수요, 인식, 여부, 수준,
점수, 평가, 조사연도처럼 설문 응답이나 분석 문항에 가까운 항목은
`일반정보`로 분류한다. 사람이 입력한 항목별 분류가 있어도 두 값 밖의 표현은
이 기준으로 정규화한다.

화면의 **심의자료 한글 문서 입력**에서 데이터명, 특이사항, 정보 개요,
개인정보 처리계획을 작성한 뒤 합성을 실행하고 ZIP을 받는다.
원본 파일명이 `1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx`처럼
연번으로 시작하면 산출물도 정리된 제출 폴더 관례를 따른다. 데이터명은 문서 본문에서
`고등학생 진로수업 경험과 진로정보 인식_세종`으로 표시하고, 심의자료 파일명은
`1. 원본데이터 명세서(고등학생 진로수업 경험과 진로정보 인식_세종).hwpx`처럼
연번을 앞에 둔다. 합성 데이터 파일도 같은 경우
`1. (합성) 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx` 형식으로 저장한다.
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

일반 문서 변환기의 HWP → HWPX 기능은 리눅스/도커에서 한글 COM 없이 동작한다.
이 경로는 HWP 5.x 본문 텍스트를 추출해 `python-hwpx`로 새 HWPX 패키지를 생성하고,
필수 구성요소와 HWPX 문서 구조를 검증한 뒤에만 성공으로 처리한다. 원본의 복잡한
표, 그림, 수식, 쪽 설정까지 완전 보존해야 하는 변환은 Windows 한글 COM 변환을 사용한다.

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
- `docker-compose.yml`과 `infra/nginx`: 사내망 Docker 운영에 사용한다. Nginx가
  80번 포트에서 현재 통합 서버로 요청을 전달한다. 이전 API/웹 분리용 Dockerfile은 제거했다.
- `docs/reference/합성데이터_수행_코드.ipynb`: 노트북 구현 근거이며 실행·배포에는 사용하지 않는다.
  실험용 샘플 데이터는 저장소에서 제거했다.
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
