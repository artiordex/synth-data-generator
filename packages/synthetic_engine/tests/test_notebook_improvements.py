import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

from synthetic_engine.common.types import ColumnPlan, SynthesisConfig
from synthetic_engine.pipeline import SyntheticPipeline
from synthetic_engine.profiling.notebook_presets import PRESETS, notebook_settings
from synthetic_engine.generators.sampling import sample_valid_rows, SamplingExhaustedError
from synthetic_engine.quality.assessment import evaluate, build_auto_assessment
from synthetic_engine.validation.anonymeter import evaluate_anonymeter


def test_known_schemas_get_notebook_options_but_unknown_data_does_not():
    for name, cats, nums, epochs, batch, pac, nulls, excluded in PRESETS:
        frame = pd.DataFrame({**{c: ['가', '나'] for c in cats}, **{c: [1., None] for c in nums}})
        preset = notebook_settings(frame)
        assert preset['name'] == name
        assert preset['options']['epochs'] == epochs
        assert preset['options']['batch_size'] == batch
        assert preset['options']['pac'] == pac
        assert preset['options']['preserve_null_columns'] == nulls
        assert preset['options']['evaluation_excluded_columns'] == excluded
    assert notebook_settings(pd.DataFrame({'소득분위': [1, None]}))['options'] == {}


def test_no_control_or_small_data_is_unmeasured_not_safe():
    frame = pd.DataFrame({'x': range(5), 'y': range(5)})
    plan = ColumnPlan([], list(frame), [], {}, {})
    for control in (None, frame):
        risk = evaluate_anonymeter(frame, frame, plan, control=control)
        assert risk['status'] == 'NOT_EVALUATED'
        assert risk['singling_out_risk'] is None
        assessment = build_auto_assessment(frame, frame, plan, 0, 1, {}, risk)
        assert assessment['overall_status'] == 'REVIEW' and assessment['score'] is None


def test_evaluator_failure_does_not_become_zero_risk(monkeypatch):
    import anonymeter.evaluators as evaluators
    class Failed:
        def __init__(self, **kwargs): pass
        def evaluate(self, **kwargs): raise RuntimeError('measurement failed')
    for name in ('SinglingOutEvaluator', 'LinkabilityEvaluator', 'InferenceEvaluator'):
        monkeypatch.setattr(evaluators, name, Failed)
    frame = pd.DataFrame({'x': range(20), 'y': range(20)})
    plan = ColumnPlan([], list(frame), [], {}, {})
    risk = evaluate_anonymeter(frame, frame, plan, control=frame + 20)
    assert risk['status'] == 'ERROR' and len(risk['errors']) == 3
    assert all(risk[f'{name}_risk'] is None for name in ('singling_out', 'linkability', 'inference'))
    assert not risk['evaluated_with_anonymeter']


def test_chart_and_report_use_same_jsd_including_nulls():
    rng = np.random.default_rng(42)
    raw, syn = pd.DataFrame({'x': rng.normal(size=100)}), pd.DataFrame({'x': rng.normal(.5, 1.2, 100)})
    raw.loc[:10, 'x'] = np.nan
    result = evaluate(raw, syn, ColumnPlan([], ['x'], [], {}, {}), run_anonymeter_eval=False)
    assert result['column_distributions'][0]['jsd'] == round(result['utility']['jsd_by_column']['x'], 4)
    assert len(result['column_distributions'][0]['bins']) == 21


def test_unreliable_zero_risk_is_not_a_pass(monkeypatch):
    import warnings
    import anonymeter.evaluators as evaluators
    class Unreliable:
        def __init__(self, **kwargs): pass
        def evaluate(self, **kwargs): pass
        def risk(self):
            warnings.warn('Analysis results cannot be trusted.')
            return SimpleNamespace(value=0.0)
    for name in ('SinglingOutEvaluator', 'LinkabilityEvaluator', 'InferenceEvaluator'):
        monkeypatch.setattr(evaluators, name, Unreliable)
    frame = pd.DataFrame({'x': range(20), 'y': range(20)})
    result = evaluate_anonymeter(frame, frame, ColumnPlan([], list(frame), [], {}, {}), control=frame + 20)
    assert result['status'] == 'ERROR' and result['singling_out_risk'] is None


