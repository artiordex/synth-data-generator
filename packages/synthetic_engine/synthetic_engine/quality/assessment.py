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
from .correlation import CorrelationEvaluator
from ..privacy.guardrails import PrivacyGuardrails

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
    correlation_report: dict[str, Any] | None = None,
    guardrail_report: dict[str, Any] | None = None,
    quality_threshold: float = 0.8,
) -> dict[str, Any]:
    anon_metrics = anonymeter_report or {}
    singling_risk = anon_metrics.get("singling_out_risk")
    link_risk = anon_metrics.get("linkability_risk")
    inf_risk = anon_metrics.get("inference_risk")
    risks = [singling_risk, link_risk, inf_risk]
    measured = bool(anon_metrics.get('evaluated_with_anonymeter')) and not anon_metrics.get('errors') and all(
        value is not None and math.isfinite(value) for value in risks)

    corr_metrics = correlation_report or {}
    corr_score = float(corr_metrics.get("overall_correlation_score", 1.0))

    gr_metrics = guardrail_report or {}
    mem_risk = gr_metrics.get('memorization_risk_rate')
    dcr_ok = not plan.numerical or (mem_risk is not None and math.isfinite(mem_risk) and mem_risk <= .05)
    distribution_quality = max(0.0, min(1.0, 1.0 - jsd_mean)) if math.isfinite(jsd_mean) else None
    quality_threshold = max(0.0, min(1.0, float(quality_threshold)))
    distribution_ok = distribution_quality is not None and distribution_quality >= quality_threshold

    score = 100
    for risk in risks:
        if risk is not None and risk > 0.05: score -= 15
    if not distribution_ok: score -= 15
    if corr_score < 0.70: score -= 10
    if mem_risk is not None and mem_risk > 0.05: score -= 10
    score = max(score, 0)

    privacy_ok = measured and all(value <= .05 for value in risks) and dcr_ok
    quality_ok = distribution_ok and corr_score >= .70
    overall_status = 'PASS' if privacy_ok and quality_ok else ('FAIL' if measured and score < 60 else 'REVIEW')
    issues: list[dict[str, Any]] = []
    if not distribution_ok:
        issues.append({
            "code": "QUALITY_THRESHOLD",
            "label": "분포 품질 기준 미달",
            "severity": "review",
            "detail": f"분포 품질 점수 {distribution_quality * 100:.1f}%가 기준 {quality_threshold * 100:.1f}%보다 낮습니다." if distribution_quality is not None else "분포 품질 점수를 계산하지 못했습니다.",
            "value": distribution_quality,
            "threshold": quality_threshold,
        })
    if corr_score < 0.70:
        issues.append({
            "code": "CORRELATION_LOW",
            "label": "상관관계 보존율 낮음",
            "severity": "review",
            "detail": f"2D 상관관계 점수 {corr_score * 100:.1f}%가 기준 70.0%보다 낮습니다.",
            "value": corr_score,
            "threshold": 0.70,
        })
    if not measured:
        errors = anon_metrics.get('errors') or {}
        reason = anon_metrics.get('reason') or "안전성 평가가 완료되지 않았습니다."
        issues.append({
            "code": "ANONYMETER_UNMEASURED",
            "label": "Anonymeter 평가 미측정/실패",
            "severity": "review",
            "detail": reason if not errors else f"{reason}: {', '.join(sorted(errors))}",
            "errors": errors,
        })
    else:
        for name, risk in (("singling_out", singling_risk), ("linkability", link_risk), ("inference", inf_risk)):
            if risk is not None and risk > 0.05:
                issues.append({
                    "code": f"ANONYMETER_{name.upper()}",
                    "label": f"Anonymeter {name} 위험도 검토",
                    "severity": "review",
                    "detail": f"{name} 위험도 {risk * 100:.2f}%가 기준 5.00%보다 높습니다.",
                    "value": risk,
                    "threshold": 0.05,
                })
    if plan.numerical and not dcr_ok:
        issues.append({
            "code": "DCR_MEMORIZATION",
            "label": "DCR 근접 레코드 검토",
            "severity": "review",
            "detail": f"수치형 DCR 기억 위험도 {mem_risk * 100:.2f}%가 기준 5.00%보다 높습니다." if mem_risk is not None and math.isfinite(mem_risk) else "수치형 DCR 기억 위험도를 측정하지 못했습니다.",
            "value": mem_risk,
            "threshold": 0.05,
        })

    return {
        "overall_status": overall_status,
        "overall_label": status_label(overall_status),
        "score": score if measured and (not plan.numerical or mem_risk is not None) else None,
        "issues": issues,
        "summary": {
            "privacy_status": "통과" if privacy_ok else "검토 필요",
            "quality_status": "통과" if quality_ok else "검토 필요",
            "quality_threshold": quality_threshold,
            "distribution_quality": distribution_quality,
            "anonymeter_singling_out": singling_risk,
            "anonymeter_linkability": link_risk,
            "anonymeter_inference": inf_risk,
            "memorization_risk": mem_risk,
            "jsd_mean": jsd_mean,
            "correlation_score": corr_score,
        },
        "note": "자동 점검 결과이며 미측정·오류가 있으면 통과로 판정하지 않습니다. " + anon_metrics.get('reason', ''),
    }

