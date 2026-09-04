from typing import Optional, Dict, Any, List, Literal
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
    model_type: str = "ctgan"
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

class ReviewColumnMetadata(BaseModel):
    description: str = Field(default="", max_length=2000)
    information_type: str = Field(default="", max_length=100)


class ReviewMetadata(BaseModel):
    dataset_name: str = Field(default="", max_length=200)
    special_notes: str = Field(default="", max_length=5000)
    overview: str = Field(default="", max_length=5000)
    privacy_plan: str = Field(default="", max_length=5000)
    columns: Dict[str, ReviewColumnMetadata] = Field(default_factory=dict)


class SynthesisRequest(BaseModel):
    file_name: str
    original_filename: Optional[str] = None
    department_name: str = "범용 데이터분석팀"
    project_purpose: str = "합성데이터 생성 및 분석"
    model_type: str = "ctgan"
    target_rows: int = Field(default=1000, ge=1)
    dp_enabled: bool = False
    eps: float = 1.0
    quality_threshold: float = 0.8
    selected_columns: Optional[List[str]] = None
    categorical_columns: Optional[List[str]] = None
    numerical_columns: Optional[List[str]] = None
    preserve_null_columns: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    constraints: Optional[List[Dict[str, Any]]] = None
    epochs: Optional[int] = Field(default=None, ge=1)
    batch_size: Optional[int] = Field(default=None, ge=1)
    pac: Optional[int] = Field(default=None, ge=1)
    duplicate_policy: Literal['balanced', 'strict'] = 'balanced'
    seed: int = Field(default=42, ge=0, lt=2**32)
    sampling_batch_size: int = Field(default=800, ge=1)
    max_sampling_attempts: int = Field(default=10, ge=1, le=100)
    enable_gpu: bool = False
    evaluation_excluded_columns: Optional[List[str]] = None
    review_metadata: Optional[ReviewMetadata] = None
