# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: sampling.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/sampling.py
# 목적: 다변량 확률 분포 기반 합성 데이터 샘플링을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Generate enough valid records without keeping rejected records as a fallback."""
import pandas as pd
from collections import Counter

from ..preprocessing.transformer import apply_constraints_after_generation
from ..privacy.dp import apply_differential_privacy_noise
from ..privacy.guardrails import PrivacyGuardrails
from ..privacy.projection import project_domain_constraints
from .rule_based.engine import RuleEngine
from ..rules.base import DatasetSchemaConfig
from ..rules.engine import DatasetRuleEngine


class SamplingExhaustedError(ValueError):
    # SamplingExhaustedError 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, report):
        self.report = report
        super().__init__(f"유효한 합성 행을 충분히 생성하지 못했습니다: 목표 {report['target_rows']}행, "
                         f"확보 {report['accepted_rows']}행, {report['attempts']}회 시도. "
                         "제약조건·생성 모델·최대 시도 횟수를 확인하세요.")


# sample valid 행 목록 작업을 수행함
def sample_valid_rows(
    gen,
    training,
    plan,
    config,
    constraints,
    conditions=None,
    progress=None,
    schema: DatasetSchemaConfig | None = None,
):
    kept, attempts = [], []
    accepted = 0
    raw_unique_rejected = 0
    dp_reports = []
    columns = plan.categorical + plan.numerical
    # 행 keys 작업을 수행함
    def row_keys(frame):
        data = frame[columns].astype(object).where(frame[columns].notna(), None)
        return list(map(tuple, data.values))
    counts = Counter(row_keys(training))
    # Common combinations can be legitimate in small categorical domains.
    # Retain them only in the explicit balanced policy; rare matches stay excluded.
    policy = config.duplicate_policy
    blocked = {key for key, count in counts.items() if policy == 'strict' or count < 5}
    # Raw-unique records are always blocked, regardless of duplicate_policy.
    raw_unique_keys = {key for key, count in counts.items() if count == 1}
    effective_blocked = blocked.union(raw_unique_keys)
    for attempt in range(config.max_sampling_attempts):
        requested = max(config.sampling_batch_size, config.sample_rows - accepted)
        if progress:
            progress(72, f"유효 행 생성 {attempt + 1}/{config.max_sampling_attempts}회: {accepted}/{config.sample_rows}행")
        chunk = gen.sample(num_rows=requested, conditions=conditions).copy()
        generated = len(chunk)
        for col in plan.categorical:
            if col in chunk:
                chunk[col] = chunk[col].astype("string")
        for col in plan.numerical:
            if col in chunk:
                chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        chunk = RuleEngine.apply_rules(chunk, plan)
        # 1단계 산식 재계산 및 2단계 논리 보정 적용
        chunk = DatasetRuleEngine.postprocess(
            chunk,
            raw_df=training,
            schema=schema,
            filter_clones=False,
            random_state=(config.seed + attempt) % 2**32,
            as_of=getattr(config, "reference_date", None),
        )
        if config.dp_enabled:
            public_bounds = {
                column: spec
                for column, spec in (plan.rules or {}).items()
                if isinstance(spec, dict) and spec.get("min") is not None and spec.get("max") is not None
            }
            chunk, dp = apply_differential_privacy_noise(
                chunk, plan.numerical, epsilon=config.dp_epsilon, delta=config.dp_delta,
                seed=(config.seed + attempt) % 2**32,
                public_bounds=public_bounds,
            )
            dp_reports.append(dp)
            chunk = project_domain_constraints(chunk, plan)
        # Validate AFTER noise too, so the final output respects the same rules.
        chunk = apply_constraints_after_generation(chunk, constraints)
        chunk = DatasetRuleEngine.postprocess(
            chunk,
            raw_df=training,
            schema=schema,
            filter_clones=False,
            random_state=(config.seed + attempt + 1000) % 2**32,
            as_of=getattr(config, "reference_date", None),
        )
        for col, value in (conditions or {}).items():
            if value is not None and str(value).strip():
                if col not in chunk:
                    raise ValueError(f"조건 컬럼이 합성 결과에 없습니다: {col}")
                chunk = chunk.loc[chunk[col].astype(str) == str(value)]
        invalid = generated - len(chunk)
        keys = row_keys(chunk)
        # 원본 유일 레코드(count==1)는 정책과 상관없이 100% 무조건 차단
        rejected = sum(key in effective_blocked for key in keys)
        raw_unique_rejected += sum(key in raw_unique_keys for key in keys)
        chunk = chunk.loc[[key not in effective_blocked for key in keys]].copy()
        attempts.append({"attempt": attempt + 1, "requested_rows": requested,
                         "generated_rows": generated, "constraint_rejected_rows": invalid,
                         "duplicate_rejected_rows": rejected,
                         "accepted_rows": len(chunk)})
        kept.append(chunk)
        accepted += len(chunk)
        if accepted >= config.sample_rows:
            break
    sampling = {"target_rows": config.sample_rows, "accepted_rows": accepted,
                "attempts": len(attempts), "batches": attempts,
                "repair": {"not_applicable": "force_null", "applicable_but_null": "drop_and_resample"}}
    if accepted < config.sample_rows:
        raise SamplingExhaustedError(sampling)
    result = pd.concat(kept, ignore_index=True).head(config.sample_rows)
    # 최종 결과 대상 도메인 업무규칙 및 원본 일치 정밀 후처리
    result = DatasetRuleEngine.postprocess(
        result,
        raw_df=training,
        schema=schema,
        filter_clones=False,
        random_state=(config.seed + 2000) % 2**32,
        as_of=getattr(config, "reference_date", None),
    )
    final_keys = row_keys(result)
    final_blocked_mask = [key in effective_blocked for key in final_keys]
    if any(final_blocked_mask):
        result = result.loc[[not blocked_row for blocked_row in final_blocked_mask]].reset_index(drop=True)
        final_keys = row_keys(result)
    final_matches = sum(key in counts for key in final_keys)
    sampling["final_rows"] = len(result)
    rejected = sum(x["duplicate_rejected_rows"] for x in attempts)
    examined = sum(x["generated_rows"] - x["constraint_rejected_rows"] for x in attempts)
    guardrails = {"exact_duplicates_found": rejected, "exact_duplicate_rate": rejected / max(examined, 1),
                  "rows_before": examined, "rows_after": len(result),
                  "policy": policy, "common_combination_min_count": 5,
                  "raw_unique_keys_blocked": len(raw_unique_keys),
                  "raw_unique_duplicates_found": raw_unique_rejected,
                  "final_exact_duplicates": final_matches,
                  "final_exact_duplicate_rate": final_matches / max(len(result), 1),
                  "final_effective_blocked_removed": int(sum(final_blocked_mask)),
                  "status": "REVIEW" if final_matches else "PASS"}
    dp = {"enabled": config.dp_enabled, "batches": dp_reports,
          "epsilon": config.dp_epsilon, "delta": config.dp_delta,
          "columns_perturbed": sorted({c for r in dp_reports for c in r["columns_perturbed"]})}
    return result, sampling, guardrails, dp
