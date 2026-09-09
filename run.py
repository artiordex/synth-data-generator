# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: run.py
# 경로: run.py
# 목적: 프론트엔드 빌드와 로컬 서버 실행을 조정함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
import os
import sys
import subprocess
import webbrowser
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def check_frontend_build():
    """프론트엔드 빌드 산출물의 존재 여부를 확인하고 필요하면 빌드함"""
    dist_index = ROOT_DIR / "apps" / "web" / "dist" / "index.html"
    if not dist_index.exists():
        print("[INFO] 프론트엔드 빌드 파일(apps/web/dist)이 없어 빌드를 먼저 진행합니다...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(ROOT_DIR / "apps" / "web"), check=True, shell=True)
            print("[SUCCESS] 프론트엔드 빌드 완료!")
        except Exception as e:
            print(f"[WARN] 프론트엔드 빌드 실패: {e}. FastAPI API 모드로 시작합니다.")

def open_browser():
    """로컬 서버 시작 후 기본 브라우저를 열음"""
    time.sleep(1.5)
    print("\n[INFO] 웹 브라우저를 엽니다: http://127.0.0.1:8000\n")
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass

def main():
    check_frontend_build()
    
    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("=" * 65)
    print("  식약처 AI 합성데이터 생성기 & 가명처리 스튜디오 통합 서버")
    print("  - 웹 UI 접속: http://127.0.0.1:8000 (또는 http://localhost:8000)")
    print("  - API 문서: http://127.0.0.1:8000/docs")
    print("  - 서버 종료: Ctrl + C")
    print("=" * 65)
    
    import uvicorn
    uvicorn.run("synthetic_api.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