def compute_column_distributions(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan,
    n_bins: int = 20,
    top_categories: int = 12
) -> list[dict[str, Any]]:
    distributions = []
    
    # 1. Numerical columns
    for col in plan.numerical:
        if col not in original.columns or col not in synthetic.columns:
            continue
        orig_full = pd.to_numeric(original[col], errors="coerce")
        synth_full = pd.to_numeric(synthetic[col], errors="coerce")
        orig_s, synth_s = orig_full.dropna(), synth_full.dropna()
        
        if not len(orig_full) or not len(synth_full):
            continue

        combined = pd.concat([orig_s, synth_s])
        min_val = float(combined.min()) if len(combined) else 0.0
        max_val = float(combined.max()) if len(combined) else 0.0
        
        if min_val == max_val:
            bin_edges = np.array([min_val - 1.0, min_val + 1.0])
        else:
            bin_edges = np.linspace(min_val, max_val, n_bins + 1)
            
        orig_counts, _ = np.histogram(orig_s, bins=bin_edges)
        synth_counts, _ = np.histogram(synth_s, bins=bin_edges)
        
        orig_total = len(orig_full)
        synth_total = len(synth_full)
        
        bins_data = []
        for i in range(len(bin_edges) - 1):
            low = bin_edges[i]
            high = bin_edges[i + 1]
            if max_val - min_val > 50:
                label = f"{round(low):,} ~ {round(high):,}"
            else:
                label = f"{low:.1f} ~ {high:.1f}"
            
            orig_c = int(orig_counts[i])
            synth_c = int(synth_counts[i])
            orig_pct = round((orig_c / orig_total) * 100, 2) if orig_total > 0 else 0.0
            synth_pct = round((synth_c / synth_total) * 100, 2) if synth_total > 0 else 0.0
            
            bins_data.append({
                "label": label,
                "low": round(float(low), 3),
                "high": round(float(high), 3),
                "original_count": orig_c,
                "synthetic_count": synth_c,
                "original_pct": orig_pct,
                "synthetic_pct": synth_pct,
                "diff_pct": round(synth_pct - orig_pct, 2)
            })

        if orig_full.isna().any() or synth_full.isna().any():
            orig_na, syn_na = int(orig_full.isna().sum()), int(synth_full.isna().sum())
            orig_pct, syn_pct = round(100 * orig_na / orig_total, 2), round(100 * syn_na / synth_total, 2)
            bins_data.append({"label": "결측치(NULL)", "low": None, "high": None,
                              "original_count": orig_na, "synthetic_count": syn_na,
                              "original_pct": orig_pct, "synthetic_pct": syn_pct,
                              "diff_pct": round(syn_pct - orig_pct, 2)})
        col_jsd = numerical_jsd(orig_full, synth_full, bins=n_bins)
        similarity = max(0.0, min(100.0, round((1.0 - col_jsd) * 100, 1))) if math.isfinite(col_jsd) else 90.0

        distributions.append({
            "name": col,
            "type": "numerical",
            "jsd": round(float(col_jsd), 4) if math.isfinite(col_jsd) else 0.05,
            "similarity_pct": similarity,
            "stats": {
                "original": {
                    "count": int(orig_total),
                    "null_count": int(orig_full.isna().sum()),
                    "mean": round(float(orig_s.mean()), 2) if len(orig_s) else None,
                    "std": round(float(orig_s.std()), 2) if len(orig_s) > 1 else 0.0,
                    "median": round(float(orig_s.median()), 2) if len(orig_s) else None,
                    "min": round(float(orig_s.min()), 2) if len(orig_s) else None,
                    "max": round(float(orig_s.max()), 2) if len(orig_s) else None,
                },
                "synthetic": {
                    "count": int(synth_total),
                    "null_count": int(synth_full.isna().sum()),
                    "mean": round(float(synth_s.mean()), 2) if len(synth_s) else None,
                    "std": round(float(synth_s.std()), 2) if len(synth_s) > 1 else 0.0,
                    "median": round(float(synth_s.median()), 2) if len(synth_s) else None,
                    "min": round(float(synth_s.min()), 2) if len(synth_s) else None,
                    "max": round(float(synth_s.max()), 2) if len(synth_s) else None,
                }
            },
            "bins": bins_data
        })

    # 2. Categorical columns
    for col in plan.categorical:
        if col not in original.columns or col not in synthetic.columns:
            continue
        orig_s = original[col].astype(str).fillna("결측치(NULL)")
        synth_s = synthetic[col].astype(str).fillna("결측치(NULL)")
        
        orig_vc = orig_s.value_counts()
        synth_vc = synth_s.value_counts()
        
        combined_vc = (orig_vc.add(synth_vc, fill_value=0)).sort_values(ascending=False)
        top_cats = list(combined_vc.index[:top_categories])
        
        orig_total = len(orig_s)
        synth_total = len(synth_s)
        
        bins_data = []
        for cat in top_cats:
            orig_c = int(orig_vc.get(cat, 0))
            synth_c = int(synth_vc.get(cat, 0))
            orig_pct = round((orig_c / orig_total) * 100, 2) if orig_total > 0 else 0.0
            synth_pct = round((synth_c / synth_total) * 100, 2) if synth_total > 0 else 0.0
            
            bins_data.append({
                "label": str(cat),
                "original_count": orig_c,
                "synthetic_count": synth_c,
                "original_pct": orig_pct,
                "synthetic_pct": synth_pct,
                "diff_pct": round(synth_pct - orig_pct, 2)
            })

        col_jsd = categorical_jsd(orig_s, synth_s)
        similarity = max(0.0, min(100.0, round((1.0 - col_jsd) * 100, 1))) if math.isfinite(col_jsd) else 90.0

        distributions.append({
            "name": col,
            "type": "categorical",
            "jsd": round(float(col_jsd), 4) if math.isfinite(col_jsd) else 0.05,
            "similarity_pct": similarity,
            "stats": {
                "original": {
                    "count": int(orig_total),
                    "unique": int(orig_s.nunique()),
                    "top": str(orig_vc.index[0]) if len(orig_vc) > 0 else "",
                    "top_pct": round((float(orig_vc.iloc[0]) / orig_total) * 100, 1) if len(orig_vc) > 0 else 0.0,
                },
                "synthetic": {
                    "count": int(synth_total),
                    "unique": int(synth_s.nunique()),
                    "top": str(synth_vc.index[0]) if len(synth_vc) > 0 else "",
                    "top_pct": round((float(synth_vc.iloc[0]) / synth_total) * 100, 1) if len(synth_vc) > 0 else 0.0,
                }
            },
            "bins": bins_data
        })

    return distributions

