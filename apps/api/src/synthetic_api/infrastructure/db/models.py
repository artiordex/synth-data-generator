from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime

from datetime import datetime

from .session import Base



class JobEntity(Base):

    __tablename__ = "jobs"



    id = Column(String(64), primary_key=True, index=True)

    status = Column(String(32), default="pending")

    progress = Column(Integer, default=0)

    message = Column(String(255), default="대기 중...")

    original_filename = Column(String(255), default="")

    file_path = Column(String(512), default="")

    file_sha256 = Column(String(64), default="")

    department_name = Column(String(128), default="")

    project_purpose = Column(String(255), default="")

    model_type = Column(String(64), default="ctgan")

    target_rows = Column(Integer, default=1000)

    eps = Column(Float, default=1.0)

    quality_threshold = Column(Float, default=0.8)

    quality_score = Column(Float, nullable=True)

    reid_risk = Column(Float, nullable=True)

    assessment_passed = Column(Boolean, nullable=True)

    assessment_grade = Column(String(16), nullable=True)

    assessment_score = Column(Integer, nullable=True)

    package_dir = Column(String(512), nullable=True)

    package_zip = Column(String(512), nullable=True)

    package_folders_json = Column(Text, nullable=True)

    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class AuditLogEntity(Base):

    __tablename__ = "audit_logs"



    id = Column(Integer, primary_key=True, autoincrement=True)

    job_id = Column(String(64), index=True)

    action = Column(String(64))

    actor = Column(String(64), default="system")

    detail = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)


class BatchEntity(Base):
    __tablename__ = "synthesis_batches"
    id = Column(String(64), primary_key=True)
    status = Column(String(32), default="pending")
    items_json = Column(Text, nullable=False)
    package_zip = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
