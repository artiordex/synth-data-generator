# Synthetic Data Generation Platform - Backend API

FastAPI backend with explicit boundaries:
- Domain models for API and job state
- Application services for dataset inspection and synthesis orchestration
- Infrastructure adapters for SQLite/SQLAlchemy persistence
- Versioned FastAPI routes under `/api/v1`

## Layout

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

The repository app is `apps/api`; its importable Python package is `synthetic_api`.
Run from the workspace root:

```sh
uv sync --locked --all-packages
uv run --locked --all-packages uvicorn synthetic_api.main:app --reload
uv run --locked --all-packages python -m pytest apps/api/tests
```

Render starts `synthetic_api.main:app` from the root Dockerfile. Public API URLs
remain `/api/v1/...`. Runtime data stays in the workspace `storage` directory;
`ROOT_DIR` can explicitly select the deployment workspace.

Empty placeholder directories are intentionally omitted. Generated `__pycache__`
and `synthetic_api.egg-info` directories are ignored and may be safely removed.
