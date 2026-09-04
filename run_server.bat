@echo off
chcp 65001 > nul
echo ========================================================
echo   인트라넷 합성데이터 생성 웹 서비스 시작
echo   브라우저에서 http://127.0.0.1:8000 접속
echo ========================================================
cd /d "%~dp0"
set "UV_CMD=uv"
where uv >nul 2>nul
if errorlevel 1 (
    if exist ".venv\Scripts\uv.exe" (
        set "UV_CMD=.venv\Scripts\uv.exe"
    ) else (
        echo Install uv first: https://docs.astral.sh/uv/getting-started/installation/
        exit /b 1
    )
)
call "%UV_CMD%" sync --locked --all-packages --inexact
if errorlevel 1 exit /b 1
call "%UV_CMD%" run --locked --all-packages server.py
pause
