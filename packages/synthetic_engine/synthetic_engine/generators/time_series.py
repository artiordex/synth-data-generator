"""Entity-aware panel/time-series bootstrap preserving order and observation gaps."""
from __future__ import annotations

import numpy as np
import pandas as pd


class PanelTimeSeriesSynthesizer:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def sample(self, frame: pd.DataFrame, *, entity_column: str, time_column: str,
               target_entities: int | None = None) -> pd.DataFrame:
        if entity_column not in frame or time_column not in frame:
            raise ValueError("개체키와 시간 컬럼을 확인하세요.")
        working = frame.copy()
        working[time_column] = pd.to_datetime(working[time_column], errors="coerce")
        working = working.dropna(subset=[entity_column, time_column]).sort_values([entity_column, time_column])
        groups = [(key, group.copy()) for key, group in working.groupby(entity_column, sort=False)]
        if not groups:
            raise ValueError("유효한 시계열 개체가 없습니다.")
        count = target_entities or len(groups)
        rng = np.random.default_rng(self.seed)
        output = []
        numeric = [c for c in working.select_dtypes(include="number").columns if c != entity_column]
        for index in range(count):
            _, group = groups[int(rng.integers(0, len(groups)))]
            group = group.copy().reset_index(drop=True)
            group[entity_column] = f"SYN-{index + 1:06d}"
            group[time_column] = group[time_column] + pd.to_timedelta(int(rng.integers(-365, 366)), unit="D")
            for column in numeric:
                std = float(working[column].std(skipna=True) or 0)
                if std:
                    group[column] = pd.to_numeric(group[column], errors="coerce") + rng.normal(0, std * .03, len(group))
            output.append(group)
        result = pd.concat(output, ignore_index=True)
        result[time_column] = result[time_column].dt.strftime("%Y-%m-%d %H:%M:%S")
        return result

