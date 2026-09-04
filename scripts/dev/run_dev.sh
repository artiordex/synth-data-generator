#!/bin/bash
echo "Starting Enterprise Synthetic Data Platform Dev Servers..."
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload &
cd apps/web && npm run dev &
wait\n