def test_balanced_keeps_common_combinations_but_rejects_rare_matches():
    raw = pd.DataFrame({'c': ['a'] * 10 + ['b'] * 10 + ['rare']})
    generated = pd.DataFrame({'c': ['a', 'b', 'rare']})
    generator = SimpleNamespace(sample=lambda **kwargs: generated.copy())
    plan = ColumnPlan(['c'], [], [], {}, {})
    result, _, report, _ = sample_valid_rows(generator, raw, plan,
        SynthesisConfig(sample_rows=2, max_sampling_attempts=1), [])
    assert result['c'].tolist() == ['a', 'b']
    assert report['status'] == 'REVIEW' and report['final_exact_duplicates'] == 2
    assert report['exact_duplicates_found'] == 1
    with pytest.raises(SamplingExhaustedError):
        sample_valid_rows(generator, raw, plan,
            SynthesisConfig(sample_rows=2, max_sampling_attempts=1, duplicate_policy='strict'), [])


def test_control_records_are_excluded_before_training_and_missing_scores_survive_export(tmp_path, monkeypatch):
    captured = {}
    class Generator:
        def fit(self, training, plan): captured['training'] = training.copy()
        def sample(self, num_rows, **kwargs):
            return pd.DataFrame({'x': range(200, 200 + num_rows), 'y': range(400, 400 + num_rows)})
    def checked_evaluate(original, synthetic, plan, **kwargs):
        control = kwargs['control']
        assert len(original) == 80 and len(control) == 20
        assert set(captured['training']['x']).isdisjoint(control['x'])
        return evaluate(original, synthetic, plan, run_anonymeter_eval=False, **kwargs)
    monkeypatch.setattr('synthetic_engine.pipeline.get_synthesizer', lambda *a, **k: Generator())
    monkeypatch.setattr('synthetic_engine.pipeline.evaluate', checked_evaluate)
    path = tmp_path / 'input.csv'
    pd.DataFrame({'x': range(100), 'y': range(100, 200)}).to_csv(path, index=False)
    result = SyntheticPipeline(SynthesisConfig(sample_rows=3, sampling_batch_size=3)).execute(
        input_path=path, output_dir=tmp_path, job_id='holdout', original_filename=path.name)
    report = json.loads(result['report_path'].read_text(encoding='utf-8'))
    assert report['config']['holdout']['control_rows'] == 20
    assert report['reid_risk'] is None and report['auto_assessment']['score'] is None
    assert report['auto_assessment']['passed'] is False
    assert len(result['hwp_files']) == 3


def test_explicit_empty_settings_override_notebook_defaults(tmp_path, monkeypatch):
    _, cats, nums, *_ = PRESETS[1]
    frame = pd.DataFrame({**{c: ['a', 'b', 'c'] for c in cats}, **{c: [1, None, 3] for c in nums}})
    path = tmp_path / 'housing.csv'
    frame.to_csv(path, index=False)
    class StopAfterFit(Exception): pass
    class Generator:
        def fit(self, training, plan):
            assert '소득분위_적용' not in training
            assert training['소득분위'].isna().sum() == 0
            raise StopAfterFit()
    monkeypatch.setattr('synthetic_engine.pipeline.get_synthesizer', lambda *a, **k: Generator())
    with pytest.raises(StopAfterFit):
        SyntheticPipeline(SynthesisConfig()).execute(input_path=path, output_dir=tmp_path,
            job_id='override', original_filename=path.name, preserve_null_columns=[])


def test_auto_constraints_respect_explicit_column_selection(tmp_path, monkeypatch):
    _, cats, nums, *_ = PRESETS[1]
    frame = pd.DataFrame({**{c: ['a', 'b', 'c'] for c in cats}, **{c: [1, None, 3] for c in nums}})
    path = tmp_path / 'housing.csv'
    frame.to_csv(path, index=False)
    class StopAfterFit(Exception): pass
    class Generator:
        def fit(self, training, plan):
            assert list(training) == ['가족수']
            raise StopAfterFit()
    monkeypatch.setattr('synthetic_engine.pipeline.get_synthesizer', lambda *a, **k: Generator())
    with pytest.raises(StopAfterFit):
        SyntheticPipeline(SynthesisConfig()).execute(input_path=path, output_dir=tmp_path,
            job_id='selected', original_filename=path.name, selected_columns=['가족수'])
