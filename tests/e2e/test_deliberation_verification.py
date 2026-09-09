import os
import shutil
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from synthetic_engine import (
    SyntheticPipeline,
    SynthesisConfig
)

def test_deliberation_verification_e2e():
    """Verify that a raw dataset from docs/ produces valid synthetic data and 3 HWPX review documents."""
    base_dir = Path(__file__).resolve().parents[2]
    raw_files = list(base_dir.glob("docs/원본데이터_*/*.xlsx")) + list(base_dir.glob("docs/원본데이터_*/*.csv"))
    
    assert len(raw_files) > 0, "No raw datasets found in docs/원본데이터_*"
    
    test_raw_file = raw_files[0]
    temp_dir = Path(tempfile.mkdtemp())
    try:
        config = SynthesisConfig(
            model_type="statistical",
            sample_rows=200,
            dp_enabled=False
        )
        pipeline = SyntheticPipeline(config=config)
        
        result = pipeline.execute(
            input_path=test_raw_file,
            output_dir=temp_dir,
            job_id="test_deliberation_job",
            original_filename=test_raw_file.name,
            department_name="심의자료 전수검증팀"
        )
        
        assert "synthetic_df" in result
        syn_df = result["synthetic_df"]
        assert not syn_df.empty
        assert len(syn_df) == 200
        
        hwp_files = result.get("hwp_files", {})
        assert len(hwp_files) == 3
        for k, v in hwp_files.items():
            path = Path(v)
            assert path.exists(), f"HWPX file {v} does not exist"
            assert path.suffix == ".hwpx"
            assert path.stat().st_size > 0
            
        report_path = result.get("report_path")
        assert report_path is not None and Path(report_path).exists()
        
        package_dirs = result.get("package_dirs", {})
        review_dir = package_dirs.get("review")
        assert review_dir is not None
        assert (review_dir / "심의자료_입력내용.json").exists()
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
