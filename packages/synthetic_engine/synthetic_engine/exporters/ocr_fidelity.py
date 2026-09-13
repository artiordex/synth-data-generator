# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ocr_fidelity.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/ocr_fidelity.py
# 목적: RapidFuzz C++ 고속 문자열 유사도 기반 OCR 문자오차율(CER) 및 용어 사전 매핑 엔진
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from rapidfuzz import fuzz, distance


PUBLIC_FORM_STANDARD_HEADERS: Tuple[str, ...] = (
    "성명", "이름", "생년월일", "주민등록번호", "외국인등록번호", "성별",
    "주소", "도로명주소", "우편번호", "전화번호", "휴대전화번호", "전자우편",
    "소속", "부서", "직위", "직급", "담당자", "대표자", "신청인", "수취인",
    "예금주", "기관명", "사업자등록번호", "법인등록번호", "접수번호", "문서번호",
    "신청일", "접수일", "작성일", "처리일", "유효기간", "사업명", "과제명",
    "신청내용", "처리내용", "검토의견", "비고", "서명", "날인", "계좌번호",
    "은행명", "금액", "수량", "단가", "합계", "총액", "연락처", "팩스번호",
    "홈페이지", "국적", "학력", "경력", "자격번호", "허가번호", "등록일",
    "처리상태", "공개여부", "개인정보 수집 동의", "담당부서", "사용목적",
)


@dataclass(frozen=True)
class FormKeyValue:
    key: str
    value: str
    row: int
    key_col: int
    value_col: int
    confidence: float


# compact form 텍스트 작업을 수행함
def _compact_form_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    compact = re.sub(r"[\s:：·ㆍ]+", "", normalized).strip()
    # Frequent single-glyph OCR confusions in compact public-form labels.
    compact = re.sub(r"잎$", "일", compact)
    return compact


# correct public form header 작업을 수행함
def correct_public_form_header(
    candidate: str,
    *,
    threshold: float = 72.0,
    standard_headers: Sequence[str] = PUBLIC_FORM_STANDARD_HEADERS,
) -> Optional[Tuple[str, float]]:
    """Correct a short Korean public-form label using a bounded domain lexicon."""
    compact = _compact_form_text(candidate)
    if not compact or len(compact) > 24:
        return None
    best_term: Optional[str] = None
    best_score = 0.0
    for term in standard_headers:
        score = float(fuzz.ratio(compact, _compact_form_text(term)))
        if score > best_score:
            best_term, best_score = term, score
    # One damaged Hangul syllable is a 50% score for a two-syllable header and
    # 66.7% for a three-syllable header. The bounded lexicon and key-cell usage
    # keep these short-label thresholds precise without weakening long labels.
    effective_threshold = threshold
    if len(compact) <= 2:
        effective_threshold = min(effective_threshold, 50.0)
    elif len(compact) == 3:
        effective_threshold = min(effective_threshold, 65.0)
    if best_term is None or best_score < effective_threshold:
        return None
    return best_term, round(best_score, 1)


# form value 데이터를 표준 형식으로 정규화함
def normalize_form_value(value: str, value_type: Optional[str] = None) -> str:
    """Normalize OCR punctuation for common form values without rewriting prose."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"[\u00a0\u2000-\u200b\u3000]+", " ", text)

    if re.fullmatch(r"(?:\[\s*[Vv✓✔]\s*\]|\(\s*[Vv✓✔]\s*\)|■)", text):
        return "■"
    if re.fullmatch(r"(?:\[\s*\]|□)", text):
        return "□"

    resident = re.fullmatch(r"\s*(\d{6})\s*[-–—]?\s*([1-4])\d{6}\s*", text)
    if resident:
        return f"{resident.group(1)}-*******"

    date_match = re.fullmatch(
        r"\s*(\d{4})\s*(?:년|[./-])\s*(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*(?:일)?\s*",
        text,
    )
    if date_match:
        year, month, day = (int(part) for part in date_match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    phone_candidate = re.sub(r"\s+", "", text)
    phone_match = re.fullmatch(r"(0\d{1,2})[-.)]?(\d{3,4})[-.]?(\d{4})", phone_candidate)
    if phone_match:
        return "-".join(phone_match.groups())

    if value_type in {"amount", "number", "currency"} or re.fullmatch(r"[\dOoIlSs,\.\s]+(?:원)?", text):
        suffix = "원" if text.endswith("원") else ""
        numeric = text[:-1] if suffix else text
        numeric = numeric.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5", "s": "5"}))
        digits = re.sub(r"\D", "", numeric)
        if digits:
            return f"{int(digits):,}{suffix}"

    if value_type == "code":
        return re.sub(r"\s+", "", text).translate(
            str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5"})
        ).upper()

    return re.sub(r"[ \t]+", " ", text)


# 셀 value 작업을 수행함
def _cell_value(cell: Any, key: str, default: Any = None) -> Any:
    if isinstance(cell, dict):
        return cell.get(key, default)
    return getattr(cell, key, default)


# bind form key value pairs 작업을 수행함
def bind_form_key_value_pairs(cells: Sequence[Any]) -> List[FormKeyValue]:
    """Bind a recognized label to the nearest value cell on the same row."""
    ordered = sorted(
        cells,
        key=lambda cell: (int(_cell_value(cell, "row", 0)), int(_cell_value(cell, "col", 0))),
    )
    pairs: List[FormKeyValue] = []
    for index, cell in enumerate(ordered):
        text = str(_cell_value(cell, "text", "") or "").strip()
        row = int(_cell_value(cell, "row", 0))
        col = int(_cell_value(cell, "col", 0))

        inline = re.match(r"^\s*([^:：]{1,24})\s*[:：]\s*(.+?)\s*$", text)
        if inline:
            match = correct_public_form_header(inline.group(1))
            if match:
                pairs.append(FormKeyValue(match[0], normalize_form_value(inline.group(2)), row, col, col, match[1] / 100.0))
                continue

        match = correct_public_form_header(text)
        if not match:
            continue
        candidates = [
            candidate for candidate in ordered[index + 1:]
            if int(_cell_value(candidate, "row", 0)) == row
            and int(_cell_value(candidate, "col", 0)) > col
            and str(_cell_value(candidate, "text", "") or "").strip()
        ]
        if candidates:
            value_cell = min(candidates, key=lambda item: int(_cell_value(item, "col", 0)))
        else:
            below = [
                candidate for candidate in ordered[index + 1:]
                if int(_cell_value(candidate, "col", 0)) == col
                and int(_cell_value(candidate, "row", 0)) > row
                and str(_cell_value(candidate, "text", "") or "").strip()
            ]
            if not below:
                continue
            value_cell = min(below, key=lambda item: int(_cell_value(item, "row", 0)))
        value_col = int(_cell_value(value_cell, "col", 0))
        pairs.append(FormKeyValue(
            key=match[0],
            value=normalize_form_value(str(_cell_value(value_cell, "text", ""))),
            row=row,
            key_col=col,
            value_col=value_col,
            confidence=match[1] / 100.0,
        ))
    return pairs


# 정답 텍스트와 인식 텍스트 간의 문자오차율(CER) 및 편집 거리를 정밀 계산함
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


# RapidFuzz 토큰 정렬 유사도를 기반으로 컬럼명을 표준 용어사전과 매핑함
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
