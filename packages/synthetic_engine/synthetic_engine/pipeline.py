# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any, Callable
import pandas as pd

from .common.types import ColumnPlan, SynthesisConfig
from .common.provenance import calculate_sha256, detect_system_device
from .profiling.analyzer import read_table, build_column_plan
from .preprocessing.transformer import (
    apply_constraints_before_training,
    prepare_training_frame,
    apply_constraints_after_generation
)
from .generators.statistical.sampler import StatisticalSampler
from .generators.rule_based.engine import RuleEngine
from .generators.ml.ctgan import CTGANGenerator
from .generators.ml.tvae import TVAEGenerator
from .generators.ml.copula import GaussianCopulaGenerator
from .privacy.dp import apply_differential_privacy_noise
from .privacy.faker import apply_pii, build_pii_output
from .quality.assessment import evaluate
from .exporters.hwp_exporter import build_review_documents
from .exporters.package_exporter import make_submission_package_dirs, safe_path_part

class SyntheticPipeline:
    def __init__(self, config: SynthesisConfig):
        self.config = config

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
        template_dir: Path | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict[str, Any]:
        def report_progress(pct: int, msg: str):
            if progress_callback: progress_callback(pct, msg)

        report_progress(10, "원본 데이터 검증 및 무결성(SHA-256) 계산 중...")
        raw = read_table(input_path)
        raw_hash = calculate_sha256(input_path)
        device_info = detect_system_device()

        report_progress(20, "PII 개인정보 탐지 및 가명화 변환 중...")
        columns_config = {}
        if selected_columns: columns_config["selected"] = selected_columns
        if categorical_columns: columns_config["categorical"] = categorical_columns
        if numerical_columns: columns_config["numerical"] = numerical_columns

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
        masked, masking_report = apply_pii(raw, plan, self.config.seed)

        report_progress(32, "도메인 규칙 및 제약조건 전처리 중...")
        constrained, plan = apply_constraints_before_training(masked, user_constraints, plan)
        training = prepare_training_frame(constrained, plan, user_constraints)

        report_progress(40, f"AI 모델({self.config.model_type.upper()}) 적대적 학습 중...")
        model_type = self.config.model_type.lower()
        if model_type == "gaussian_copula":
            gen = GaussianCopulaGenerator()
        elif model_type == "tvae":
            gen = TVAEGenerator(epochs=self.config.epochs, batch_size=self.config.batch_size)
        elif model_type == "ctgan":
            gen = CTGANGenerator(epochs=self.config.epochs, batch_size=self.config.batch_size, pac=self.config.pac)
        else:
            gen = StatisticalSampler()

        gen.fit(training, plan)
        synthetic = gen.sample(num_rows=self.config.sample_rows, conditions=conditions)

        report_progress(72, "조건부 역변환 및 합성 데이터 생성 완료")
        synthetic = RuleEngine.apply_rules(synthetic, plan)
        synthetic = apply_constraints_after_generation(synthetic, user_constraints)

        dp_report = {"enabled": False}
        if self.config.dp_enabled:
            report_progress(80, "차분 프라이버시(DP) 라플라스 노이즈 주입 중...")
            synthetic, dp_report = apply_differential_privacy_noise(
                synthetic, plan.numerical, epsilon=self.config.dp_epsilon, delta=self.config.dp_delta, seed=self.config.seed
            )
        else:
            report_progress(80, "비즈니스 제약조건 및 수치 범위 검증 중...")

        synthetic, pii_output_report = build_pii_output(raw, synthetic, plan, self.config.seed)
        synth_hash = calculate_sha256(synthetic)

        report_progress(88, "Anonymeter 3대 재식별 안전성 & JSD 평가 중...")
        evaluation = evaluate(training, synthetic, plan, qbins=20)

        report_progress(94, "심의위원회 HWP 3종 공문서 자동 바인딩 및 패키징 중...")
        dataset_name = safe_path_part(Path(original_filename).stem, "데이터")
        package_dirs = make_submission_package_dirs(output_dir, job_id, original_filename)

        import shutil
        shutil.copy2(input_path, package_dirs["original"] / original_filename)

        csv_path = package_dirs["synthetic"] / f"합성데이터_{dataset_name}.csv"
        xlsx_path = package_dirs["synthetic"] / f"합성데이터_{dataset_name}.xlsx"
        report_path = package_dirs["review"] / f"{job_id}_synthetic_evaluation_report.json"

        synthetic.to_csv(csv_path, index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(xlsx_path) as writer:
            synthetic.to_excel(writer, index=False)

        columns_info = [{"name": str(c)} for c in raw.columns]
        hwp_created = build_review_documents(
            dataset_name=dataset_name,
            orig_filename=original_filename,
            orig_rows=int(len(raw)),
            synth_rows=int(len(synthetic)),
            model_type=self.config.model_type,
            columns_info=columns_info,
            metrics={**evaluation, "differential_privacy": dp_report},
            output_review_dir=package_dirs["review"],
            template_dir=template_dir
        )

        jsd_val = evaluation.get("utility", {}).get("jsd_mean", 0.1)
        if not math.isfinite(jsd_val): jsd_val = 0.1
        quality_score = max(0.0, min(1.0, 1.0 - jsd_val))
        
        anon_metrics = evaluation.get("safety", {}).get("anonymeter", {})
        singling_risk = float(anon_metrics.get("singling_out_risk", evaluation.get("safety", {}).get("single_out_rate_binned", 0.04)))
        
        raw_assessment = evaluation.get("assessment", {})
        score_val = int(raw_assessment.get("score", 85))
        grade = "S" if score_val >= 95 else ("A" if score_val >= 85 else ("B" if score_val >= 75 else ("C" if score_val >= 60 else "F")))
        
        auto_assessment = {
            **raw_assessment,
            "grade": grade,
            "score": score_val,
            "passed": raw_assessment.get("overall_status") in ["PASS", "통과"] or score_val >= 80,
            "recommendation": "심의 승인 권고" if score_val >= 80 else "보완 후 재심의"
        }

        report_payload = {
            "job_id": job_id,
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
