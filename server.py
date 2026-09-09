"""
파일명: server.py
경로: server.py
목적: FastAPI 로컬 서버 실행 진입점을 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09

로컬 실행 명령: uv run --locked --all-packages server.py
"""
from synthetic_api.main import app, start

if __name__ == "__main__":
    start()
