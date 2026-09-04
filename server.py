import sys
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "apps" / "api"))
sys.path.insert(0, str(BASE_DIR / "packages" / "synthetic_engine"))

from app.main import app, start

if __name__ == "__main__":
    start()
