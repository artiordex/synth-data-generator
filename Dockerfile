# ==========================================
# Stage 1: Build React Frontend with Node.js
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

# ==========================================
# Stage 2: Ultra-Light Python API Runtime
# ==========================================
FROM python:3.12-slim
WORKDIR /app

# Install minimal system dependencies for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy package configurations and source modules
COPY pyproject.toml package.json ./
COPY packages packages
COPY apps/api apps/api

# Install core engine & API packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e packages/synthetic_engine -e apps/api

# Copy pre-built React frontend assets from Stage 1
COPY --from=frontend-builder /app/apps/web/dist /app/apps/web/dist
COPY storage storage
COPY experiments experiments
COPY server.py ./

# Expose Render default port (10000) and standard port (8000)
EXPOSE 10000 8000

ENV PORT=10000 \
    PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --port ${PORT:-10000}"]
