FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /bin/

WORKDIR /app

ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never ROOT_DIR=/app PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
COPY packages/synthetic_engine packages/synthetic_engine
COPY apps/api apps/api

RUN uv sync --locked --all-packages --no-dev
COPY storage/templates/*.hwpx storage/templates/

EXPOSE 8000

CMD ["uvicorn", "synthetic_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
