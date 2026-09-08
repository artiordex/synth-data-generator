import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

def find_project_root() -> Path:
    if os.environ.get('ROOT_DIR'):
        return Path(os.environ['ROOT_DIR']).resolve()
    for candidate in Path(__file__).resolve().parents:
        if (candidate / 'pyproject.toml').is_file() and (candidate / 'apps').is_dir() and (candidate / 'packages').is_dir():
            return candidate
    return Path.cwd().resolve()


PROJECT_ROOT = find_project_root()

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

    # Optional OpenAI-assisted review document text polishing
    OPENAI_API_KEY: str = ''
    OPENAI_COLUMN_DESCRIPTION_ENABLED: bool = False
    OPENAI_COLUMN_DESCRIPTION_MODEL: str = ''
    OPENAI_COLUMN_DESCRIPTION_SYSTEM_PROMPT: str = ''
    OPENAI_COLUMN_DESCRIPTION_ONLY_AMBIGUOUS: bool = True
    OPENAI_COLUMN_DESCRIPTION_MAX_OUTPUT_TOKENS: int = 40
    OPENAI_COLUMN_DESCRIPTION_TIMEOUT_SEC: int = 8
    OPENAI_COLUMN_DESCRIPTION_CACHE_TTL_DAYS: int = 30
    OPENAI_COLUMN_DESCRIPTION_CACHE_PATH: Path = PROJECT_ROOT / 'storage' / 'local' / 'column_description_cache.json'
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()

# Ensure critical dirs
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)
