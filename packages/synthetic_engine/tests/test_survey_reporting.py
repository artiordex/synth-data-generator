import math

import pandas as pd
import pytest

from synthetic_engine.generators.survey.survey_fusion import SurveyFusionEngine
from synthetic_engine.generators.survey.survey_logic import SurveyLogicEngine


def test_no_applicable_rules_is_unmeasured():
    frame = pd.DataFrame({'answer': ['a', 'b']})
    for rules in ([], [{'condition_col': 'answer', 'condition_val': 'absent',
                       'target_col': 'answer', 'target_val': 'a'}]):
        report = SurveyLogicEngine.validate_survey_logic(frame, rules)
        assert report['passed'] is None
        assert report['integrity_score'] is None
        assert report['status'] == 'NOT_EVALUATED'


@pytest.mark.parametrize('jsd, expected', [(0.2, 0.8), (None, None), (math.nan, None)])
def test_quality_uses_measured_jsd_and_preserves_assessment(monkeypatch, jsd, expected):
    monkeypatch.setattr('synthetic_engine.generators.survey.survey_fusion.evaluate',
                        lambda *a, **k: {'utility': {'jsd_mean': jsd},
                                         'assessment': {'overall_status': 'REVIEW'}})
    frame = pd.DataFrame({'answer': ['a', 'b']})
    metrics = SurveyFusionEngine.evaluate_survey_synthesis(frame, frame)
    assert metrics['overall_quality'] == expected
    assert metrics['auto_assessment']['overall_status'] == 'REVIEW'
    assert metrics['logic_integrity']['passed'] is None


def test_missing_metrics_never_produce_pass_or_approval(tmp_path):
    frame = pd.DataFrame({'answer': ['a', 'b']})
    target = tmp_path / 'report.xlsx'
    SurveyFusionEngine.generate_excel_compliance_report({}, frame, frame, target)
    sheets = pd.read_excel(target, sheet_name=None)
    all_text = ' '.join(str(v) for sheet in sheets.values() for v in sheet.to_numpy().ravel())
    for text in ('A등급', '보호 완료', '기준 충족', '100% 무결성', 'PASS'):
        assert text not in all_text
    assert '미측정' in all_text
    assert '담당자 검토 및 승인 필요' in all_text


def test_rule_failure_and_actual_quality_are_visible(tmp_path):
    frame = pd.DataFrame({'answer': ['a', 'b']})
    target = tmp_path / 'report.xlsx'
    SurveyFusionEngine.generate_excel_compliance_report({
        'overall_quality': .42,
        'logic_integrity': {'passed': False, 'total_applicable_rows': 2,
                            'total_violations': 1, 'integrity_score': 50},
    }, frame, frame, target)
    summary = pd.read_excel(target, sheet_name=0).set_index('항목')['결과']
    assert summary['종합 품질 점수 (JSD/유사도)'] == '42.0%'
    assert '검토 필요' in summary['설문 분기(Skip-Logic) 무결성']
    assert 'PASS' not in summary['설문 분기(Skip-Logic) 무결성']
