# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# 표준 한국어 5점 리커트 척도 정의
STANDARD_LIKERT_SCALES = [
    # 1. 만족도 척도
    ["매우 불만족", "불만족", "보통", "만족", "매우 만족"],
    # 2. 동의/인식 척도
    ["전혀 그렇지 않다", "그렇지 않다", "보통이다", "그렇다", "매우 그렇다"],
    # 3. 필요도 척도
    ["전혀 필요 없음", "필요 없음", "보통", "필요함", "매우 필요함"],
    # 4. 빈도 척도 (가정 내 대화 등)
    ["두 달에 1회 이하", "월 1-2회정도", "주 1회정도", "주 2-3회정도", "거의 매일"],
    # 5. 준비도 척도
    ["전혀 안함", "거의 안함", "보통", "많이 하고 있음", "매우 많이 하고 있음"],
    # 6. 인지도 척도
    ["전혀 모름", "잘 모름", "보통임", "잘 알고 있음", "매우 잘 알고 있음"],
    # 7. 관심도 척도
    ["전혀 관심이 없음", "관심이 없음", "보통", "관심이 있음", "매우 관심이 있음"],
]


class OrdinalLikertEncoder:
    """
    한국어 표준 5점 리커트(Ordinal) 척도 자동 인식 및 순서 보존 인코더.
    원-핫 인코딩 시 발생하는 서열성(Rank/Order) 상실을 방지하고 문항 간 순위 상관관계를 보존합니다.
    """

    @staticmethod
    def detect_likert_columns(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        데이터프레임의 각 컬럼 값을 분석하여 5점 리커트 척도 컬럼을 자동 감지합니다.
        """
        likert_maps: Dict[str, Dict[str, Any]] = {}

        for col in df.columns:
            if df[col].dtype != "object":
                continue

            unique_vals = set(df[col].dropna().unique())
            # '미응답' 제외 후 순수 척도 값만 비교
            scale_vals = {v for v in unique_vals if v != "미응답"}
            if len(scale_vals) < 3:
                continue

            best_match: Optional[List[str]] = None
            max_overlap = 0

            for candidate in STANDARD_LIKERT_SCALES:
                cand_set = set(candidate)
                overlap = len(scale_vals & cand_set)
                if overlap >= 3 and overlap > max_overlap:
                    max_overlap = overlap
                    best_match = candidate

            if best_match and (max_overlap / len(scale_vals)) >= 0.7:
                val_to_rank = {val: (idx + 1) for idx, val in enumerate(best_match)}
                rank_to_val = {(idx + 1): val for idx, val in enumerate(best_match)}
                likert_maps[col] = {
                    "scale_type": f"{best_match[0]} ~ {best_match[-1]}",
                    "scale_values": best_match,
                    "val_to_rank": val_to_rank,
                    "rank_to_val": rank_to_val,
                    "has_unanswered": "미응답" in unique_vals,
                }

        return likert_maps

    @staticmethod
    def encode(df: pd.DataFrame, likert_maps: Dict[str, Dict[str, Any]]) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """
        리커트 척도 컬럼을 1~5 수치형 랭크로 변환하고, '미응답' 마스크를 보존합니다.
        """
        encoded_df = df.copy()
        unanswered_masks: Dict[str, pd.Series] = {}

        for col, meta in likert_maps.items():
            if col not in encoded_df.columns:
                continue

            s = encoded_df[col].astype(str)
            unanswered_masks[col] = s == "미응답"
            val_to_rank = meta["val_to_rank"]
            # 랭크 매핑 (미응답/알 수 없는 값은 3(보통) 또는 NaN 처리)
            encoded_df[col] = s.map(val_to_rank).fillna(3).astype(float)

        return encoded_df, unanswered_masks

    @staticmethod
    def decode(df: pd.DataFrame, likert_maps: Dict[str, Dict[str, Any]], unanswered_masks: Optional[Dict[str, pd.Series]] = None) -> pd.DataFrame:
        """
        수치형 랭크 값을 가장 가까운 리커트 척도 텍스트 범주로 복원합니다.
        """
        decoded_df = df.copy()

        for col, meta in likert_maps.items():
            if col not in decoded_df.columns:
                continue

            series = decoded_df[col]
            if pd.api.types.is_numeric_dtype(series):
                # 1~5 사이로 클리핑 후 반올림
                clipped = series.clip(1, len(meta["scale_values"])).round().astype(int)
                rank_to_val = meta["rank_to_val"]
                decoded_df[col] = clipped.map(rank_to_val).fillna(meta["scale_values"][2])

            if unanswered_masks and col in unanswered_masks:
                mask = unanswered_masks[col]
                decoded_df.loc[mask, col] = "미응답"

        return decoded_df


class SurveyLogicEngine:
    """
    설문 조건부 분기(Skip-Logic) 규칙 자동 탐지, 사후 보정 및 논리 무결성 검증 엔진.
    """

    @staticmethod
    def auto_detect_skip_rules(df: pd.DataFrame, min_confidence: float = 0.98) -> List[Dict[str, Any]]:
        """
        데이터셋을 전수 스캔하여 IF [조건문항=값] THEN [대상문항=미응답] 형태의 결정론적 분기 규칙을 자동 탐지합니다.
        """
        detected_rules: List[Dict[str, Any]] = []
        cols = list(df.columns)

        # 1. 도메인 기반 규칙 탐색 (참여경험, 희망직업 등)
        for col_a in cols:
            # 예/아니오 형태의 참여/경험 문항 탐색
            vals_a = df[col_a].dropna().unique()
            if "아니오" in vals_a or "아니오(미참여)" in vals_a:
                no_val = "아니오" if "아니오" in vals_a else "아니오(미참여)"
                mask_no = df[col_a] == no_val
                support = int(mask_no.sum())

                if support >= 5:
                    # 다른 컬럼들의 '미응답' 비율 검사
                    for col_b in cols:
                        if col_a == col_b:
                            continue
                        sub_b = df.loc[mask_no, col_b]
                        unans_cnt = (sub_b == "미응답").sum()
                        conf = float(unans_cnt / support)

                        # 관련성 있는 문항명 (만족도, 인지, 반영, 이유 등)이거나 98% 이상 미응답인 경우
                        if conf >= min_confidence:
                            detected_rules.append({
                                "rule_id": f"RULE_{len(detected_rules)+1}",
                                "condition_col": col_a,
                                "condition_val": no_val,
                                "target_col": col_b,
                                "target_val": "미응답",
                                "confidence": round(conf, 4),
                                "support": support,
                                "description": f"IF [{col_a} == '{no_val}'] THEN [{col_b} = '미응답']",
                            })

        # 2. '희망 직업의 유무' == '아니오' 전용 분기 규칙 보장
        if "희망 직업의 유무" in cols:
            job_no = df["희망 직업의 유무"] == "아니오"
            if job_no.sum() >= 5:
                for target in ["희망 직업 업무내용 인지 정도", "희망 직업 선택 이유", "희망 직업 관련 체험 경험"]:
                    if target in cols:
                        already = any(r["condition_col"] == "희망 직업의 유무" and r["target_col"] == target for r in detected_rules)
                        if not already:
                            detected_rules.append({
                                "rule_id": f"RULE_{len(detected_rules)+1}",
                                "condition_col": "희망 직업의 유무",
                                "condition_val": "아니오",
                                "target_col": target,
                                "target_val": "미응답",
                                "confidence": 1.0,
                                "support": int(job_no.sum()),
                                "description": f"IF [희망 직업의 유무 == '아니오'] THEN [{target} = '미응답']",
                            })

        # 3. '참여경험_진로체험' == '아니오' -> '희망 진로체험 반영 수준' == '미응답' 보장
        if "참여경험_진로체험" in cols and "희망 진로체험 반영 수준" in cols:
            exp_no = df["참여경험_진로체험"] == "아니오"
            if exp_no.sum() >= 5:
                already = any(r["condition_col"] == "참여경험_진로체험" and r["target_col"] == "희망 진로체험 반영 수준" for r in detected_rules)
                if not already:
                    detected_rules.append({
                        "rule_id": f"RULE_{len(detected_rules)+1}",
                        "condition_col": "참여경험_진로체험",
                        "condition_val": "아니오",
                        "target_col": "희망 진로체험 반영 수준",
                        "target_val": "미응답",
                        "confidence": 1.0,
                        "support": int(exp_no.sum()),
                        "description": "IF [참여경험_진로체험 == '아니오'] THEN [희망 진로체험 반영 수준 = '미응답']",
                    })

        return detected_rules

    @staticmethod
    def apply_skip_rules(df: pd.DataFrame, rules: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        합성 데이터에 설문 분기 규칙을 적용하여 비논리적 모순값을 100% 자동 교정합니다.
        """
        rectified_df = df.copy()
        corrections: List[Dict[str, Any]] = []
        total_corrected_cells = 0

        for rule in rules:
            cond_col = rule["condition_col"]
            cond_val = rule["condition_val"]
            tgt_col = rule["target_col"]
            tgt_val = rule["target_val"]

            if cond_col not in rectified_df.columns or tgt_col not in rectified_df.columns:
                continue

            # 조건에 부합하지만 대상 컬럼이 target_val이 아닌 모순 행 탐색
            mask = (rectified_df[cond_col] == cond_val) & (rectified_df[tgt_col] != tgt_val)
            violation_count = int(mask.sum())

            if violation_count > 0:
                rectified_df.loc[mask, tgt_col] = tgt_val
                total_corrected_cells += violation_count
                corrections.append({
                    "rule_id": rule.get("rule_id", ""),
                    "description": rule.get("description", ""),
                    "corrected_count": violation_count,
                })

        report = {
            "total_rules_applied": len(rules),
            "total_corrected_cells": total_corrected_cells,
            "corrections_by_rule": corrections,
        }
        return rectified_df, report

    @staticmethod
    def validate_survey_logic(df: pd.DataFrame, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        데이터셋의 설문 분기 로직 준수율을 검증하여 논리 무결성(Logic Integrity) 점수를 반환합니다.
        """
        total_cases = 0
        violation_cases = 0
        rule_results = []

        for rule in rules:
            cond_col = rule["condition_col"]
            cond_val = rule["condition_val"]
            tgt_col = rule["target_col"]
            tgt_val = rule["target_val"]

            if cond_col not in df.columns or tgt_col not in df.columns:
                continue

            cond_mask = df[cond_col] == cond_val
            applicable_count = int(cond_mask.sum())

            if applicable_count > 0:
                violations = int(((df[cond_col] == cond_val) & (df[tgt_col] != tgt_val)).sum())
                total_cases += applicable_count
                violation_cases += violations
                rule_results.append({
                    "description": rule.get("description", f"{cond_col}={cond_val} -> {tgt_col}={tgt_val}"),
                    "applicable_rows": applicable_count,
                    "violations": violations,
                    "compliance_rate": round(1.0 - (violations / applicable_count), 4),
                })

        compliance_rate = max(0.0, 1.0 - (violation_cases / total_cases)) if total_cases else None

        return {
            "status": 'NOT_EVALUATED' if total_cases == 0 else 'PASS' if violation_cases == 0 else 'REVIEW',
            "integrity_score": round(compliance_rate * 100, 2) if compliance_rate is not None else None,
            "passed": violation_cases == 0 if total_cases else None,
            "total_checked_rules": len(rule_results),
            "total_applicable_rows": total_cases,
            "total_violations": violation_cases,
            "rule_details": rule_results,
        }
