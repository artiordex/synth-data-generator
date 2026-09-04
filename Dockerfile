FROM python:3.12-slim

WORKDIR /app

# Install system dependencies & Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy package configs & python code
COPY pyproject.toml package.json ./
COPY packages packages
COPY apps/api apps/api

# Install python workspace packages
RUN pip install --no-cache-dir -e packages/synthetic_engine -e apps/api

# Build React web frontend
COPY apps/web apps/web
WORKDIR /app/apps/web
RUN npm install && npm run build

WORKDIR /app
COPY storage storage
COPY experiments experiments
COPY server.py ./

# Expose default cloud ports (7860 for Hugging Face, 8000/10000 for standard)
EXPOSE 7860 8000 10000

ENV PORT=7860
CMD ["sh", "-c", "uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --port ${PORT:-7860}"]
