# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ...common.types import ColumnPlan
from ...generators.registry import get_synthesizer
from ...preprocessing.transformer import prepare_training_frame
from ...profiling.analyzer import build_column_plan, read_table
from ...quality.assessment import evaluate
from ...quality.correlation import CorrelationEvaluator
from ...quality.jsd import categorical_jsd, numerical_jsd
from .survey_logic import OrdinalLikertEncoder, SurveyLogicEngine


@dataclass
class SurveyModuleMeta:
    file_key: str
    original_filename: str
    sheet_name: str
    columns: List[str]
    row_count: int
    column_count: int
    unique_columns: List[str] = field(default_factory=list)


@dataclass
class SurveyInspectionResult:
    modules: List[Dict[str, Any]]
    common_keys: List[str]
    is_aligned: bool
    total_rows: int
    total_columns: int
    preview_columns: List[str]
    sample_preview: List[Dict[str, Any]]
    detected_rules: List[Dict[str, Any]] = field(default_factory=list)
    likert_columns_count: int = 0
    likert_column_names: List[str] = field(default_factory=list)
    k_anonymity_risk: Dict[str, Any] = field(default_factory=dict)
    available_regions: List[str] = field(default_factory=list)


class SurveyFusionEngine:
    """
    설문조사 다중 모듈 자동 통합, 조건부 분기(Skip-Logic) 무결성 100% 보정,
    리커트 척도 서열성 보존, 다지역 풀링(Pooled) 조건부 생성 및 엑셀 심의 평가서 생성 엔진.
    """

    @staticmethod
    def inspect_modules(tables: Dict[str, pd.DataFrame]) -> SurveyInspectionResult:
        if not tables:
            raise ValueError("검사할 설문 데이터 테이블이 없습니다.")

        table_names = list(tables.keys())
        first_table = tables[table_names[0]]
        total_rows = len(first_table)

        # 1. 공통 컬럼(후보 준식별자 / 결합 키) 탐색
        common_candidates = set(first_table.columns)
        for name in table_names[1:]:
            common_candidates &= set(tables[name].columns)

        common_keys = [c for c in first_table.columns if c in common_candidates]

        # 2. 1:1 행 매핑 및 정합성 검증
        is_aligned = True
        for name in table_names:
            df = tables[name]
            if len(df) != total_rows:
                is_aligned = False
                break
            if common_keys:
                sub1 = first_table[common_keys].reset_index(drop=True)
                sub2 = df[common_keys].reset_index(drop=True)
                if not sub1.equals(sub2):
                    is_aligned = False
                    break

        # 3. 통합 와이드 테이블 구성
        fused_df, module_metas = SurveyFusionEngine.fuse_tables(tables, common_keys=common_keys)
        merged_cols = list(fused_df.columns)

        # 4. 설문 조건부 분기 규칙 및 리커트 척도 자동 탐지
        detected_rules = SurveyLogicEngine.auto_detect_skip_rules(fused_df)
        likert_maps = OrdinalLikertEncoder.detect_likert_columns(fused_df)

        # 5. 가용 지역(Regions) 탐색
        available_regions: List[str] = []
        if "지역" in fused_df.columns:
            available_regions = [str(r).strip() for r in fused_df["지역"].dropna().unique() if str(r).strip()]

        # 6. k-익명성 희귀 집단 위험도 분석
        k_risk = {}
        if common_keys:
            grp_counts = fused_df.groupby(common_keys).size()
            rare_counts = int((grp_counts < 5).sum())
            k_risk = {
                "total_groups": len(grp_counts),
                "rare_groups_under_5": rare_counts,
                "rare_ratio": round(rare_counts / max(1, len(grp_counts)), 4),
            }

        preview_records = fused_df.head(5).fillna("").to_dict(orient="records")

        return SurveyInspectionResult(
            modules=[
                {
                    "file_key": m.file_key,
                    "original_filename": m.original_filename,
                    "sheet_name": m.sheet_name,
                    "columns": m.columns,
                    "row_count": m.row_count,
                    "column_count": m.column_count,
                    "unique_columns": m.unique_columns,
                }
                for m in module_metas
            ],
            common_keys=common_keys,
            is_aligned=is_aligned,
            total_rows=total_rows,
            total_columns=len(merged_cols),
            preview_columns=merged_cols[:20],
            sample_preview=preview_records,
            detected_rules=detected_rules,
            likert_columns_count=len(likert_maps),
            likert_column_names=list(likert_maps.keys()),
            k_anonymity_risk=k_risk,
            available_regions=available_regions,
        )

    @staticmethod
    def fuse_tables(
        tables: Dict[str, pd.DataFrame],
        common_keys: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[SurveyModuleMeta]]:
        if not tables:
            raise ValueError("통합할 테이블이 없습니다.")

        table_names = list(tables.keys())
        first_table = tables[table_names[0]]
        total_rows = len(first_table)

        if common_keys is None:
            common_candidates = set(first_table.columns)
            for name in table_names[1:]:
                common_candidates &= set(tables[name].columns)
            common_keys = [c for c in first_table.columns if c in common_candidates]

        fused_df = first_table.copy().reset_index(drop=True)
        module_metas: List[SurveyModuleMeta] = []

        # 첫 번째 모듈 메타 등록
        module_metas.append(SurveyModuleMeta(
            file_key=table_names[0],
            original_filename=table_names[0] if table_names[0].endswith((".xlsx", ".csv")) else f"{table_names[0]}.xlsx",
            sheet_name=table_names[0][:31],
            columns=list(first_table.columns),
            row_count=len(first_table),
            column_count=len(first_table.columns),
            unique_columns=[c for c in first_table.columns if c not in common_keys]
        ))

        for name in table_names[1:]:
            df = tables[name].reset_index(drop=True)
            u_cols = [c for c in df.columns if c not in fused_df.columns]
            for col in u_cols:
                fused_df[col] = df[col]

            module_metas.append(SurveyModuleMeta(
                file_key=name,
                original_filename=name if name.endswith((".xlsx", ".csv")) else f"{name}.xlsx",
                sheet_name=name[:31],
                columns=list(df.columns),
                row_count=len(df),
                column_count=len(df.columns),
                unique_columns=u_cols
            ))

        return fused_df, module_metas

    @staticmethod
    def synthesize_fused_survey(
        fused_raw: pd.DataFrame,
        target_rows: int = 1000,
        model_type: str = "ctgan",
        epochs: int = 30,
        batch_size: int = 64,
        pac: int = 1,
        seed: int = 42,
        apply_logic_rules: bool = True,
        preserve_likert_order: bool = True,
        protect_k_anonymity: bool = True,
        conditions: Optional[Dict[str, Any]] = None,
        custom_rules: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        enable_gpu: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        결합된 설문 와이드 테이블을 AI 모델로 학습하고 증강 샘플링하며,
        조건부 분기(Skip-Logic) 무결성 100% 보정 및 리커트 척도 순서성을 보존합니다.
        """
        def report(pct: int, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        report(10, "설문 데이터 구조, 분기 로직 및 리커트 척도 분석 중...")
        # 1. 분기 규칙 탐색
        rules = custom_rules or SurveyLogicEngine.auto_detect_skip_rules(fused_raw)

        # 2. 리커트 척도 순서 보존 인코딩
        training_df = fused_raw.copy()
        likert_maps = {}
        if preserve_likert_order:
            likert_maps = OrdinalLikertEncoder.detect_likert_columns(fused_raw)
            if likert_maps:
                training_df, _ = OrdinalLikertEncoder.encode(fused_raw, likert_maps)

        report(20, "AI 모델 학습 데이터셋 전처리 및 컬럼 플랜 수립...")
        plan = build_column_plan({}, training_df)
        training = prepare_training_frame(training_df, plan, [])

        report(35, f"AI 모델({model_type.upper()}) 설문 문항 간 다차원 상관관계 학습 중...")
        kwargs: Dict[str, Any] = {}
        if model_type in ("ctgan", "tvae"):
            kwargs = {
                "epochs": max(1, epochs),
                "batch_size": max(10, min(len(training), batch_size)),
                "enable_gpu": enable_gpu
            }
            if model_type == "ctgan":
                kwargs["pac"] = max(1, pac)

        synthesizer = get_synthesizer(model_type, **kwargs)
        synthesizer.fit(training, plan)

        cond_msg = f" (조건: {conditions})" if conditions else ""
        report(75, f"합성 설문 응답자 데이터 {target_rows:,}건 생성(Sampling){cond_msg} 중...")
        
        # 조건부 샘플링 또는 일반 샘플링
        if conditions and hasattr(synthesizer, "sample"):
            try:
                synthetic_df = synthesizer.sample(target_rows, conditions=conditions)
            except Exception:
                synthetic_df = synthesizer.sample(target_rows)
        else:
            synthetic_df = synthesizer.sample(target_rows)

        # 3. 리커트 척도 디코딩 (텍스트 복원)
        if preserve_likert_order and likert_maps:
            report(82, "리커트 척도 서열성 기반 텍스트 범주 복원 중...")
            synthetic_df = OrdinalLikertEncoder.decode(synthetic_df, likert_maps)

        # 컬럼 순서 복원
        for col in fused_raw.columns:
            if col not in synthetic_df.columns:
                synthetic_df[col] = fused_raw[col].iloc[0]
        synthetic_df = synthetic_df[fused_raw.columns].copy()

        # 조건부 컬럼 강제 보정 (선택된 지역 등)
        if conditions:
            for c_k, c_v in conditions.items():
                if c_k in synthetic_df.columns:
                    synthetic_df[c_k] = c_v

        # 4. 설문 분기 규칙(Skip-Logic) 무결성 사후 보정
        rectify_report = {}
        if apply_logic_rules and rules:
            report(88, "설문 조건부 분기(Skip-Logic) 모순값 자동 교정 중...")
            synthetic_df, rectify_report = SurveyLogicEngine.apply_skip_rules(synthetic_df, rules)

        # 5. 논리 무결성 최종 검증
        logic_validation = SurveyLogicEngine.validate_survey_logic(synthetic_df, rules)

        report(95, "합성데이터 품질 및 논리 무결성 평가 완료...")
        extra_meta = {
            "rules_count": len(rules),
            "rectify_report": rectify_report,
            "logic_validation": logic_validation,
            "likert_encoded_columns": len(likert_maps),
        }
        return synthetic_df, extra_meta

    @staticmethod
    def split_synthesized(
        fused_synthetic_df: pd.DataFrame,
        modules: List[SurveyModuleMeta]
    ) -> Dict[str, pd.DataFrame]:
        split_results: Dict[str, pd.DataFrame] = {}
        for meta in modules:
            valid_cols = [c for c in meta.columns if c in fused_synthetic_df.columns]
            sub_df = fused_synthetic_df[valid_cols].copy()
            split_results[meta.file_key] = sub_df
        return split_results

    @staticmethod
    def evaluate_survey_synthesis(
        fused_raw: pd.DataFrame,
        fused_syn: pd.DataFrame,
        common_keys: Optional[List[str]] = None,
        rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        plan = build_column_plan({}, fused_raw)
        eval_result = evaluate(fused_raw, fused_syn, plan, run_anonymeter_eval=False)

        # 논리 무결성 검증
        logic_check = SurveyLogicEngine.validate_survey_logic(fused_syn, rules or [])

        # k-익명성 점검
        k_anonymity_report = {}
        if common_keys and set(common_keys).issubset(set(fused_syn.columns)):
            syn_groups = fused_syn.groupby(common_keys, dropna=False).size()
            raw_groups = fused_raw.groupby(common_keys, dropna=False).size()
            k_syn_less_5 = int((syn_groups < 5).sum())
            k_raw_less_5 = int((raw_groups < 5).sum())
            k_anonymity_report = {
                "common_keys": common_keys,
                "raw_distinct_groups": len(raw_groups),
                "raw_rare_groups_under_5": k_raw_less_5,
                "raw_rare_ratio": round(k_raw_less_5 / max(1, len(raw_groups)), 4),
                "syn_distinct_groups": len(syn_groups),
                "syn_rare_groups_under_5": k_syn_less_5,
                "syn_rare_ratio": round(k_syn_less_5 / max(1, len(syn_groups)), 4),
            }

        jsd = eval_result.get('utility', {}).get('jsd_mean')
        quality = max(0.0, min(1.0, 1.0 - jsd)) if jsd is not None and math.isfinite(jsd) else None
        return {
            "overall_quality": quality,
            "utility": eval_result.get("utility", {}),
            "safety": eval_result.get("safety", {}),
            "auto_assessment": eval_result.get("assessment", {}),
            "logic_integrity": logic_check,
            "k_anonymity": k_anonymity_report,
            "raw_rows": len(fused_raw),
            "syn_rows": len(fused_syn),
            "total_columns": len(fused_raw.columns)
        }

    @staticmethod
    def generate_excel_compliance_report(
        eval_metrics: Dict[str, Any],
        fused_raw: pd.DataFrame,
        fused_syn: pd.DataFrame,
        output_path: Path
    ) -> None:
        """
        설문 논리 무결성, 리커트 척도 서열성, k-익명성, JSD 품질이 총망라된
        다중 시트 심의 적정성 평가 엑셀 보고서(00_설문_합성품질_적정성_평가서.xlsx)를 생성합니다.
        """
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # 1. 시트: 종합 심의 요약
            logic_data = eval_metrics.get("logic_integrity", {})
            k_data = eval_metrics.get("k_anonymity", {})
            def percentage(value):
                return f'{value * 100:.1f}%' if isinstance(value, (int, float)) and math.isfinite(value) else '미측정'

            logic_measured = bool(logic_data.get('total_applicable_rows', 0))
            logic_summary = (
                f"{logic_data.get('integrity_score')}% "
                f"{'PASS' if logic_data.get('passed') is True else '검토 필요'} "
                f"(위반: {logic_data.get('total_violations')}건)"
            ) if logic_measured else '미측정 (적용 가능한 규칙 없음)'
            
            summary_rows = [
                {"항목": "평가 대상 데이터", "결과": eval_metrics.get('dataset_name') or '설문 합성데이터'},
                {"항목": "원본 데이터 표본 규모", "결과": f"{eval_metrics.get('raw_rows', len(fused_raw)):,} 건"},
                {"항목": "합성 데이터 생성 규모 (증강)", "결과": f"{eval_metrics.get('syn_rows', len(fused_syn)):,} 건"},
                {"항목": "통합 설문 문항(컬럼) 수", "결과": f"{eval_metrics.get('total_columns', len(fused_raw.columns))} 개"},
                {"항목": "설문 분기(Skip-Logic) 무결성", "결과": logic_summary},
                {"항목": "종합 품질 점수 (JSD/유사도)", "결과": percentage(eval_metrics.get('overall_quality'))},
                {"항목": "상관계수 보존율 (Correlation Score)", "결과": percentage(eval_metrics.get('utility', {}).get('correlation', {}).get('overall_correlation_score'))},
                {"항목": "준식별자 k-익명성 희귀 집단 비율", "결과": f"원본 {percentage(k_data.get('raw_rare_ratio'))} → 합성 {percentage(k_data.get('syn_rare_ratio'))}"},
                {"항목": "개인정보 비식별 심의 적격성", "결과": "담당자 검토 및 승인 필요"},
            ]
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="종합_심의_요약", index=False)

            # 2. 시트: 분기 로직 무결성 검증표
            rule_details = logic_data.get("rule_details", [])
            if rule_details:
                df_rules = pd.DataFrame(rule_details)
                df_rules.rename(columns={
                    "description": "분기 규칙 (Skip-Logic Rule)",
                    "applicable_rows": "해당 행 수",
                    "violations": "위반(모순) 건수",
                    "compliance_rate": "준수율 (1.0 = 100%)",
                }, inplace=True)
                df_rules.to_excel(writer, sheet_name="분기로직_무결성_검증", index=False)
            else:
                pd.DataFrame([{"규칙": "미측정 (적용 가능한 규칙 없음)"}]).to_excel(writer, sheet_name="분기로직_무결성_검증", index=False)

            # 3. 시트: 문항별 분포 유사도 (JSD/TVD)
            col_scores = []
            for col in fused_raw.columns:
                if col in fused_syn.columns:
                    score = 1.0 - categorical_jsd(fused_raw[col], fused_syn[col])
                    col_scores.append({
                        "문항명": col,
                        "데이터 형태": "범주형/리커트",
                        "분포 일치도 (1.0 만점)": round(max(0.0, score), 4) if math.isfinite(score) else None,
                        "품질 판정": "미측정" if not math.isfinite(score) else "참고 지표 (적격 판정 아님)",
                    })
            pd.DataFrame(col_scores).to_excel(writer, sheet_name="문항별_분포_유사도", index=False)

            # 4. 시트: 준식별자 결합 빈도 및 k-익명성
            if "common_keys" in k_data and k_data["common_keys"]:
                ckeys = [k for k in k_data["common_keys"] if k in fused_raw.columns and k in fused_syn.columns]
                if ckeys:
                    raw_c = fused_raw[ckeys].astype(str)
                    syn_c = fused_syn[ckeys].astype(str)
                    raw_grp = raw_c.groupby(ckeys).size().reset_index(name="원본_빈도(N)")
                    syn_grp = syn_c.groupby(ckeys).size().reset_index(name="합성_빈도(N)")
                    merged_k = pd.merge(raw_grp, syn_grp, on=ckeys, how="outer").fillna(0)
                    merged_k["k>=5 충족여부"] = merged_k["합성_빈도(N)"].apply(lambda x: "빈도 기준 충족" if x >= 5 else "주의(소표본)")
                    merged_k.to_excel(writer, sheet_name="준식별자_k익명성_검증", index=False)
