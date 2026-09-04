@echo off
chcp 65001 > nul
echo ========================================================
echo   인트라넷 합성데이터 생성 웹 서비스 시작
echo   브라우저에서 http://127.0.0.1:8000 접속
echo ========================================================
set UV_PROJECT_ENVIRONMENT=.uv
uv run server.py
pause
