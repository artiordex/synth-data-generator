@echo off
echo ========================================================
echo  Running Enterprise Test Suites
echo ========================================================
cd /d %~dp0..\..
set "UV_CMD=uv"
where uv >nul 2>nul
if errorlevel 1 set "UV_CMD=.venv\Scripts\uv.exe"
call "%UV_CMD%" run --locked --all-packages python -m pytest -v
