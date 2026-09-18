"""Locate document templates without coupling exporters to the source tree."""
from __future__ import annotations

import os
from pathlib import Path


TEMPLATE_DIR_ENV = "SYNTHETIC_ENGINE_TEMPLATE_DIR"


def _unique_existing(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        path = path.expanduser()
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen or not path.is_dir():
            continue
        seen.add(key)
        result.append(path)
    return result


def default_template_dirs(*, include_user_downloads: bool = False) -> list[Path]:
    """Return available template directories in deterministic precedence order."""
    candidates: list[Path] = []
    configured = os.getenv(TEMPLATE_DIR_ENV)
    if configured:
        candidates.append(Path(configured))

    package_root = Path(__file__).resolve().parents[1]
    candidates.append(package_root / "templates")
    candidates.append(Path.cwd() / "storage" / "templates")
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "storage" / "templates")

    if include_user_downloads:
        candidates.append(Path.home() / "Downloads")
    return _unique_existing(candidates)


def resolve_template_dir(template_dir: Path | None = None) -> Path:
    """Resolve a usable template directory or raise an actionable error."""
    if template_dir is not None:
        candidates = [Path(template_dir)]
    elif os.getenv(TEMPLATE_DIR_ENV):
        candidates = [Path(os.environ[TEMPLATE_DIR_ENV])]
    else:
        candidates = default_template_dirs()
    resolved = _unique_existing(candidates)
    if resolved:
        return resolved[0]

    hint = f" 환경변수 {TEMPLATE_DIR_ENV}에 템플릿 디렉터리를 지정하세요."
    requested = str(template_dir) if template_dir is not None else "the configured locations"
    raise FileNotFoundError(f"템플릿 디렉터리를 찾을 수 없습니다 ({requested}).{hint}")


__all__ = ["TEMPLATE_DIR_ENV", "default_template_dirs", "resolve_template_dir"]
