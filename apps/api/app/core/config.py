import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = 'Enterprise Synthetic Data Platform API'
    VERSION: str = '2.1.0'
    API_V1_PREFIX: str = '/api/v1'
    
    # Paths
    ROOT_DIR: Path = PROJECT_ROOT
    STORAGE_DIR: Path = PROJECT_ROOT / 'storage'
    UPLOAD_DIR: Path = PROJECT_ROOT / 'storage' / 'uploads'
    OUTPUT_DIR: Path = PROJECT_ROOT / 'storage' / 'outputs'
    LOCAL_DB_DIR: Path = PROJECT_ROOT / 'storage' / 'local'
    DATABASE_URL: str = f'sqlite:///{PROJECT_ROOT}/storage/local/app.db'
    
    # Defaults
    MAX_FILE_SIZE_MB: int = 100
    DEFAULT_TIMEOUT_SEC: int = 600
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()

# Ensure critical dirs
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)
