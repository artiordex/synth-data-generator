# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import math
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable
import pandas as pd

from .common.types import ColumnPlan, SynthesisConfig
from .common.provenance import calculate_sha256, detect_system_device
from .common.randomness import seeded_pipeline
from .profiling.analyzer import read_table, build_column_plan
from .profiling.notebook_presets import notebook_settings
from .preprocessing.transformer import (
    apply_constraints_before_training,
    prepare_training_frame,
)
from .generators.registry import get_synthesizer
from .generators.sampling import sample_valid_rows
from .privacy.faker import apply_pii, build_pii_output
from .quality.assessment import evaluate
from .exporters.review_documents import build_review_documents
from .exporters.package_exporter import make_submission_package_dirs, safe_path_part

class SyntheticPipeline:
    def __init__(self, config: SynthesisConfig):
        self.config = config

    @seeded_pipeline
    def execute(
        self,
        input_path: Path,
        output_dir: Path,
        job_id: str,
        original_filename: str,
        department_name: str = "",
        selected_columns: list[str] | None = None,
        categorical_columns: list[str] | None = None,
        numerical_columns: list[str] | None = None,
        preserve_null_columns: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
        constraints: list[dict[str, Any]] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        project_purpose: str = "",
        review_metadata: dict[str, Any] | None = None,
        evaluation_excluded_columns: list[str] | None = None,
    ) -> dict[str, Any]:
        def report_progress(pct: int, msg: str):
            if progress_callback: progress_callback(pct, msg)

        report_progress(10, "원본 데이터 검증 및 무결성(SHA-256) 계산 중...")
        raw = read_table(input_path)
        raw_hash = calculate_sha256(input_path)
        device_info = detect_system_device()
        preset = notebook_settings(raw)
        defaults = preset['options']
        selected_scope = set(selected_columns if selected_columns is not None else raw.columns)
        if categorical_columns is None and numerical_columns is None:
            categorical_columns = defaults.get('categorical_columns')
            numerical_columns = defaults.get('numerical_columns')
        if preserve_null_columns is None:
            preserve_null_columns = [c for c in defaults.get('preserve_null_columns', []) if c in selected_scope]
        if evaluation_excluded_columns is None:
            evaluation_excluded_columns = [c for c in defaults.get('evaluation_excluded_columns', []) if c in selected_scope]

        # Reserve records before any fitted transformation or model training.
        shuffled = raw.sample(frac=1, random_state=self.config.seed)
        control_size = int(len(raw) * .2) if len(raw) >= 50 else 0
        control_raw = shuffled.iloc[:control_size].copy() if control_size else None
        fit_raw = shuffled.iloc[control_size:].copy() if control_size else raw

        report_progress(20, "PII 개인정보 탐지 및 가명화 변환 중...")
        columns_config = {}
        if selected_columns is not None: columns_config["selected"] = selected_columns
        if categorical_columns is not None: columns_config["categorical"] = categorical_columns
        if numerical_columns is not None: columns_config["numerical"] = numerical_columns
        for names in (selected_columns, categorical_columns, numerical_columns, preserve_null_columns):
            unknown = set(names or []) - set(raw.columns)
            if unknown:
                raise ValueError(f"입력 파일에 없는 컬럼입니다: {sorted(unknown)}")

        user_constraints = list(constraints or [])
        for column in preserve_null_columns or []:
            if not column: continue
            user_constraints.append({
                "type": "null_indicator",
                "column": column,
                "indicator_column": f"{column}_적용",
                "null_label": "비적용",
                "not_null_label": "적용",
            })

        plan_cfg = {"columns": columns_config, "conditions": conditions or {}, "constraints": user_constraints}
        plan = build_column_plan(plan_cfg, raw)
        masked, masking_report = apply_pii(fit_raw, plan, self.config.seed)

        report_progress(32, "도메인 규칙 및 제약조건 전처리 중...")
        constrained, plan = apply_constraints_before_training(masked, user_constraints, plan)
        training = prepare_training_frame(constrained, plan, user_constraints)
        control = None
        if control_raw is not None:
            control_constrained, _ = apply_constraints_before_training(control_raw, user_constraints, plan)
            control = prepare_training_frame(control_constrained, plan, user_constraints, reference=constrained)
        if training.empty or not len(training.columns):
            raise ValueError("학습 가능한 행과 컬럼이 필요합니다.")
        excluded = set(evaluation_excluded_columns or [])
        if excluded - set(training.columns):
            raise ValueError(f"학습 컬럼에 없는 평가 제외 항목입니다: {sorted(excluded - set(training.columns))}")
        eval_plan = ColumnPlan([c for c in plan.categorical if c not in excluded],
                              [c for c in plan.numerical if c not in excluded], plan.ignored, plan.pii, plan.rules)
        if not eval_plan.categorical and not eval_plan.numerical:
            raise ValueError("평가할 컬럼을 최소 1개 선택해야 합니다.")

        report_progress(40, f"AI 모델({self.config.model_type.upper()}) 적대적 학습 중...")
        model_type = self.config.model_type.lower()
        model_kwargs = {}
        if model_type in ("ctgan", "tvae"):
            model_kwargs["epochs"] = self.config.epochs
            model_kwargs["batch_size"] = self.config.batch_size
            model_kwargs["enable_gpu"] = self.config.enable_gpu
            if model_type == "ctgan":
                model_kwargs["pac"] = self.config.pac

        gen = get_synthesizer(model_type, **model_kwargs)

        gen.fit(training, plan)
        synthetic, sampling_report, duplicate_report, dp_report = sample_valid_rows(
            gen, training, plan, self.config, user_constraints, conditions, report_progress)

        synthetic, pii_output_report = build_pii_output(raw, synthetic, plan, self.config.seed)
        synth_hash = calculate_sha256(synthetic)

        report_progress(88, "다차원 품질(JSD, 2D 상관관계) 및 안전성(Anonymeter, DCR) 종합 평가 중...")
        evaluation = evaluate(
            training,
            synthetic,
            eval_plan,
            qbins=20,
            control=control,
            quality_threshold=self.config.quality_threshold,
        )
        if duplicate_report.get('final_exact_duplicates', 0):
            evaluation['assessment']['overall_status'] = 'REVIEW'
            evaluation['assessment']['overall_label'] = '검토 필요'
            evaluation['assessment']['note'] += ' 원본의 빈번한 조합과 일치하는 생성 행이 포함되어 있습니다.'
            evaluation['assessment'].setdefault('issues', []).append({
                "code": "FINAL_EXACT_DUPLICATES",
                "label": "원본 조합 일치 레코드 감지",
                "severity": "review",
                "detail": (
                    f"생성 결과 {duplicate_report.get('final_exact_duplicates')}건이 "
                    "원본의 빈번한 값 조합과 일치합니다. 범주형 조합이 적은 데이터에서는 정상 패턴일 수 있어 수동 검토가 필요합니다."
                ),
                "value": duplicate_report.get('final_exact_duplicate_rate'),
                "threshold": 0,
            })
        evaluation['guardrails'] = duplicate_report

        report_progress(94, "심의위원회 한글(HWPX) 3종 문서 생성 및 패키징 중...")
        dataset_name = safe_path_part(Path(original_filename).stem, "데이터")
        package_dirs = make_submission_package_dirs(output_dir, job_id, original_filename)

        # Save model checkpoint for reuse
        try:
            gen.save(package_dirs["root"] / "model_checkpoint.pkl")
        except Exception:
            pass

        import shutil
        shutil.copy2(input_path, package_dirs["original"] / original_filename)

        csv_path = package_dirs["synthetic"] / f"합성데이터_{dataset_name}.csv"
        xlsx_path = package_dirs["synthetic"] / f"합성데이터_{dataset_name}.xlsx"
        report_path = package_dirs["review"] / f"{job_id}_synthetic_evaluation_report.json"

        synthetic.to_csv(csv_path, index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(xlsx_path) as writer:
            synthetic.to_excel(writer, index=False)

        hwp_created = build_review_documents(
            raw=raw,
            synthetic=synthetic,
            plan=plan,
            original_filename=original_filename,
            model_type=model_type,
            metrics={**evaluation, "differential_privacy": dp_report},
            output_review_dir=package_dirs["review"],
            department_name=department_name,
            project_purpose=project_purpose,
            metadata=review_metadata,
        )

        jsd_val = evaluation.get("utility", {}).get("jsd_mean", 0.1)
        if not math.isfinite(jsd_val): jsd_val = 0.1
        quality_score = max(0.0, min(1.0, 1.0 - jsd_val))
        
        anon_metrics = evaluation.get("safety", {}).get("anonymeter", {})
        singling_risk = anon_metrics.get('singling_out_risk')
        
        raw_assessment = evaluation.get("assessment", {})
        score_val = raw_assessment.get('score')
        grade = None if score_val is None else ('S' if score_val >= 95 else 'A' if score_val >= 85 else 'B' if score_val >= 75 else 'C' if score_val >= 60 else 'F')
        passed = raw_assessment.get('overall_status') == 'PASS'
        
        auto_assessment = {
            **raw_assessment,
            "grade": grade,
            "score": score_val,
            "passed": passed,
            "recommendation": "자동 점검 통과" if passed else "검토 필요"
        }

        report_payload = {
            "job_id": job_id,
            "config": {
                **asdict(self.config),
                "cat_cols_train": plan.categorical, "num_cols_train": plan.numerical,
                "cat_cols_eval": eval_plan.categorical, "num_cols_eval": eval_plan.numerical,
                "evaluation_excluded_columns": sorted(excluded),
                "constraints": user_constraints, "conditions": conditions or {},
                "effective_batch_size": getattr(gen, "batch_size", None),
                "notebook_preset": preset['name'],
                "holdout": {'training_rows': len(training), 'control_rows': control_size,
                            'fraction': .2, 'split_before_training': True, 'seed': self.config.seed},
                "numeric_jsd": "histogram_with_null_bucket", "qbins": 20,
                "versions": {name: version(name) for name in ("sdv", "ctgan", "numpy", "pandas", "torch")},
                "seed_scope": "NumPy/Python/PyTorch training RNG; SDV deterministic sampling stream",
            },
            "sampling": sampling_report,
            "overall_quality": quality_score,
            "quality_score": quality_score,
            "reid_risk": singling_risk,
            "auto_assessment": auto_assessment,
            "provenance": {
                "raw_data_sha256": raw_hash,
                "synthetic_data_sha256": synth_hash,
                "device": device_info,
            },
            "input": {"filename": original_filename, "rows": len(raw), "columns": list(raw.columns)},
            "output": {
                "package_dir": str(package_dirs["root"]),
                "csv_file": str(csv_path),
                "xlsx_file": str(xlsx_path),
                "hwp_files": [str(f) for f in hwp_created.values()],
                "rows": len(synthetic),
            },
            "differential_privacy": dp_report,
            "guardrails": duplicate_report,
            **evaluation
        }

        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, ensure_ascii=False)

        report_progress(100, "합성 및 심의 패키지 생성 완료")

        return {
            "synthetic_df": synthetic,
            "report": report_payload,
            "package_dirs": package_dirs,
            "csv_path": csv_path,
            "xlsx_path": xlsx_path,
            "report_path": report_path,
            "hwp_files": hwp_created,
            "raw_hash": raw_hash,
            "synth_hash": synth_hash,
            "device_info": device_info,
        }
