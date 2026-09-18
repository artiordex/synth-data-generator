# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: sampler.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/statistical/sampler.py
# 목적: 통계 분포 기반의 빠른 합성 데이터를 생성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from ...common.types import ColumnPlan
from ..base import BaseSynthesizer
from ..registry import register_synthesizer

@register_synthesizer("statistical")
class StatisticalSampler(BaseSynthesizer):
    """컬럼별 통계 분포를 학습하고 데이터를 샘플링함"""
    # StatisticalSampler 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self):
        """
            @description StatisticalSampler 인스턴스 멤버 변수 및 초기 설정을 구성함
        """
        self.training = None
        self.plan = None

    # fit 작업을 수행함
    def fit(self, training: pd.DataFrame, plan: ColumnPlan, **kwargs: Any) -> None:
        """
            @description 입력 데이터로 합성 모델을 학습함
            @param {training} - 메서드 입력값임
            @param {plan} - 메서드 입력값임
            @param {kwargs} - 메서드 입력값임
            @returns {None} - 메서드 실행 결과를 반환함
        """
        self.training = training.copy()
        self.plan = plan

    # sample 작업을 수행함
    def sample(self, num_rows: int, conditions: dict[str, Any] | None = None) -> pd.DataFrame:
        """
            @description 학습된 합성 모델에서 데이터를 샘플링함
            @param {num_rows} - 메서드 입력값임
            @param {conditions} - 메서드 입력값임
            @returns {pd.DataFrame} - 메서드 실행 결과를 반환함
        """
        output = pd.DataFrame(index=range(num_rows))
        sub_training = self.training.copy()

        if conditions:
            for col, val in conditions.items():
                if col in sub_training.columns and val is not None and str(val).strip() != "":
                    filtered = sub_training[sub_training[col].astype(str) == str(val)]
                    if not filtered.empty:
                        sub_training = filtered

        for column in self.plan.categorical:
            if column not in sub_training.columns:
                continue
            distribution = sub_training[column].astype("string").value_counts(normalize=True, dropna=False)
            output[column] = np.random.choice(distribution.index.to_numpy(dtype=object), size=num_rows, p=distribution.values)

        for column in self.plan.numerical:
            if column not in sub_training.columns:
                continue
            series = pd.to_numeric(sub_training[column], errors="coerce").dropna()
            if series.empty:
                output[column] = np.nan
                continue
            output[column] = np.random.choice(series.values, size=num_rows, replace=True)

        if conditions:
            for col, val in conditions.items():
                if col in output.columns and val is not None and str(val).strip() != "":
                    output[col] = val

        return output
