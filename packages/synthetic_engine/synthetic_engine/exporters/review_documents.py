"""Build evidence-backed data and fill copies of the original Hangul templates."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

import pandas as pd

from ..common.types import ColumnPlan
from ..profiling.analyzer import classify_information_type, normalize_information_type, scan_pii_columns
from .openai_text import env_bool, polish_column_description
from .package_exporter import review_document_filename, split_leading_sequence
from .template_binding import write_template

PENDING = "담당자 확인 필요"
ACTIONS = {"drop": "삭제", "mask": "마스킹", "hash": "SHA-256 해시 변환", "faker": "가상 값 생성"}


def readable_column_name(value: Any) -> str:
    text = clean(value).strip()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def general_response_subject(column_name: str) -> str:
    parts = [part.strip() for part in re.split(r"[_\-]+", column_name) if part.strip()]
    if len(parts) >= 2:
        return readable_column_name(" ".join(parts[1:] + parts[:1]))
    return readable_column_name(column_name)


def describe_original_column(column_name: Any, information_type: str, series: pd.Series) -> str:
    name = readable_column_name(column_name)
    compact = re.sub(r"\s+", "", name)

    if information_type == "준식별자":
        quasi_rules = [
            (r"거주지역|^지역$|시도|시군구|행정구역", "개인의 거주지역"),
            (r"고등학교유형|학교유형", "개인의 학교유형"),
            (r"학교소재지", "개인의 학교소재지 유형"),
            (r"주소|소재지", "개인의 소재지 정보"),
            (r"성별", "개인의 성별"),
            (r"연령대|연령|나이|생년|출생", "개인의 연령대"),
            (r"최종학력|학력|졸업", "개인의 학력 유형"),
            (r"직급|직위", "개인의 직급 유형"),
            (r"부서|소속", "개인의 소속 정보"),
            (r"소득|월평균|가구소득", "개인의 소득구간"),
            (r"가구|세대", "개인의 가구 특성"),
            (r"장애", "개인의 장애 여부 또는 유형"),
            (r"이름|성명|전화|휴대폰|이메일|메일|주민|외국인|여권", "개인의 직접 식별자 후보"),
        ]
        for pattern, description in quasi_rules:
            if re.search(pattern, compact, re.IGNORECASE):
                return description
        return f"개인의 {name} 정보"

    if re.search(r"조사연도|조사년도|연도|년도", compact):
        return f"{name} 정보"
    if re.search(r"여부$", compact):
        return f"{name} 응답정보"
    if re.search(r"점수|수준|정도|등급|단계|빈도|횟수", compact):
        return f"{general_response_subject(str(column_name))} 정보"
    if re.search(r"경험|참여|만족|희망|수요|인식|인지|평가|효과|사고|피해|응답|의향|계획|관심|활동|상담|체험", compact):
        return f"{general_response_subject(str(column_name))} 응답정보"
    return f"{name} 응답정보"


def is_ambiguous_description(column_name: Any, information_type: str, description: str) -> bool:
    name = readable_column_name(column_name)
    if information_type == "준식별자":
        return description == f"개인의 {name} 정보"
    return description == f"{name} 응답정보"


def sample_values_for_prompt(series: pd.Series) -> list[str]:
    return [clean(value)[:40] for value in series.dropna().astype(str).drop_duplicates().head(8).tolist()]


def maybe_polish_description(column_name: Any, information_type: str, series: pd.Series, base_description: str) -> str:
    if env_bool("OPENAI_COLUMN_DESCRIPTION_ONLY_AMBIGUOUS", True) and not is_ambiguous_description(column_name, information_type, base_description):
        return base_description
    polished = polish_column_description(
        column_name=str(column_name),
        information_type=information_type,
        base_description=base_description,
        sample_values=sample_values_for_prompt(series),
    )
    return polished or base_description


def describe_information_area(group: str, columns: list[dict[str, Any]], dataset_name: str) -> str:
    names = "".join(col["name"] for col in columns)
    compact_dataset = re.sub(r"\s+", "", dataset_name)
    compact = re.sub(r"\s+", "", names)
    subject = "고등학생 응답자" if re.search(r"고등학생|고등학교", compact_dataset + compact) else "응답자"

    if group == "준식별자":
        return f"{subject}의 개인 특성정보"
    if re.search(r"진로|직업|진학|수업|상담|체험", compact_dataset + compact):
        return "진로수업 경험 및 진로인식 정보"
    if re.search(r"개인정보|정보보호|침해|사고|피해", compact_dataset + compact):
        return "개인정보보호 인식 및 침해사고 경험 정보"
    if re.search(r"학습|성향|동기", compact_dataset + compact):
        return "학습성향 및 자기주도 학습 정보"
    if re.search(r"창업", compact_dataset + compact):
        return "창업활동 및 창업관심 정보"
    return "조사 문항 응답 및 일반 현황 정보"


def build_information_area_summaries(columns: list[dict[str, Any]], dataset_name: str) -> dict[str, str]:
    summaries = {}
    for group in ("준식별자", "일반정보"):
        grouped = [col for col in columns if col["information_type"] == group]
        if grouped:
            summaries[group] = describe_information_area(group, grouped, dataset_name)
    return summaries


def default_special_notes(raw: pd.DataFrame, detected: dict[str, Any]) -> str:
    missing = int(raw.isna().sum().sum())
    duplicated = int(raw.duplicated().sum())
    detected_count = len(detected)
    notes = [f"결측값 {missing:,}개", f"중복행 {duplicated:,}건", f"식별자 후보 {detected_count:,}개 항목"]
    if missing == 0 and duplicated == 0 and detected_count == 0:
        return "결측값, 중복행 및 직접 식별자 후보가 자동 점검 기준에서 발견되지 않음. 정보영역 및 항목 설명은 자동 분류 결과 기준으로 작성되어 담당자 검토 필요."
    return f"{', '.join(notes)}이 확인됨. 정보영역 및 항목 설명은 자동 분류 결과 기준으로 작성되어 담당자 검토 필요."


def clean(value: Any) -> str:
    # XML 1.0 cannot represent most ASCII control characters.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))


def measured(value: Any) -> str:
    try:
        number = float(value)
        return f"{number:.4f}" if math.isfinite(number) else "미측정"
    except (TypeError, ValueError):
        return "미측정"


def report_value(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "미측정"
    if not math.isfinite(number) or not 0 <= number <= 1:
        return "미측정"
    return "<0.01" if 0 < number < 0.005 else f"{number:.2f}"


def report_model_name(model_type: str) -> str:
    return {"ctgan": "CTGAN", "tvae": "TVAE", "gaussian_copula": "Gaussian Copula",
            "statistical": "통계 기반 모형"}.get(model_type, clean(model_type))


def build_review_context(
    raw: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan,
    original_filename: str, model_type: str, metrics: dict[str, Any],
    department_name: str = "", project_purpose: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    detected = scan_pii_columns(raw)
    overrides = metadata.get("columns", {})
    sequence, parsed_name = split_leading_sequence(Path(original_filename).stem)
    name = metadata.get("dataset_name") or parsed_name
    columns = []
    for col in raw.columns:
        series = raw[col]
        spec = overrides.get(str(col), {})
        classification = (
            normalize_information_type(spec.get("information_type"))
            or classify_information_type(col, series, col in detected)
        )
        action = plan.pii.get(col, {}).get("action")
        method = ACTIONS.get(action, "합성 생성" if col in synthetic.columns else "출력 제외")
        description = spec.get("description") or maybe_polish_description(
            col,
            classification,
            series,
            describe_original_column(col, classification, series),
        )
        columns.append({
            "name": str(col),
            "dtype": "수치형" if col in plan.numerical else ("범주형" if col in plan.categorical else str(series.dtype)),
            "information_type": classification,
            "description": description,
            "missing": int(series.isna().sum()), "unique": int(series.nunique()),
            "synthetic_description": description,
            "method": method,
            "note": "자동 탐지 결과 확인 필요" if col in detected else PENDING,
        })

    # The original specification includes one actual source row as its example.
    examples = [
        ["결측" if pd.isna(value) else clean(value) for value in row]
        for row in raw.head(1).itertuples(index=False, name=None)
    ]
    synth_examples = [
        ["결측" if pd.isna(value) else clean(value) for value in row]
        for row in synthetic.head(5).itertuples(index=False, name=None)
    ]
    safety, utility = metrics.get("safety", {}), metrics.get("utility", {})
    report_measurements = [
        ["안전성", "구별 위험도", report_value(safety.get("single_out_rate_binned"))],
        ["유용성", "일차원 분포 유사성(JSD)", report_value(utility.get("jsd_mean"))],
    ]
    report_missing = any(row[2] == "미측정" for row in report_measurements)
    report_model = report_model_name(model_type)
    report_summary = (
        f"※ 데이터명: {clean(name)}\n"
        f"※ {report_model} 모델을 이용하여 합성데이터를 생성하고, 안전성·유용성 검증 진행함\n"
        + ("※ 측정 누락 또는 실패: 보완 후 검토 필요"
           if report_missing else
           f"※ 구별 위험도 {report_measurements[0][2]}, 일차원 분포 유사성(JSD) {report_measurements[1][2]}. 최종 적정성은 심의 검토 필요")
    )
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
        "document_sequence": sequence,
        "original_rows": len(raw), "synthetic_rows": len(synthetic),
        "columns": columns, "synthetic_columns": [str(c) for c in synthetic.columns],
        "department": department_name or PENDING, "purpose": project_purpose or PENDING,
        "overview": metadata.get("overview") or f"{name}: {len(raw):,}행, {len(raw.columns):,}개 항목의 정형데이터. 수집 배경·출처·기간: {PENDING}",
        "special_notes": metadata.get("special_notes") or default_special_notes(raw, detected),
        "information_area_summaries": build_information_area_summaries(columns, clean(name)),
        "privacy_plan": metadata.get("privacy_plan") or "",
        "original_examples": examples, "synthetic_examples": synth_examples,
        "model": model_type, "measurements": measurements,
        "report_model": report_model, "report_measurements": report_measurements,
        "report_summary": report_summary,
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
    template_dir = template_dir or Path(__file__).resolve().parents[4] / "storage" / "templates"
    outputs = {}
    sources = {}
    for kind, title in [("original_spec", "원본데이터 명세서"), ("synthetic_spec", "합성데이터 명세서"), ("review_report", "합성데이터 안전성 및 유용성 측정결과서")]:
        path = output_review_dir / review_document_filename(title, context["dataset_name"], context.get("document_sequence"))
        sources[kind] = write_template(context, kind, template_dir, path)
        outputs[kind] = path
    context["templates"] = sources
    (output_review_dir / "심의자료_입력내용.json").write_text(json.dumps(context, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return outputs
# =============================================================================
# 파일명: review_documents.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/review_documents.py
# 목적: 심의용 데이터 설명과 결과 문서를 생성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
