# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: notebook_presets.py
# 경로: packages/synthetic_engine/synthetic_engine/profiling/notebook_presets.py
# 목적: 데이터 분석 및 프로파일링용 주피터 노트북 프리셋을 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from .analyzer import infer_columns, scan_pii_columns
from ..rules.profile_registry import default_engine_settings

def _load_presets() -> list[tuple[str, list[str], list[str], int, int, int, list[str], list[str]]]:
    """YAML 레지스트리의 노트북 프리셋을 기존 튜플 API로 변환함."""
    presets = []
    for preset in default_engine_settings().get("notebook_presets", []):
        presets.append((
            str(preset["name"]),
            list(preset.get("required_categorical", [])),
            list(preset.get("required_numerical", [])),
            int(preset["epochs"]),
            int(preset["batch_size"]),
            int(preset["pac"]),
            list(preset.get("preserve_null_columns", [])),
            list(preset.get("evaluation_excluded_columns", [])),
        ))
    return presets


PRESETS = _load_presets()


# notebook 설정값 작업을 수행함
def notebook_settings(frame):
    """데이터 컬럼 구조에 맞는 노트북 기반 합성 설정을 반환함"""
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
