# 합성데이터 생성 플랫폼 백엔드 API

FastAPI 기반 백엔드입니다. 계층별 책임을 분리해 다음 영역을 독립적으로 관리합니다.

- API 요청과 작업 상태를 표현하는 도메인 모델
- 데이터 점검과 합성 실행을 조정하는 애플리케이션 서비스
- SQLite·SQLAlchemy 저장소를 연결하는 인프라 어댑터
- `/api/v1` 아래의 버전 관리 API 라우터

## 디렉터리 구조

```text
apps/api/
  pyproject.toml
  src/synthetic_api/
    main.py
    routes/v1/
    application/services/
    domain/models/
    infrastructure/db/             # SQLAlchemy schema and session
    infrastructure/repositories/   # job and audit persistence
    core/
  tests/
```

저장소 애플리케이션 경로는 `apps/api`이며, 가져올 수 있는 Python 패키지 이름은 `synthetic_api`입니다. 다음 명령은 저장소 루트에서 실행합니다.

```sh
uv sync --locked --all-packages
uv run --locked --all-packages uvicorn synthetic_api.main:app --reload
uv run --locked --all-packages python -m pytest apps/api/tests
```

Render는 루트 Dockerfile에서 `synthetic_api.main:app`을 실행합니다. 공개 API 경로는 `/api/v1/...` 형식을 유지합니다. 실행 데이터는 저장소의 `storage` 디렉터리에 두며, 배포 작업 공간은 `ROOT_DIR`로 명시할 수 있습니다.

비어 있는 자리 표시용 디렉터리는 만들지 않습니다. 생성되는 `__pycache__`와 `synthetic_api.egg-info`는 무시 대상이며 필요하면 제거할 수 있습니다.
