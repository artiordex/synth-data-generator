import os
import shutil
import tempfile
import pandas as pd
from pathlib import Path
from synthetic_engine import (
    SyntheticPipeline,
    SynthesisConfig,
    DifferentialPrivacyManager,
    AnonymeterValidator
)

def test_full_pipeline_e2e():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # 1. Create realistic sample dataset
        df = pd.DataFrame({
            "고객번호": [f"CUST_{i:04d}" for i in range(100)],
            "고객성명": [f"홍길동{i}" for i in range(100)],
            "나이": [20 + (i % 50) for i in range(100)],
            "소득": [3000 + (i * 100) for i in range(100)],
            "지역": ["서울", "경기", "부산", "대전", "대구"] * 20,
            "구매금액": [150.5 + (i * 2.5) for i in range(100)]
        })
        
        input_csv = temp_dir / "sample_e2e.csv"
        df.to_csv(input_csv, index=False, encoding="utf-8-sig")
        
        output_dir = temp_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Configure Pipeline with DP Laplace Noise & Fast Statistical Sampling
        config = SynthesisConfig(
            model_type="statistical",
            sample_rows=150,
            dp_enabled=True,
            dp_epsilon=1.5
        )
        
        pipeline = SyntheticPipeline(config=config)
        
        progress_records = []
        def on_progress(pct, msg):
            progress_records.append((pct, msg))
            
        result = pipeline.execute(
            input_path=input_csv,
            output_dir=output_dir,
            job_id="test_job_e2e",
            original_filename="sample_e2e.csv",
            department_name="데이터혁신팀",
            progress_callback=on_progress
        )
        
        # 3. Assertions
        assert "synthetic_df" in result
        syn_df = result["synthetic_df"]
        assert len(syn_df) == 150
        assert "고객성명" in syn_df.columns
        assert "나이" in syn_df.columns
        # Every completed job must include the three generated Hangul forms.
        hwp_files = result["hwp_files"]
        assert len(hwp_files) == 3
        if hwp_files:
            assert len(hwp_files) == 3
            for k, v in hwp_files.items():
                assert Path(v).exists()
                assert Path(v).suffix == ".hwpx"
                assert Path(v).stat().st_size > 0
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
