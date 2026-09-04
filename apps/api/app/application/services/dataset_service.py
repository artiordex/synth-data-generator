import os
import shutil
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from app.core.config import settings
from app.core.security import calculate_sha256
from synthetic_engine import (
    read_table,
    infer_columns,
    scan_pii_columns
)

class DatasetService:
    @staticmethod
    def save_upload_file(file_obj, filename: str) -> Dict[str, Any]:
        dest_path = settings.UPLOAD_DIR / filename
        with open(dest_path, 'wb') as buffer:
            shutil.copyfileobj(file_obj, buffer)
            
        sha256_hash = calculate_sha256(dest_path)
        return {
            'filename': filename,
            'path': str(dest_path),
            'sha256': sha256_hash,
            'size_bytes': dest_path.stat().st_size
        }

    @staticmethod
    def inspect_file(file_name: str) -> Dict[str, Any]:
        p = settings.UPLOAD_DIR / file_name
        if not p.exists():
            p = Path(file_name)
            
        if not p.exists():
            raise FileNotFoundError(f'파일을 찾을 수 없습니다: {p}')
            
        df = read_table(p)
        pii_detected = scan_pii_columns(df)
        cat_cols, num_cols = infer_columns(df, ignored=list(pii_detected.keys()))
        
        columns_info = []
        for col in df.columns:
            series = df[col]
            dtype_str = 'numerical' if col in num_cols else ('pii' if col in pii_detected else 'categorical')
            pii_info = pii_detected.get(col, {})
            
            sample_vals = [str(x) for x in series.dropna().head(5).tolist()]
            
            columns_info.append({
                'name': str(col),
                'inferred_type': dtype_str,
                'null_count': int(series.isna().sum()),
                'unique_count': int(series.nunique()),
                'pii_detected': col in pii_detected,
                'pii_type': pii_info.get('faker', ''),
                'samples': sample_vals
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
            'suggested_numerical': num_cols
        }
