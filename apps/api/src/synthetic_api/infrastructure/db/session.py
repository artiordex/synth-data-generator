# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: session.py
# 경로: apps/api/src/synthetic_api/infrastructure/db/session.py
# 목적: 비동기/동기 데이터베이스 엔진 및 세션 팩토리를 제공함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, declarative_base

from synthetic_api.core.config import settings



engine = create_engine(

    settings.DATABASE_URL,

    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

)



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



# db 정보를 조회하여 반환함
def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()
