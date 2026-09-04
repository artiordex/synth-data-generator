"""Explicit schemas from the bundled notebook; never infer meaning from file names."""
from .analyzer import infer_columns, scan_pii_columns

PRESETS = [
    ('보육교사 근무 제약', ['성별', '연령대', '학력', '근무지역', '담당 영유아와 상호작용에서의 어려움',
       '담당 영유아 부모와의 관계에서의 어려움', '보육프로그램 운영에서의 어려움', '행정_사무 등의 업무처리에서의 어려움',
       '보육교직원과 관계에서의 어려움', '원장과의 관계에서의 어려움'], [], 30, 64, 1, [], []),
    ('임대주택 당첨자', ['연령대', '성별', '주택소재지_자치구', '임대주택 유형', '일반_우선_특별', '주택면적', '당첨_예비'],
       ['가족수', '소득분위'], 50, 64, 1, ['소득분위'], []),
    ('면세점 회원·주기 변수', ['성별', '연령대', '가입연월'], ['장바구니 품목수', '가입후_경과월수', '가입월_sin', '가입월_cos'],
       50, 64, 1, [], ['가입월_sin', '가입월_cos']),
    ('면세점 회원', ['성별', '연령대', '가입연월'], ['장바구니 품목수', '가입후_경과월'], 50, 64, 1, [], []),
    ('개인 인터넷 이용행태', ['성별', '학력', '직업분류', '최근인터넷이용시기', '인터넷이용빈도', '월평균가구소득', '거주지'],
       ['가구원연령'], 10, 200, 10, [], []),
    ('국민임대 임대계약', ['연령대', '성별', '주택소재지(자치구)', '주거급여 수급여부', '국민임대 임대보증금액', '국민임대 월임대료'],
       ['가족수'], 100, 64, 1, [], []),
]


def notebook_settings(frame):
    matches = [p for p in PRESETS if set(p[1] + p[2]).issubset(frame.columns)]
    if not matches:
        return {'name': None, 'options': {}}
    name, cats, nums, epochs, batch, pac, nulls, excluded = max(matches, key=lambda p: len(p[1]) + len(p[2]))
    pii = scan_pii_columns(frame)
    inferred_cats, inferred_nums = infer_columns(frame, list(pii))
    # Extra columns remain available; only known schema fields override inference.
    known = set(cats + nums)
    return {'name': name, 'options': {
        'categorical_columns': [c for c in cats if c not in pii] + [c for c in inferred_cats if c not in known],
        'numerical_columns': [c for c in nums if c not in pii] + [c for c in inferred_nums if c not in known],
        'preserve_null_columns': nulls, 'evaluation_excluded_columns': excluded,
        'epochs': epochs, 'batch_size': batch, 'pac': pac,
    }}
