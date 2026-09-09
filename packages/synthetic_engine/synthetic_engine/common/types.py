# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: types.py
# 경로: packages/synthetic_engine/synthetic_engine/common/types.py
# 목적: 합성 파이프라인에서 사용하는 공통 데이터 구조를 정의함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ColumnPlan:
    """컬럼별 합성·가명화 처리 계획을 보관함"""
    categorical: list[str]
    numerical: list[str]
    ignored: list[str]
    pii: dict[str, dict[str, Any]]
    rules: dict[str, dict[str, Any]]

@dataclass
class SynthesisConfig:
    """합성 모델과 품질·개인정보 보호 옵션을 보관함"""
    model_type: str = "ctgan"
    sample_rows: int = 1000
    epochs: int = 30
    batch_size: int = 64
    pac: int = 1
    dp_enabled: bool = False
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5
    quality_threshold: float = 0.8
    seed: int = 42
    sampling_batch_size: int = 800
    max_sampling_attempts: int = 10
    enable_gpu: bool = False
    duplicate_policy: str = 'balanced'

    def __post_init__(self):
        """합성 설정값의 범위와 조합을 검증함"""
        if self.duplicate_policy not in {'balanced', 'strict'}:
            raise ValueError('duplicate_policy must be balanced or strict')
        for name in ("sample_rows", "epochs", "batch_size", "pac", "sampling_batch_size", "max_sampling_attempts"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        if not 0 <= self.seed < 2**32:
            raise ValueError("seed must be between 0 and 2**32 - 1")
        if not 0 <= self.quality_threshold <= 1:
            raise ValueError("quality_threshold must be between 0 and 1")

@dataclass
class TableRelationship:
    """부모 테이블과 자식 테이블의 키 관계를 보관함"""
    parent_table: str
    child_table: str
    parent_key: str
    child_key: str
