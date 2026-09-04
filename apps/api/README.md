# Synthetic Data Generation Platform - Backend API

FastAPI-based Enterprise Backend implementing Clean Architecture principles:
- Domain layer (pure business models & repository interfaces)
- Application layer (services orchestrating data processing & synthesis)
- Infrastructure layer (SQLite/SQLAlchemy DB, Local storage, Synthetic Engine integration)
- Routes layer (FastAPI REST v1 endpoints)

## Layout

```text
apps/api/
  pyproject.toml
  src/synthetic_api/
    main.py
    routes/v1/
    application/services/
    domain/models/
    infrastructure/
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
