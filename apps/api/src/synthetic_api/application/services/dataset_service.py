# =============================================================================
# 파일명: dataset_service.py
# 경로: apps/api/src/synthetic_api/application/services/dataset_service.py
# 목적: 데이터 파일 저장과 프로파일링 작업을 처리함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
import os
import shutil
import uuid
import pandas as pd
from synthetic_engine.profiling.notebook_presets import notebook_settings
from synthetic_engine.profiling.pseudonym_input import read_pseudonym_input
from pathlib import Path
from typing import Dict, Any, List
from synthetic_api.core.config import settings
from synthetic_engine import (
    calculate_sha256,
    read_table,
    infer_columns,
    scan_pii_columns,
    classify_information_type,
)

class DatasetService:
    """업로드 데이터의 저장·검사·프로파일링을 제공함"""

    @staticmethod
    def save_upload_file(file_obj, filename: str, unique: bool = False) -> Dict[str, Any]:
        """업로드 파일을 허용된 저장소에 저장하고 메타데이터를 반환함"""
        original_filename = filename.replace('\\', '/').rsplit('/', 1)[-1]
        if not original_filename or original_filename in {'.', '..'}:
            raise ValueError('올바른 파일명이 필요합니다.')
        filename = f'{uuid.uuid4().hex}_{original_filename}' if unique else original_filename
        dest_path = settings.UPLOAD_DIR / filename
        temporary = settings.UPLOAD_DIR / f'.{uuid.uuid4().hex}.upload'
        size = 0
        try:
            with open(temporary, 'wb') as buffer:
                while chunk := file_obj.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                        raise ValueError(f'파일당 최대 {settings.MAX_FILE_SIZE_MB}MB까지 업로드할 수 있습니다.')
                    buffer.write(chunk)
            temporary.replace(dest_path)
        finally:
            temporary.unlink(missing_ok=True)
            
        sha256_hash = calculate_sha256(dest_path)
        return {
            'filename': filename,
            'original_filename': original_filename,
            'path': str(dest_path),
            'sha256': sha256_hash,
            'size_bytes': dest_path.stat().st_size
        }

    @staticmethod
    def inspect_file(file_name: str, pseudonym: bool = False) -> Dict[str, Any]:
        """저장된 데이터 파일의 구조와 개인정보 후보를 분석함"""
        p = settings.UPLOAD_DIR / file_name
        if not p.exists():
            p = Path(file_name)
            
        if not p.exists():
            raise FileNotFoundError(f'파일을 찾을 수 없습니다: {p}')
            
        df = read_pseudonym_input(p) if pseudonym else read_table(p)
        pii_detected = scan_pii_columns(df)
        cat_cols, num_cols = infer_columns(df, ignored=list(pii_detected.keys()))
        
        columns_info = []
        for col in df.columns:
            series = df[col]
            dtype_str = 'numerical' if col in num_cols else ('pii' if col in pii_detected else 'categorical')
            pii_info = pii_detected.get(col, {})
            
            # Use distinct displayed values from the whole column so repeated
            # leading rows do not hide the other kinds of values in the data.
            unique_values = series.dropna().astype(str).drop_duplicates()
            max_unique_preview = 200
            sample_vals = unique_values.head(max_unique_preview).tolist()
            
            columns_info.append({
                'name': str(col),
                'inferred_type': dtype_str,
                'null_count': int(series.isna().sum()),
                'unique_count': int(series.nunique()),
                'information_type': classify_information_type(col, series, col in pii_detected),
                'pii_detected': col in pii_detected,
                'pii_type': pii_info.get('faker', ''),
                'samples': sample_vals,
                'samples_truncated': len(unique_values) > max_unique_preview,
                'unique_values_total': int(len(unique_values)),
            })
            
        preview_rows = df.head(10).fillna('').to_dict(orient='records')
        sha256_hash = calculate_sha256(p)
        
        return {
            'filename': p.name,
            'row_count': int(len(df)),
            'column_count': int(len(df.columns)),
            'sha256': sha256_hash,
            'columns': columns_info,
            'preview': preview_rows,
            'detected_pii': pii_detected,
            'suggested_categorical': cat_cols,
            'suggested_numerical': num_cols,
            'notebook_preset': notebook_settings(df)
        }
