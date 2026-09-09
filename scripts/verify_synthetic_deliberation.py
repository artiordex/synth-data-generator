#!/usr/bin/env python
import os
import sys
import json
import argparse
import time
from pathlib import Path
import pandas as pd

# Add packages/synthetic_engine to path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "synthetic_engine"))

from synthetic_engine import SyntheticPipeline, SynthesisConfig, read_table
from synthetic_engine.exporters.package_exporter import split_leading_sequence, submission_folder_name

def find_raw_datasets():
    base_dir = Path(__file__).resolve().parent.parent
    raw_files = []
    
    # 1. Check docs/원본데이터_*
    docs_dir = base_dir / "docs"
    if docs_dir.exists():
        for path in docs_dir.glob("원본데이터_*/*"):
            if path.is_file() and path.suffix.lower() in [".xlsx", ".xls", ".csv"]:
                raw_files.append(("docs_raw", path))

    # 2. Check storage/outputs/job-*/원본데이터/*
    outputs_dir = base_dir / "storage" / "outputs"
    if outputs_dir.exists():
        for path in list(outputs_dir.glob("job-*/원본데이터*/*")) + list(outputs_dir.glob("job-*/*/원본데이터*/*")):
            if path.is_file() and path.suffix.lower() in [".xlsx", ".xls", ".csv"]:
                raw_files.append(("storage_output_raw", path))

    # 3. Check storage/uploads/*
    uploads_dir = base_dir / "storage" / "uploads"
    if uploads_dir.exists():
        for path in uploads_dir.glob("*"):
            if path.is_file() and path.suffix.lower() in [".csv", ".xlsx"]:
                raw_files.append(("storage_upload", path))

    # Deduplicate by absolute path
    seen = set()
    unique_files = []
    for category, path in raw_files:
        abs_str = str(path.resolve())
        if abs_str not in seen:
            seen.add(abs_str)
            unique_files.append((category, path))

    return unique_files

