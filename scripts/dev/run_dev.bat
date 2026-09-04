@echo off
echo ========================================================
echo  Enterprise Synthetic Data Platform - Dev Server Runner
echo ========================================================

start "Backend API Server" cmd /k "cd /d %~dp0..\.. && .\.uv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload"
start "Frontend Web Server" cmd /k "cd /d %~dp0..\..\apps\web && npm run dev"

echo Backend running on http://127.0.0.1:8000/api/v1/docs
echo Frontend running on http://localhost:5173\n