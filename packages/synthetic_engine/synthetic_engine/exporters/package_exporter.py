# -*- coding: utf-8 -*-
from __future__ import annotations
import re
import shutil
import zipfile
from pathlib import Path

LEADING_SEQUENCE_RE = re.compile(r"^\s*(?P<number>\d+)\.\s*(?P<name>.+?)\s*$")


def split_leading_sequence(stem: str) -> tuple[str | None, str]:
    match = LEADING_SEQUENCE_RE.match(stem)
    if not match:
        return None, stem.strip()
    return f"{match.group('number')}.", match.group("name").strip()


def review_document_filename(title: str, dataset_name: str, sequence: str | None = None, suffix: str = ".hwpx") -> str:
    prefix = f"{sequence} " if sequence else ""
    return f"{prefix}{title}({safe_path_part(dataset_name, '데이터')}){suffix}"


def synthetic_data_filename(dataset_name: str, sequence: str | None = None, suffix: str = ".xlsx") -> str:
    clean_name = safe_path_part(dataset_name, "데이터")
    if sequence:
        return f"{sequence} (합성) {clean_name}{suffix}"
    return f"합성데이터_{clean_name}{suffix}"


def safe_path_part(value: str | None, default: str) -> str:
    text = (value or "").strip() or default
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:80] or default

def make_submission_package_dirs(base_output_dir: Path, job_id: str, original_filename: str) -> dict[str, Path]:
    dataset_name = safe_path_part(Path(original_filename).stem, "데이터")
    package_root = base_output_dir / f"{job_id}_{dataset_name}"

    dirs = {
        "root": package_root,
        "original": package_root / "원본데이터",
        "synthetic": package_root / "합성데이터",
        "review": package_root / "심의위원회 심의자료",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    return dirs

def create_package_zip(package_dir: Path, zip_output_path: Path) -> Path:
    zip_output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    return zip_output_path
