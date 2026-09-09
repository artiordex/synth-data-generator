# UTF-8 Encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  식약처 AI 합성데이터 생성기 & 가명처리 스튜디오 시작 (Port: 8000)" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $rootDir) { $rootDir = (Get-Location).Path }
Set-Location $rootDir

if (-not (Test-Path "$rootDir\apps\web\dist\index.html")) {
    Write-Host "[1/2] 프론트엔드 빌드 파일 생성 중..." -ForegroundColor Yellow
    Push-Location "$rootDir\apps\web"
    npm run build
    Pop-Location
}

Write-Host "[2/2] 통합 서버 가동 (http://127.0.0.1:8000)..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"

uv run uvicorn synthetic_api.main:app --host 127.0.0.1 --port 8000
