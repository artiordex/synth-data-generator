from pathlib import Path

from synthetic_api.core.config import settings
from synthetic_api.main import app


def test_src_layout_resolves_workspace_paths():
    root = Path(__file__).resolve().parents[3]
    assert settings.ROOT_DIR == root
    assert settings.UPLOAD_DIR == root / "storage/uploads"
    assert settings.OUTPUT_DIR == root / "storage/outputs"
    assert (settings.ROOT_DIR / "storage/templates/원본데이터 명세서.hwpx").exists()
    assert "/api/v1/synthesis/start" in app.openapi()["paths"]
