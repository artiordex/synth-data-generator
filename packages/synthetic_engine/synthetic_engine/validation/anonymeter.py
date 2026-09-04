"""Risk evaluation against a control set excluded before model fitting."""
from __future__ import annotations
import math
import warnings
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan


def unavailable(reason: str, status: str = 'NOT_EVALUATED') -> dict[str, Any]:
    report = {'evaluated_with_anonymeter': False, 'status': status, 'reason': reason, 'errors': {}}
    for name in ('singling_out', 'linkability', 'inference'):
        report[name] = {'risk': None, 'status': status, 'reason': reason}
        report[f'{name}_risk'] = None
    return report


class AnonymeterValidator:
    @staticmethod
    def evaluate_risks(original: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan,
                       n_attacks: int = 50, control: pd.DataFrame | None = None) -> dict[str, Any]:
        cols = [c for c in plan.categorical + plan.numerical if c in original and c in synthetic]
        if control is None or any(c not in control for c in cols):
            return unavailable('학습에서 제외한 독립 대조 데이터가 없습니다.')
        if len(cols) < 2 or min(len(original), len(synthetic), len(control)) < 10:
            return unavailable('평가에는 최소 2개 컬럼과 학습·합성·대조 데이터 각각 10행이 필요합니다.')
        try:
            from anonymeter.evaluators import SinglingOutEvaluator, LinkabilityEvaluator, InferenceEvaluator
        except Exception as exc:
            return unavailable(str(exc), 'ERROR')
        ori, syn, ctrl = [frame[cols].sample(n=min(len(frame), 600), random_state=42).reset_index(drop=True)
                          for frame in (original, synthetic, control)]
        attacks = min(n_attacks, len(ori), len(syn), len(ctrl))
        report = unavailable('')
        half = max(1, len(cols) // 2)
        factories = {
            'singling_out': lambda: SinglingOutEvaluator(ori=ori, syn=syn, control=ctrl, n_attacks=attacks),
            'linkability': lambda: LinkabilityEvaluator(ori=ori, syn=syn, control=ctrl,
                                                       aux_cols=(cols[:half], cols[half:]), n_attacks=attacks),
            'inference': lambda: InferenceEvaluator(ori=ori, syn=syn, control=ctrl,
                                                    aux_cols=cols[:-1], secret=cols[-1], n_attacks=attacks),
        }
        for name, factory in factories.items():
            try:
                evaluator = factory()
                with warnings.catch_warnings(record=True) as notices:
                    warnings.simplefilter('always')
                    evaluator.evaluate(**({'mode': 'univariate'} if name == 'singling_out' else {'n_jobs': 1}))
                    result = evaluator.risk()
                unreliable = [str(w.message) for w in notices if 'cannot be trusted' in str(w.message).lower()]
                if unreliable:
                    raise ValueError('; '.join(unreliable))
                value = float(result.value if hasattr(result, 'value') else result)
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('유효하지 않은 위험도 측정값')
                report[name] = {'risk': value, 'status': 'PASS' if value <= .05 else 'REVIEW'}
                report[f'{name}_risk'] = value
            except Exception as exc:
                report['errors'][name] = str(exc)
                report[name] = {'risk': None, 'status': 'ERROR', 'reason': str(exc)}
        report['evaluated_with_anonymeter'] = not bool(report['errors'])
        report['status'] = ('ERROR' if report['errors'] else
                            'PASS' if all(report[name]['status'] == 'PASS' for name in factories) else 'REVIEW')
        report['reason'] = '일부 평가 실패' if report['errors'] else ''
        report['sample_rows'] = {'training': len(ori), 'synthetic': len(syn), 'control': len(ctrl)}
        return report


evaluate_anonymeter = AnonymeterValidator.evaluate_risks
