# ==========================================
# Stage 1: Build React Frontend with Node.js
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN npm ci
COPY apps/web apps/web
COPY packages/contracts packages/contracts
RUN npm run build

# ==========================================
# Stage 2: Ultra-Light Python API Runtime
# ==========================================
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /bin/
WORKDIR /app

# Install minimal system dependencies for C-extensions, LibreOffice headless, and Korean fonts
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-nogui \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    fonts-nanum \
    fonts-noto-cjk \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package configurations and source modules
COPY pyproject.toml uv.lock 프로젝트안내.md ./
COPY packages/synthetic_engine packages/synthetic_engine
COPY apps/api apps/api

# Install core engine & API packages
RUN uv sync --locked --all-packages --no-dev

# Copy pre-built React frontend assets from Stage 1
COPY --from=frontend-builder /app/apps/web/dist /app/apps/web/dist
COPY storage/templates/*.hwpx storage/templates/

EXPOSE 8000

ENV PORT=8000 \
    ROOT_DIR=/app \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn synthetic_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
