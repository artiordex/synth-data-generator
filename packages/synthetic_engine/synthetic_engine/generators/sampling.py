"""Generate enough valid records without keeping rejected records as a fallback."""
import pandas as pd
from collections import Counter

from ..preprocessing.transformer import apply_constraints_after_generation
from ..privacy.dp import apply_differential_privacy_noise
from ..privacy.guardrails import PrivacyGuardrails
from .rule_based.engine import RuleEngine


class SamplingExhaustedError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(f"유효한 합성 행을 충분히 생성하지 못했습니다: 목표 {report['target_rows']}행, "
                         f"확보 {report['accepted_rows']}행, {report['attempts']}회 시도. "
                         "제약조건·생성 모델·최대 시도 횟수를 확인하세요.")


def sample_valid_rows(gen, training, plan, config, constraints, conditions=None, progress=None):
    kept, attempts = [], []
    accepted = 0
    dp_reports = []
    columns = plan.categorical + plan.numerical
    def row_keys(frame):
        data = frame[columns].astype(object).where(frame[columns].notna(), None)
        return list(map(tuple, data.values))
    counts = Counter(row_keys(training))
    # Common combinations can be legitimate in small categorical domains.
    # Retain them only in the explicit balanced policy; rare matches stay excluded.
    policy = config.duplicate_policy
    blocked = {key for key, count in counts.items() if policy == 'strict' or count < 5}
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
        if config.dp_enabled:
            chunk, dp = apply_differential_privacy_noise(
                chunk, plan.numerical, epsilon=config.dp_epsilon, delta=config.dp_delta,
                seed=(config.seed + attempt) % 2**32)
            dp_reports.append(dp)
        # Validate AFTER noise too, so the final output respects the same rules.
        chunk = apply_constraints_after_generation(chunk, constraints)
        for col, value in (conditions or {}).items():
            if value is not None and str(value).strip():
                if col not in chunk:
                    raise ValueError(f"조건 컬럼이 합성 결과에 없습니다: {col}")
                chunk = chunk.loc[chunk[col].astype(str) == str(value)]
        invalid = generated - len(chunk)
        keys = row_keys(chunk)
        rejected = sum(key in blocked for key in keys)
        chunk = chunk.loc[[key not in blocked for key in keys]].copy()
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
    final_matches = sum(key in counts for key in row_keys(result))
    sampling["final_rows"] = len(result)
    rejected = sum(x["duplicate_rejected_rows"] for x in attempts)
    examined = sum(x["generated_rows"] - x["constraint_rejected_rows"] for x in attempts)
    guardrails = {"exact_duplicates_found": rejected, "exact_duplicate_rate": rejected / max(examined, 1),
                  "rows_before": examined, "rows_after": len(result),
                  "policy": policy, "common_combination_min_count": 5,
                  "final_exact_duplicates": final_matches,
                  "final_exact_duplicate_rate": final_matches / len(result),
                  "status": "REVIEW" if final_matches else "PASS"}
    dp = {"enabled": config.dp_enabled, "batches": dp_reports,
          "epsilon": config.dp_epsilon, "delta": config.dp_delta,
          "columns_perturbed": sorted({c for r in dp_reports for c in r["columns_perturbed"]})}
    return result, sampling, guardrails, dp
