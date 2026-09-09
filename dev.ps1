# UTF-8 Encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  [실시간 개발 모드] 식약처 AI 합성데이터 스튜디오" -ForegroundColor Cyan
Write-Host "  - 프론트엔드 (수정 즉시 실시간 반영): http://localhost:5173" -ForegroundColor Yellow
Write-Host "  - 백엔드 API (수정 즉시 자동 리로드): http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $rootDir) { $rootDir = (Get-Location).Path }
Set-Location $rootDir

# 1. Start Backend API with reload
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rootDir'; uv run uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000 --reload"

# 2. Open browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

# 3. Start Frontend Vite Dev Server
Set-Location "$rootDir\apps\web"
npm run dev
