# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from ..common.types import ColumnPlan
from ..profiling.analyzer import scan_pii_columns
from ..validation.anonymeter import evaluate_anonymeter
from .jsd import categorical_jsd, numerical_jsd, binned_keys

def status_by_threshold(value: float | None, pass_max: float, review_max: float, lower_is_better: bool = True) -> str:
    if value is None or not math.isfinite(value): return "REVIEW"
    if lower_is_better:
        if value <= pass_max: return "PASS"
        if value <= review_max: return "REVIEW"
        return "FAIL"
    if value >= pass_max: return "PASS"
    if value >= review_max: return "REVIEW"
    return "FAIL"

def status_label(status: str) -> str:
    return {"PASS": "통과", "REVIEW": "검토 필요", "FAIL": "실패"}.get(status, status)

def build_auto_assessment(
    original_eval: pd.DataFrame,
    synthetic_eval: pd.DataFrame,
    plan: ColumnPlan,
    jsd_mean: float,
    single_out_rate: float,
    pii_rescan_candidates: dict[str, dict[str, Any]],
    anonymeter_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    anon_metrics = anonymeter_report or {}
    singling_risk = float(anon_metrics.get("singling_out_risk", single_out_rate))
    link_risk = float(anon_metrics.get("linkability_risk", 0.0))
    inf_risk = float(anon_metrics.get("inference_risk", 0.0))

    score = 100
    if singling_risk > 0.05: score -= 15
    if link_risk > 0.05: score -= 15
    if inf_risk > 0.05: score -= 15
    if jsd_mean > 0.05: score -= 15
    score = max(score, 0)

    overall_status = "PASS" if score >= 80 else ("REVIEW" if score >= 60 else "FAIL")

    return {
        "overall_status": overall_status,
        "overall_label": status_label(overall_status),
        "score": score,
        "summary": {
            "privacy_status": "통과" if singling_risk <= 0.05 and link_risk <= 0.05 and inf_risk <= 0.05 else "검토 필요",
            "quality_status": "통과" if jsd_mean <= 0.05 else "검토 필요",
            "anonymeter_singling_out": singling_risk,
            "anonymeter_linkability": link_risk,
            "anonymeter_inference": inf_risk,
            "jsd_mean": jsd_mean,
        },
        "note": "EU GDPR 29조 및 개인정보보호위원회 3대 프라이버시 측정 기준을 반영한 자동 점검 결과입니다.",
    }

def evaluate(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan,
    qbins: int = 20,
    run_anonymeter_eval: bool = True
) -> dict[str, Any]:
    comparable_columns = [column for column in plan.categorical + plan.numerical if column in original.columns and column in synthetic.columns]
    original_eval = original[comparable_columns].copy()
    synthetic_eval = synthetic[comparable_columns].copy()

    reference = pd.concat([original_eval, synthetic_eval], ignore_index=True)
    original_keys = set(binned_keys(original_eval, plan.categorical, plan.numerical, qbins, reference))
    synthetic_keys = binned_keys(synthetic_eval, plan.categorical, plan.numerical, qbins, reference)
    single_out_rate = float(synthetic_keys.isin(original_keys).mean()) if len(synthetic_keys) else 0.0

    jsd_by_column = {}
    for column in plan.categorical:
        if column in original_eval.columns and column in synthetic_eval.columns:
            jsd_by_column[column] = categorical_jsd(original_eval[column], synthetic_eval[column])

    for column in plan.numerical:
        if column in original_eval.columns and column in synthetic_eval.columns:
            jsd_by_column[column] = numerical_jsd(original_eval[column], synthetic_eval[column], qbins)

    jsd_mean = float(np.mean(list(jsd_by_column.values()))) if jsd_by_column else math.nan
    pii_rescan_candidates = scan_pii_columns(synthetic)

    anonymeter_metrics = {}
    if run_anonymeter_eval:
        anonymeter_metrics = evaluate_anonymeter(original_eval, synthetic_eval, plan)

    assessment = build_auto_assessment(original_eval, synthetic_eval, plan, jsd_mean, single_out_rate, pii_rescan_candidates, anonymeter_metrics)

    return {
        "safety": {
            "single_out_rate_binned": single_out_rate,
            "qbins": qbins,
            "anonymeter": anonymeter_metrics,
        },
        "utility": {
            "jsd_mean": jsd_mean,
            "jsd_by_column": jsd_by_column,
        },
        "assessment": assessment,
    }
