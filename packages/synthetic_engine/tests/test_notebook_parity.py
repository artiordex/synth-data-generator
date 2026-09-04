import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import entropy

from synthetic_engine.common.types import ColumnPlan, SynthesisConfig
from synthetic_engine.common.randomness import seeded_pipeline
from synthetic_engine.generators.sampling import sample_valid_rows, SamplingExhaustedError
from synthetic_engine.preprocessing.transformer import apply_constraints_after_generation
from synthetic_engine.quality.jsd import numerical_jsd, binned_keys
from synthetic_engine.quality.assessment import compute_column_distributions
from synthetic_engine.pipeline import SyntheticPipeline


@pytest.mark.parametrize('raw,syn', [([1, None], [1, 1]), ([1, 2, None], [1, 2, 2]),
                                    ([None, None], [1, 2]), ([None], [None])])
def test_jsd_matches_notebook_null_bucket(raw, syn):
    a, b = pd.Series(raw, dtype=float), pd.Series(syn, dtype=float)
    both = pd.concat([a, b]).dropna()
    if both.nunique() <= 1:
        p, q = np.array([a.notna().sum(), a.isna().sum()]), np.array([b.notna().sum(), b.isna().sum()])
    else:
        edges = np.linspace(both.min(), both.max(), 21)
        p = np.append(np.histogram(a.dropna(), edges)[0], a.isna().sum())
        q = np.append(np.histogram(b.dropna(), edges)[0], b.isna().sum())
    p, q = p.astype(float) + 1e-12, q.astype(float) + 1e-12
    p, q = p / p.sum(), q / q.sum()
    midpoint = (p + q) / 2
    expected = (entropy(p, midpoint) + entropy(q, midpoint)) / 2
    assert numerical_jsd(a, b) == pytest.approx(expected, abs=1e-12)
    chart = compute_column_distributions(pd.DataFrame({'x': a}), pd.DataFrame({'x': b}),
                                        ColumnPlan([], ['x'], [], {}, {}), n_bins=20)[0]
    assert chart['jsd'] == pytest.approx(expected, abs=0.0001)
    na_bin = next(x for x in chart['bins'] if x['label'] == '결측치(NULL)')
    assert na_bin['original_count'] == a.isna().sum()
    json.dumps(chart, allow_nan=False)


def test_null_repair_preserves_applicability():
    constraints = [{'type': 'null_indicator', 'column': 'income', 'indicator_column': 'applies'}]
    frame = pd.DataFrame({'income': [None, 4, 5, 6], 'applies': ['적용', '비적용', '적용', None]})
    repaired = apply_constraints_after_generation(frame, constraints)
    assert list(repaired.index) == [1, 2]
    assert pd.isna(repaired.loc[1, 'income'])
    assert repaired.loc[2, 'applies'] == '적용'


def test_sparse_quantiles_use_notebook_rounding_fallback_with_null_bucket():
    reference = pd.DataFrame({'x': [0] * 199 + [10]})
    sample = pd.DataFrame({'x': [0, 10, None]})
    assert binned_keys(sample, [], ['x'], 20, reference).tolist() == ['0', '10', '__NA__']


class BatchGenerator:
    def __init__(self, batches):
        self.batches = iter(batches)

    def sample(self, num_rows, conditions=None):
        return next(self.batches).copy()


def test_refills_after_repair_and_duplicate_rejection():
    raw = pd.DataFrame({'value': [1, 2]})
    gen = BatchGenerator([pd.DataFrame({'value': [1, 3]}), pd.DataFrame({'value': [4, 5]})])
    result, sampling, guardrails, _ = sample_valid_rows(gen, raw, ColumnPlan([], ['value'], [], {}, {}),
        SynthesisConfig(sample_rows=3, sampling_batch_size=2, max_sampling_attempts=2), [])
    assert result['value'].tolist() == [3, 4, 5]
    assert sampling['attempts'] == 2
    assert guardrails['exact_duplicates_found'] == 1
    assert guardrails['final_exact_duplicates'] == 0


def test_no_success_when_all_samples_are_training_copies():
    raw = pd.DataFrame({'value': [1, 2]})
    gen = BatchGenerator([raw, raw])
    with pytest.raises(SamplingExhaustedError) as error:
        sample_valid_rows(gen, raw, ColumnPlan([], ['value'], [], {}, {}),
            SynthesisConfig(sample_rows=2, max_sampling_attempts=2), [])
    assert error.value.report['accepted_rows'] == 0
    assert error.value.report['attempts'] == 2