def verify_dataset(category: str, raw_path: Path, output_base_dir: Path, model_type: str = "statistical"):
    dataset_name = raw_path.stem
    print(f"\n[Audit Target] [{category}] {raw_path.name}")
    
    # Clean file name for directory
    safe_dir_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in dataset_name)
    audit_job_dir = output_base_dir / f"audit_{safe_dir_name}"
    audit_job_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    
    config = SynthesisConfig(
        model_type=model_type,
        sample_rows=300,
        dp_enabled=False
    )
    pipeline = SyntheticPipeline(config=config)

    logs = []
    def on_progress(pct, msg):
        logs.append(f"[{pct}%] {msg}")

    try:
        raw_df = read_table(raw_path)
        result = pipeline.execute(
            input_path=raw_path,
            output_dir=audit_job_dir,
            job_id=f"audit_{int(time.time())}",
            original_filename=raw_path.name,
            department_name="심의자료 전수검증팀",
            progress_callback=on_progress
        )
        
        elapsed = time.time() - start_time
        
        syn_df = result.get("synthetic_df")
        hwp_files = result.get("hwp_files", {})
        package_dirs = result.get("package_dirs", {})
        report_path = result.get("report_path")
        
        review_dir = package_dirs.get("review") if package_dirs else None
        review_input_json = (review_dir / "심의자료_입력내용.json") if review_dir else None
        _, parsed_dataset_name = split_leading_sequence(raw_path.stem)
        expected_original_dir = submission_folder_name("원본데이터", parsed_dataset_name)
        expected_synthetic_dir = submission_folder_name("합성데이터", parsed_dataset_name)
        expected_review_dir = submission_folder_name("심의자료", parsed_dataset_name)
        synthetic_columns = list(syn_df.columns) if syn_df is not None else []
        original_columns = list(raw_df.columns)

        checks = {
            "synthetic_df_valid": syn_df is not None and not syn_df.empty,
            "row_count": len(syn_df) if syn_df is not None else 0,
            "col_count": len(syn_df.columns) if syn_df is not None else 0,
            "original_col_count": len(original_columns),
            "columns_preserved": original_columns == synthetic_columns,
            "missing_columns": [col for col in original_columns if col not in synthetic_columns],
            "extra_columns": [col for col in synthetic_columns if col not in original_columns],
            "hwp_files_count": len(hwp_files),
            "hwp_files_exist": all(Path(v).exists() and Path(v).stat().st_size > 0 for v in hwp_files.values()) if hwp_files else False,
            "eval_report_exists": Path(report_path).exists() if report_path else False,
            "review_input_exists": review_input_json.exists() if review_input_json else False,
            "folder_names_standard": (
                package_dirs.get("original") and Path(package_dirs["original"]).name == expected_original_dir
                and package_dirs.get("synthetic") and Path(package_dirs["synthetic"]).name == expected_synthetic_dir
                and package_dirs.get("review") and Path(package_dirs["review"]).name == expected_review_dir
            ),
            "expected_folders": {
                "original": expected_original_dir,
                "synthetic": expected_synthetic_dir,
                "review": expected_review_dir,
            },
        }

        # Check JSD measurement in evaluation report
        jsd_value = None
        if report_path and Path(report_path).exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    eval_data = json.load(f)
                    jsd_value = eval_data.get("quality_score") or eval_data.get("utility", {}).get("jsd_mean")
            except Exception as e:
                jsd_value = f"Error: {e}"

        status = "PASSED" if all([
            checks["synthetic_df_valid"],
            checks["columns_preserved"],
            checks["folder_names_standard"],
            checks["hwp_files_count"] >= 3,
            checks["hwp_files_exist"],
            checks["eval_report_exists"],
            checks["review_input_exists"]
        ]) else "FAILED"

        return {
            "status": status,
            "category": category,
            "filename": raw_path.name,
            "elapsed_seconds": round(elapsed, 2),
            "checks": checks,
            "jsd_value": jsd_value,
            "output_dir": str(audit_job_dir)
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": "ERROR",
            "category": category,
            "filename": raw_path.name,
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Audit and verify synthetic generation & review document generation across docs/ and storage/")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of datasets to test")
    parser.add_argument("--model", type=str, default="statistical", choices=["statistical", "ctgan"], help="Synthetic model type")
    args = parser.parse_args()

    raw_files = find_raw_datasets()
    print(f"==================================================")
    print(f" Found {len(raw_files)} raw datasets across docs/ and storage/")
    print(f" Model type: {args.model}")
    print(f"==================================================")

    if args.limit:
        raw_files = raw_files[:args.limit]
        print(f" Testing first {args.limit} datasets...")

    base_dir = Path(__file__).resolve().parent.parent
    audit_output_dir = base_dir / "storage" / "outputs" / "deliberation_audit"
    audit_output_dir.mkdir(parents=True, exist_ok=True)

    summary_results = []
    passed_count = 0

    for idx, (category, raw_path) in enumerate(raw_files, 1):
        res = verify_dataset(category, raw_path, audit_output_dir, model_type=args.model)
        summary_results.append(res)
        if res["status"] == "PASSED":
            passed_count += 1
            print(
                f" Result: PASSED (Time: {res['elapsed_seconds']}s, "
                f"Rows: {res['checks']['row_count']}, "
                f"Cols: {res['checks']['original_col_count']} -> {res['checks']['col_count']}, "
                f"Columns preserved: {res['checks']['columns_preserved']}, "
                f"HWPX Docs: {res['checks']['hwp_files_count']})"
            )
        else:
            print(f" Result: {res['status']} - {res.get('error') or res.get('checks')}")

    summary_path = audit_output_dir / "audit_summary_report.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_datasets": len(raw_files),
            "passed_datasets": passed_count,
            "failed_datasets": len(raw_files) - passed_count,
            "results": summary_results
        }, f, ensure_ascii=False, indent=2)

    print("\n==================================================")
    print(f" AUDIT COMPLETE: {passed_count}/{len(raw_files)} PASSED")
    print(f" Summary report saved to: {summary_path}")
    print("==================================================")

if __name__ == "__main__":
    main()
