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


def infer_dataset_group(dataset_name: str | None) -> str | None:
    """Infer the trailing folder group from names like '데이터명_세종'."""
    text = (dataset_name or "").strip()
    if "_" not in text:
        return None
    group = text.rsplit("_", 1)[-1].strip()
    if not group or len(group) > 20 or re.search(r"\s", group):
        return None
    return safe_path_part(group, "그룹")


def submission_folder_name(kind: str, dataset_name: str | None = None) -> str:
    group = infer_dataset_group(dataset_name)
    return f"{kind}_{group}" if group else kind


def numbered_submission_filename(filename: str, index: int) -> str:
    """Replace any leading sequence with the batch sequence: '01. name.ext'."""
    path = Path(filename)
    _, clean_stem = split_leading_sequence(path.stem)
    return f"{index:02d}. {safe_path_part(clean_stem, '데이터')}{path.suffix}"


def review_document_filename(title: str, dataset_name: str, sequence: str | None = None, suffix: str = ".hwpx") -> str:
    prefix = f"{sequence} " if sequence else ""
    return f"{prefix}{title}({safe_path_part(dataset_name, '데이터')}){suffix}"


def synthetic_data_filename(dataset_name: str, sequence: str | None = None, suffix: str = ".xlsx") -> str:
    clean_name = safe_path_part(dataset_name, "데이터")
    if sequence:
        return f"{sequence} {clean_name}{suffix}"
    return f"합성데이터_{clean_name}{suffix}"


def safe_path_part(value: str | None, default: str) -> str:
    text = (value or "").strip() or default
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:80] or default

def make_submission_package_dirs(base_output_dir: Path, job_id: str, original_filename: str) -> dict[str, Path]:
    _, parsed_dataset_name = split_leading_sequence(Path(original_filename).stem)
    dataset_name = safe_path_part(parsed_dataset_name, "데이터")
    package_root = base_output_dir / f"{job_id}_{dataset_name}"

    dirs = {
        "root": package_root,
        "original": package_root / submission_folder_name("원본데이터", dataset_name),
        "synthetic": package_root / submission_folder_name("합성데이터", dataset_name),
        "review": package_root / submission_folder_name("심의자료", dataset_name),
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
# =============================================================================
# 파일명: package_exporter.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/package_exporter.py
# 목적: 심의 제출용 결과 파일과 ZIP 패키지를 생성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
