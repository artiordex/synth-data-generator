#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
echo "Starting Enterprise Synthetic Data Platform Dev Servers..."
uv run --locked --all-packages uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000 --reload &
npm run dev --workspace apps/web &
wait
