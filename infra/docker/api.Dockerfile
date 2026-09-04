FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     curl     && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY packages/synthetic_engine packages/synthetic_engine
COPY apps/api apps/api

RUN pip install --no-cache-dir -e packages/synthetic_engine -e apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n