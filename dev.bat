@echo off
chcp 65001 > nul
echo ===================================================================
echo   [실시간 개발 모드] 식약처 AI 합성데이터 스튜디오 가동
echo   - 프론트엔드 (수정 즉시 실시간 반영): http://localhost:5173
echo   - 백엔드 API (수정 즉시 자동 리로드): http://127.0.0.1:8000
echo ===================================================================

cd /d "%~dp0"

echo [1/2] 백엔드 API 서버(Reload 모드) 시작 중...
start "Backend-API" cmd /k "uv run uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] 프론트엔드 실시간 핫 리로딩 서버 시작 중...
timeout /t 2 > nul
start http://localhost:5173

cd apps\web
call npm run dev
