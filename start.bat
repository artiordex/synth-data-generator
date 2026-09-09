@echo off
chcp 65001 > nul
echo ===================================================================
echo   식약처 AI 합성데이터 생성기 & 가명처리 스튜디오 시작 (Port: 8000)
echo ===================================================================

cd /d "%~dp0"

if not exist "apps\web\dist\index.html" (
    echo [1/2] 프론트엔드 빌드 파일 생성 중...
    cd apps\web
    call npm run build
    cd ..\..
)

echo [2/2] 통합 서버 가동 및 브라우저 실행 (http://127.0.0.1:8000)
start http://127.0.0.1:8000
uv run uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000
pause