def test_duplicate_detection_ignores_numeric_display_and_null_sentinel():
    from synthetic_engine.privacy.guardrails import PrivacyGuardrails
    raw = pd.DataFrame({'value': pd.Series([1, None], dtype='Int64')})
    generated = pd.DataFrame({'value': [1.0, np.nan, 3.0]})
    filtered, report = PrivacyGuardrails.filter_exact_duplicates(raw, generated)
    assert filtered['value'].tolist() == [3.0]
    assert report['exact_duplicates_found'] == 2


def test_noise_cannot_break_final_range_or_null_rules(monkeypatch):
    def noisy(frame, *args, **kwargs):
        out = frame.copy()
        out['value'] = [-100, 200]
        return out, {'enabled': True, 'columns_perturbed': ['value']}
    monkeypatch.setattr('synthetic_engine.generators.sampling.apply_differential_privacy_noise', noisy)
    frame = pd.DataFrame({'value': [3, 4], 'applies': ['비적용', '적용']})
    result, *_ = sample_valid_rows(BatchGenerator([frame]), pd.DataFrame({'value': [8], 'applies': ['적용']}),
        ColumnPlan(['applies'], ['value'], [], {}, {}), SynthesisConfig(sample_rows=2, dp_enabled=True),
        [{'type': 'null_indicator', 'column': 'value', 'indicator_column': 'applies'},
         {'type': 'range', 'column': 'value', 'min': 0, 'max': 10}])
    assert pd.isna(result.loc[0, 'value'])
    assert result.loc[1, 'value'] == 10


def test_pipeline_keeps_features_for_training_but_excludes_from_evaluation(tmp_path, monkeypatch):
    class Generator:
        def fit(self, training, plan):
            assert 'month_sin' in training and 'month_cos' in training
        def sample(self, num_rows, conditions=None):
            return pd.DataFrame({'value': np.random.uniform(10, 20, num_rows),
                                 'month_sin': np.zeros(num_rows), 'month_cos': np.ones(num_rows)})
    monkeypatch.setattr('synthetic_engine.pipeline.get_synthesizer', lambda *a, **k: Generator())
    raw = pd.DataFrame({'value': [1, 2, 3], 'month_sin': [0, .5, 1], 'month_cos': [1, .5, 0]})
    path = tmp_path / 'data.csv'
    raw.to_csv(path, index=False)
    config = SynthesisConfig(sample_rows=3, sampling_batch_size=3, seed=123)
    def run(job):
        return SyntheticPipeline(config).execute(input_path=path, output_dir=tmp_path / 'out',
            job_id=job, original_filename=path.name, categorical_columns=[], numerical_columns=list(raw.columns),
            evaluation_excluded_columns=['month_sin', 'month_cos'])
    first, second = run('first'), run('second')
    pd.testing.assert_frame_equal(first['synthetic_df'], second['synthetic_df'])
    assert set(first['report']['utility']['jsd_by_column']) == {'value'}
    report = json.loads(first['report_path'].read_text(encoding='utf-8'))
    assert report['config']['num_cols_train'] == list(raw.columns)
    assert report['config']['num_cols_eval'] == ['value']
    assert report['config']['seed'] == 123 and report['config']['pac'] == 1
    assert report['sampling']['final_rows'] == 3
    assert len(first['hwp_files']) == 3
    with pytest.raises(ValueError, match='최소 1개'):
        SyntheticPipeline(config).execute(input_path=path, output_dir=tmp_path, job_id='invalid',
            original_filename=path.name, evaluation_excluded_columns=list(raw.columns))


def test_real_ctgan_cpu_reproducibility_and_pac_batch_size():
    from synthetic_engine.generators.ml.ctgan import CTGANGenerator
    frame = pd.DataFrame({'group': ['a', 'b', 'c'] * 7, 'value': np.arange(21, dtype=float)})
    plan = ColumnPlan(['group'], ['value'], [], {}, {})
    class Job:
        config = SynthesisConfig(seed=71)
        @seeded_pipeline
        def run(self):
            gen = CTGANGenerator(epochs=1, batch_size=21, pac=3, enable_gpu=False)
            gen.fit(frame, plan)
            assert gen.batch_size % 2 == 0 and gen.batch_size % 3 == 0
            return gen.sample(12)
    pd.testing.assert_frame_equal(Job().run(), Job().run())
