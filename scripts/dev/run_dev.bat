@echo off
echo ========================================================
echo  Enterprise Synthetic Data Platform - Dev Server Runner
echo ========================================================

cd /d "%~dp0..\.."
set "UV_CMD=uv"
where uv >nul 2>nul
if errorlevel 1 set "UV_CMD=%CD%\.venv\Scripts\uv.exe"
call "%UV_CMD%" sync --locked --all-packages --inexact
if errorlevel 1 exit /b 1
start "Backend API Server" /b "%UV_CMD%" run --locked --all-packages uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000 --reload
call npm run dev

echo Backend running on http://127.0.0.1:8000/api/v1/docs
echo Frontend running on http://localhost:5173\n
