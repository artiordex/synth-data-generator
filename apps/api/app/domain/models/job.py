from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class JobStatus(BaseModel):
    id: str
    status: str = "pending"  # pending, processing, completed, failed, canceled
    progress: int = 0
    message: str = "대기 중..."
    original_filename: str = ""
    file_path: str = ""
    file_sha256: str = ""
    department_name: str = ""
    project_purpose: str = ""
    model_type: str = "statistical"
    target_rows: int = 1000
    eps: float = 1.0
    quality_threshold: float = 0.8
    quality_score: Optional[float] = None
    reid_risk: Optional[float] = None
    assessment_passed: Optional[bool] = None
    assessment_grade: Optional[str] = None
    assessment_score: Optional[int] = None
    package_dir: Optional[str] = None
    package_zip: Optional[str] = None
    package_folders: Optional[Dict[str, str]] = None
    hwp_files: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class SynthesisRequest(BaseModel):
    file_name: str
    department_name: str = "범용 데이터분석팀"
    project_purpose: str = "합성데이터 생성 및 분석"
    model_type: str = "statistical"
    target_rows: int = 1000
    dp_enabled: bool = False
    eps: float = 1.0
    quality_threshold: float = 0.8
    selected_columns: Optional[List[str]] = None
    categorical_columns: Optional[List[str]] = None
    numerical_columns: Optional[List[str]] = None
    preserve_null_columns: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    constraints: Optional[List[Dict[str, Any]]] = None
    epochs: int = 30
    batch_size: int = 64
