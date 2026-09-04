"""Build evidence-backed data and fill copies of the original Hangul templates."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

import pandas as pd

from ..common.types import ColumnPlan
from ..profiling.analyzer import scan_pii_columns
from .package_exporter import safe_path_part
from .template_binding import write_template

PENDING = "담당자 확인 필요"
ACTIONS = {"drop": "삭제", "mask": "마스킹", "hash": "SHA-256 해시 변환", "faker": "가상 값 생성"}


def clean(value: Any) -> str:
    # XML 1.0 cannot represent most ASCII control characters.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))


def measured(value: Any) -> str:
    try:
        number = float(value)
        return f"{number:.4f}" if math.isfinite(number) else "미측정"
    except (TypeError, ValueError):
        return "미측정"


def build_review_context(
    raw: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan,
    original_filename: str, model_type: str, metrics: dict[str, Any],
    department_name: str = "", project_purpose: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    detected = scan_pii_columns(raw)
    overrides = metadata.get("columns", {})
    name = metadata.get("dataset_name") or Path(original_filename).stem
    columns = []
    for col in raw.columns:
        series = raw[col]
        spec = overrides.get(str(col), {})
        classification = spec.get("information_type") or ("식별자 후보" if col in detected else "분류 확인 필요")
        action = plan.pii.get(col, {}).get("action")
        method = ACTIONS.get(action, "합성 생성" if col in synthetic.columns else "출력 제외")
        columns.append({
            "name": str(col),
            "dtype": "수치형" if col in plan.numerical else ("범주형" if col in plan.categorical else str(series.dtype)),
            "information_type": classification,
            "description": spec.get("description") or f"{col} 항목; 결측 {int(series.isna().sum()):,}건, 고유값 {int(series.nunique()):,}개. 의미·코드 정의: {PENDING}",
            "missing": int(series.isna().sum()), "unique": int(series.nunique()),
            "synthetic_description": spec.get("description") or (
                f"{col} 항목; 합성 출력 결측 {int(synthetic[col].isna().sum()):,}건, 고유값 {int(synthetic[col].nunique()):,}개. 의미·코드 정의: {PENDING}"
                if col in synthetic.columns else "출력 제외"
            ),
            "method": method,
            "note": "자동 탐지 결과 확인 필요" if col in detected else PENDING,
        })

    # Original values are deliberately redacted, including undetected identifiers.
    # Keep actual row/column topology and nulls; never substitute old sample rows.
    examples = [
        ["결측" if pd.isna(value) else "[원본값 비공개]" for value in row]
        for row in raw.head(5).itertuples(index=False, name=None)
    ]
    synth_examples = [
        ["결측" if pd.isna(value) else ("[식별값 비공개]" if col in detected or col in plan.pii else clean(value))
         for col, value in zip(synthetic.columns, row)]
        for row in synthetic.head(5).itertuples(index=False, name=None)
    ]
    safety, utility = metrics.get("safety", {}), metrics.get("utility", {})
    anon = safety.get("anonymeter", {})
    measurements = [
        ["안전성", "구간화 원본 중복 비율", measured(safety.get("single_out_rate_binned")), "구간화한 합성 행 중 원본에도 존재하는 행의 비율; 재식별 확률과 다름"],
        ["유용성", "일차원 분포 유사성(JSD)", measured(utility.get("jsd_mean")), "열별 분포 차이의 평균; 작을수록 유사"],
    ]
    for key, label in [("singling_out", "단일 식별 위험도"), ("linkability", "연결 위험도"), ("inference", "속성 추론 위험도")]:
        details = anon.get(key, {})
        valid = anon.get("evaluated_with_anonymeter") is True and details.get("status") not in {"ERROR", "NOT_EVALUATED"}
        measurements.append(["안전성", label, measured(anon.get(f"{key}_risk")) if valid else "미측정", "Anonymeter; 측정 실패·생략 시 미측정"])
    assessment = metrics.get("assessment", {})
    incomplete = any(row[2] == "미측정" for row in measurements)
    assessment_text = "측정 누락 또는 실패: 보완 후 검토 필요" if incomplete else f"자동 평가: {assessment.get('overall_status', PENDING)} / {measured(assessment.get('score'))}점"
    guards = metrics.get('guardrails', {})
    if guards:
        assessment_text += (f"; 원본 일치 처리: {guards.get('policy', 'strict')}, "
                            f"최종 일치 {guards.get('final_exact_duplicates', 0)}행")
    return {
        "dataset_name": clean(name), "original_filename": original_filename,
        "original_rows": len(raw), "synthetic_rows": len(synthetic),
        "columns": columns, "synthetic_columns": [str(c) for c in synthetic.columns],
        "department": department_name or PENDING, "purpose": project_purpose or PENDING,
        "overview": metadata.get("overview") or f"{name}: {len(raw):,}행, {len(raw.columns):,}개 항목의 정형데이터. 수집 배경·출처·기간: {PENDING}",
        "special_notes": metadata.get("special_notes") or f"결측값 {int(raw.isna().sum().sum()):,}개, 중복행 {int(raw.duplicated().sum()):,}건, 식별자 후보 {len(detected):,}개 항목. 자동 탐지·분류 결과 검토 필요.",
        "privacy_plan": metadata.get("privacy_plan") or f"항목별 실제 처리방법은 아래 표 참조. 이용 목적: {project_purpose or PENDING}. 보유기간·접근권한·제공범위·파기절차: {PENDING}",
        "original_examples": examples, "synthetic_examples": synth_examples,
        "model": model_type, "measurements": measurements,
        "jsd_by_column": [[str(k), measured(v)] for k, v in utility.get("jsd_by_column", {}).items()],
        "assessment": assessment_text + ". 자동 산출 참고자료이며 최종 적정성은 심의위원회에서 판단.",
        "dp": metrics.get("differential_privacy", {}),
    }


def build_review_documents(*, raw: pd.DataFrame, synthetic: pd.DataFrame,
                           plan: ColumnPlan, original_filename: str, model_type: str,
                           metrics: dict[str, Any], output_review_dir: Path,
                           department_name: str = "", project_purpose: str = "",
                           metadata: dict[str, Any] | None = None,
                           template_dir: Path | None = None) -> dict[str, Path]:
    context = build_review_context(raw, synthetic, plan, original_filename, model_type, metrics, department_name, project_purpose, metadata)
    name = safe_path_part(context["dataset_name"], "데이터")
    template_dir = template_dir or Path(__file__).resolve().parents[4] / "storage" / "templates"
    outputs = {}
    sources = {}
    for kind, title in [("original_spec", "원본데이터 명세서"), ("synthetic_spec", "합성데이터 명세서"), ("review_report", "합성데이터 안전성 및 유용성 측정결과서")]:
        path = output_review_dir / f"{title}({name}).hwpx"
        sources[kind] = write_template(context, kind, template_dir, path)
        outputs[kind] = path
    context["templates"] = sources
    (output_review_dir / "심의자료_입력내용.json").write_text(json.dumps(context, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return outputs