def evaluate(
    original: pd.DataFrame,
    synthetic: pd.DataFrame,
    plan: ColumnPlan,
    qbins: int = 20,
    run_anonymeter_eval: bool = True,
    control: pd.DataFrame | None = None,
    quality_threshold: float = 0.8,
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
        anonymeter_metrics = evaluate_anonymeter(original_eval, synthetic_eval, plan, control=control)

    # 2D Correlation analysis
    correlation_metrics = CorrelationEvaluator.evaluate_correlations(original_eval, synthetic_eval, plan)

    # DCR (Distance to Closest Record) memorization check
    dcr_metrics = PrivacyGuardrails.evaluate_dcr(original_eval, synthetic_eval, plan)

    # Detailed Column Distributions for interactive visual comparison
    column_distributions = compute_column_distributions(original_eval, synthetic_eval, plan, n_bins=qbins)

    assessment = build_auto_assessment(
        original_eval, synthetic_eval, plan, jsd_mean, single_out_rate,
        pii_rescan_candidates, anonymeter_metrics, correlation_metrics, dcr_metrics,
        quality_threshold=quality_threshold,
    )

    return {
        "safety": {
            "single_out_rate_binned": single_out_rate,
            "qbins": qbins,
            "anonymeter": anonymeter_metrics,
            "dcr": dcr_metrics,
        },
        "utility": {
            "jsd_mean": jsd_mean,
            "jsd_by_column": jsd_by_column,
            "correlation": correlation_metrics,
            "column_distributions": column_distributions,
        },
        "column_distributions": column_distributions,
        "assessment": assessment,
    }
