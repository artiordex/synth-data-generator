# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_fidelity.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_fidelity.py
# 목적: RapidFuzz C++ 고속 문자열 유사도 기반 OCR 문자오차율(CER) 및 용어 사전 매핑 엔진
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz, distance


def calculate_ocr_cer(ground_truth: str, recognized_text: str) -> Dict[str, Any]:
    """
    RapidFuzz C++ 엔진을 사용하여 원본 정답(Ground Truth)과 OCR 인식 텍스트 간의
    문자 오차율(CER: Character Error Rate) 및 레벤슈타인 편집 거리를 정밀 계산합니다.
    """
    gt = ground_truth.strip()
    rec = recognized_text.strip()

    if not gt and not rec:
        return {"cer": 0.0, "accuracy_pct": 100.0, "distance": 0}
    if not gt:
        return {"cer": 1.0, "accuracy_pct": 0.0, "distance": len(rec)}

    # Levenshtein distance (insertions, deletions, substitutions)
    edit_dist = distance.Levenshtein.distance(gt, rec)
    cer = float(edit_dist) / float(len(gt))
    # Normalized similarity ratio: 0.0 to 100.0%
    similarity_ratio = fuzz.ratio(gt, rec)

    return {
        "cer": round(cer, 4),
        "accuracy_pct": round(similarity_ratio, 2),
        "edit_distance": int(edit_dist),
        "ground_truth_len": len(gt),
        "recognized_len": len(rec),
    }


def fuzzy_match_column_to_dictionary(
    candidate_col: str,
    standard_dict: List[str],
    threshold: float = 70.0,
) -> Optional[Tuple[str, float]]:
    """
    RapidFuzz 토큰 정렬 유사도(token_sort_ratio)를 기반으로
    업로드된 컬럼명을 식약처/행안부 표준 용어사전의 정규 용어와 0.001초 만에 자동 매핑합니다.
    """
    if not candidate_col or not standard_dict:
        return None

    best_match = None
    best_score = 0.0

    for term in standard_dict:
        score = fuzz.token_sort_ratio(candidate_col, term)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = term

    if best_match:
        return (best_match, round(best_score, 1))
    return None
