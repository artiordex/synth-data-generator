"""Local entrypoint. Run with `uv run --locked --all-packages server.py`."""
from synthetic_api.main import app, start

if __name__ == "__main__":
    start()
