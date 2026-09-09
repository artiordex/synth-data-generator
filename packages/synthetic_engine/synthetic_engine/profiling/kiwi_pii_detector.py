# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: kiwi_pii_detector.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/kiwi_pii_detector.py
# 목적: Kiwi C++ 고속 형태소 분석기 기반 한글 인명·지명·기관명 PII 정밀 탐지 엔진
# 작성자: 개발팀
# 작성일: 2026-09-09
# =============================================================================
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

_KIWI_INSTANCE = None


def get_kiwi():
    """Lazy singleton Kiwi morphological analyzer."""
    global _KIWI_INSTANCE
    if _KIWI_INSTANCE is None:
        try:
            from kiwipiepy import Kiwi
            _KIWI_INSTANCE = Kiwi()
        except Exception:
            _KIWI_INSTANCE = None
    return _KIWI_INSTANCE


# Korean common surname list to boost Korean person name detection precision
COMPOUND_SURNAMES = {"남궁", "황보", "제갈", "선우", "독고", "사공", "동방", "서문", "소봉"}
KOREAN_SURNAMES = {
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안",
    "송", "류", "전", "홍", "고", "문", "양", "손", "배", "백", "허", "유", "남", "심", "노", "하", "곽",
    "성", "차", "주", "우", "구", "신", "임", "라", "전", "민", "유", "진", "지", "엄", "채", "원", "천",
    "방", "공", "강", "현", "함", "변", "염", "양", "변", "여", "추", "노", "도", "소", "신", "석", "선",
    "설", "마", "길", "연", "표", "명", "기", "반", "왕", "금", "옥", "육", "인", "맹", "제", "탁", "국",
} | COMPOUND_SURNAMES

# Honorifics / titles commonly following person names
NAME_POSTFIXES = {
    "씨", "님", "군", "양", "선생", "선생님", "박사", "교수", "원장", "부장", "과장", "팀장", "대리", "사원", "주임",
    "의사", "약사", "간호사", "연구원", "수석", "책임", "선임", "주무관", "사무관", "서기관", "심사관", "조사관",
    "위원", "대표", "대표이사", "이사", "상무", "전무", "처장", "국장", "단장", "총장", "담당자", "환자", "수검자", "피험자",
}


# Suffixes that indicate organizations, institutions, banks, or corporations (NOT person names)
ORGANIZATION_SUFFIXES = (
    "은행", "뱅크", "카드", "증권", "보험", "생명", "화재", "캐피탈", "저축은행", "금고", "신협", "농협", "수협", "우체국",
    "병원", "의원", "약국", "보건소", "클리닉", "요양원", "센터", "처", "청", "재단", "연구소", "연구원",
    "협회", "학회", "조합", "연합회", "공사", "공단", "본부", "지사", "지점", "본점", "출장소", "영업점",
    "회사", "주식회사", "법인", "기업", "그룹", "대학교", "대학", "학교", "고등학교", "중학교", "초등학교",
)

# Common nouns in banking, administration, clinical research that must not be mistaken for person names
NON_PERSON_WORDS = {
    "이체", "출금", "입금", "송금", "결제", "승인", "정산", "환불", "청구", "납부", "조회", "잔액", "원금", "이자",
    "계좌", "통장", "예금", "적금", "대출", "금융", "수수료", "거래", "내역", "송부", "반환", "차감", "합계",
    "총액", "세액", "공제", "영수증", "전표", "세금", "환율", "현금", "수표", "어음", "외환", "신용", "한도",
    "자동이체", "즉시이체", "당타행", "타행", "당행", "안내", "확인", "검토", "평가", "분석", "조사", "연구",
    "관리", "운영", "지원", "사업", "과제", "업무", "작업", "사항", "내용", "항목", "구분", "유형", "분류",
    "상태", "단계", "일자", "기간", "시간", "금액", "수량", "비율", "단위", "비고", "첨부", "참조", "수신",
    "발신", "제출", "보고", "계획", "의견", "접수", "발급", "신청", "등록", "처리", "완료", "진행", "예정",
    "보류", "반려", "취소", "변경", "수정", "삭제", "추가", "조치", "조정", "조직", "조달", "규정", "지침",
    "기준", "표준", "서식", "서류", "문서", "공문", "보고서", "계획서", "신청서", "동의서", "계약서", "증명서",
    "통지서", "명세서", "결과서", "심의서", "이용자", "담당자", "관리자", "책임자", "작성자", "확인자", "승인자",
    "소유자", "운영자", "신청인", "수혜자", "수검자", "피험자", "환자", "우리", "당사", "귀사", "본인",
    "타인", "개인", "전체", "일부", "하나", "현재", "과거", "최근", "최종", "이상", "이하", "미만", "초과",
    "원문", "대체", "가명", "익명", "비식별", "식별", "합성", "더미", "변환", "변조", "원본", "사본",
}

NAME_PREFIX_WORDS = {
    "성명", "이름", "환자명", "환자", "수검자", "피험자", "작성자", "확인자", "승인자", "담당자", "수취인",
    "예금주", "주문자", "의뢰인", "대표자", "보호자", "검토자", "보고자", "조사자",
}


