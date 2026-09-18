# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: hma.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/relational/hma.py
# 목적: Hierarchical Multi-table Algorithm 기반 관계형 합성을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations
from typing import Any
import pandas as pd
from ...common.types import TableRelationship

class HMARelationalSynthesizer:
    """Multi-table hierarchical relational synthesizer using SDV HMASynthesizer."""

    # HMARelationalSynthesizer 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, verbose: bool = False):
        """
            @description HMARelationalSynthesizer 인스턴스 멤버 변수 및 초기 설정을 구성함
            @param {verbose} - 메서드 입력값임
        """
        self.verbose = verbose
        self.synthesizer = None
        self.metadata = None
        self.table_names: list[str] = []

    # fit 작업을 수행함
    def fit(
        self,
        tables: dict[str, pd.DataFrame],
        relationships: list[TableRelationship],
        primary_keys: dict[str, str] | None = None,
        **kwargs: Any
    ) -> None:
        """
            @description 입력 데이터로 합성 모델을 학습함
            @param {tables} - 메서드 입력값임
            @param {relationships} - 메서드 입력값임
            @param {primary_keys} - 메서드 입력값임
            @param {kwargs} - 메서드 입력값임
            @returns {None} - 메서드 실행 결과를 반환함
        """
        from sdv.metadata import MultiTableMetadata
        from sdv.multi_table import HMASynthesizer

        self.metadata = MultiTableMetadata()
        self.table_names = list(tables.keys())
        pkeys = primary_keys or {}

        # 1. Detect metadata for each table
        for table_name, df in tables.items():
            self.metadata.detect_table_from_dataframe(
                table_name=table_name,
                data=df
            )
            # Set primary key if specified or inferred
            if table_name in pkeys:
                self.metadata.set_primary_key(table_name=table_name, column_name=pkeys[table_name])

        # 2. Add relationships
        for rel in relationships:
            if rel.parent_table in tables and rel.child_table in tables:
                parent_pk = rel.parent_key
                try:
                    self.metadata.set_primary_key(table_name=rel.parent_table, column_name=parent_pk)
                except Exception:
                    pass

                self.metadata.add_relationship(
                    parent_table_name=rel.parent_table,
                    child_table_name=rel.child_table,
                    parent_primary_key=rel.parent_key,
                    child_foreign_key=rel.child_key
                )

        self.synthesizer = HMASynthesizer(
            self.metadata,
            verbose=self.verbose
        )
        self.synthesizer.fit(tables)

    # sample 작업을 수행함
    def sample(self, scale: float = 1.0) -> dict[str, pd.DataFrame]:
        """
            @description 학습된 합성 모델에서 데이터를 샘플링함
            @param {scale} - 메서드 입력값임
            @returns {dict[str, pd.DataFrame]} - 메서드 실행 결과를 반환함
        """
        if self.synthesizer is None:
            raise RuntimeError("HMARelationalSynthesizer is not fitted.")
        return self.synthesizer.sample(scale=scale)