def detect_korean_named_entities(text: str) -> List[Dict[str, Any]]:
    """
    Kiwi 형태소 분석기를 통해 문장 속 한국인 성명(NNP), 병원/기관명, 행정구역 지명을 정밀 탐지합니다.
    정규식으로 탐지할 수 없는 문맥 속 실명(인명)을 품사 단위로 정확하게 분리합니다.
    """
    if not text or not str(text).strip():
        return []

    kiwi = get_kiwi()
    if kiwi is None:
        return []

    entities: List[Dict[str, Any]] = []

    try:
        tokens = kiwi.tokenize(text)
    except Exception:
        return []

    n = len(tokens)
    idx = 0

    while idx < n:
        tok = tokens[idx]
        word = tok.form
        tag = tok.tag
        start = tok.start
        end = tok.start + tok.len

        # 1. 기관/기업/은행명 우선 감지 (인명 오탐 방지: 예 "우리은행", "신한카드")
        if any(word.endswith(suffix) for suffix in ORGANIZATION_SUFFIXES) or any(k in word for k in ("은행", "뱅크", "카드", "증권", "보험")):
            if len(word) >= 2:
                entities.append({
                    "entity": word,
                    "type": "ORGANIZATION",
                    "start": start,
                    "end": end,
                    "confidence": 0.95,
                })
                idx += 1
                continue

        # 2. 금융/행정/일반 명사 블랙리스트 제외 (예: "이체", "출금", "송금", "결제" 등)
        if word in NON_PERSON_WORDS:
            idx += 1
            continue

        # 3. 인명(Person Name) 감지:
        is_name = False
        name_candidate = word

        has_postfix = (idx + 1 < n and tokens[idx + 1].form in NAME_POSTFIXES)
        prev_tok = tokens[idx - 1] if idx > 0 else None
        prev_prev_tok = tokens[idx - 2] if idx > 1 else None
        has_prefix = (
            (prev_tok and prev_tok.form in NAME_PREFIX_WORDS)
            or (prev_prev_tok and prev_prev_tok.form in NAME_PREFIX_WORDS and prev_tok and prev_tok.form in (":", "："))
        )

        # 2글자 외자 성명은 직책/호칭 또는 접두어가 있을 때만 인명으로 판정 (독립된 '이체', '송금' 등 차단)
        if len(word) == 2 and tag == "NNP":
            if (has_postfix or has_prefix) and (word[0] in KOREAN_SURNAMES):
                is_name = True
        elif 3 <= len(word) <= 4 and tag == "NNP":
            if word[0] in KOREAN_SURNAMES or (word[:2] in COMPOUND_SURNAMES):
                is_name = True
            elif has_postfix or has_prefix:
                is_name = True

        # 연속된 형태소 결합 검사 (예: "김" + "철수", "남궁" + "민수", "남궁" + "민" + "수")
        if (not is_name or (is_name and len(name_candidate) < 3)) and idx + 1 < n:
            starts_surname = (word in KOREAN_SURNAMES) or (len(word) >= 2 and word[:2] in COMPOUND_SURNAMES)
            if starts_surname and word not in NON_PERSON_WORDS:
                comb = word
                curr_end = end
                j = idx + 1
                while j < n and len(comb) < 4:
                    nxt = tokens[j]
                    if nxt.start == curr_end and nxt.tag in ("NNP", "NNG"):
                        if nxt.form in NON_PERSON_WORDS:
                            break
                        comb += nxt.form
                        curr_end = nxt.start + nxt.len
                        j += 1
                    else:
                        break
                if (2 <= len(comb) <= 4 and comb != word and comb not in NON_PERSON_WORDS
                        and not any(comb.endswith(s) for s in ORGANIZATION_SUFFIXES)):
                    if len(comb) >= 3 or has_postfix or has_prefix:
                        is_name = True
                        name_candidate = comb
                        end = curr_end
                        idx = j - 1

        if is_name:
            entities.append({
                "entity": name_candidate,
                "type": "PERSON_NAME",
                "start": start,
                "end": end,
                "confidence": 0.95,
            })
            idx += 1
            continue

        # 2. 의료기관/약국/기관명 감지 (예: "서울대병원", "종로약국", "식품의약품안전처")
        if any(word.endswith(suffix) for suffix in ("병원", "의원", "약국", "보건소", "센터", "처", "청", "재단", "연구소")):
            if len(word) >= 3:
                entities.append({
                    "entity": word,
                    "type": "ORGANIZATION",
                    "start": start,
                    "end": end,
                    "confidence": 0.90,
                })
                idx += 1
                continue

        # 3. 행정구역 지명 감지 (예: "서울특별시", "종로구", "역삼동")
        if any(word.endswith(suffix) for suffix in ("특별시", "광역시", "시", "군", "구", "읍", "면", "동", "리")):
            if len(word) >= 2 and tag in ("NNP", "NNG"):
                entities.append({
                    "entity": word,
                    "type": "LOCATION",
                    "start": start,
                    "end": end,
                    "confidence": 0.88,
                })
                idx += 1
                continue

        idx += 1

    return entities
