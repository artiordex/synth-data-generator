# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/synthetic_engine/synthetic_engine/__init__.py
# 목적: 합성 엔진 지연 로딩 진입점 및 패키지 버전을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Public synthetic-engine exports loaded only when requested."""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as distribution_version
from typing import Any

try:
    __version__ = distribution_version("synthetic-engine")
except PackageNotFoundError:
    # Source checkouts are usable without an editable install.
    __version__ = "2.1.0"

_EXPORTS: dict[str, tuple[str, str]] = {
    "ColumnPlan": (".common.types", "ColumnPlan"),
    "SynthesisConfig": (".common.types", "SynthesisConfig"),
    "TableRelationship": (".common.types", "TableRelationship"),
    "calculate_sha256": (".common.provenance", "calculate_sha256"),
    "detect_system_device": (".common.provenance", "detect_system_device"),
    "read_table": (".profiling.analyzer", "read_table"),
    "infer_columns": (".profiling.analyzer", "infer_columns"),
    "scan_pii_columns": (".profiling.analyzer", "scan_pii_columns"),
    "build_column_plan": (".profiling.analyzer", "build_column_plan"),
    "classify_information_type": (".profiling.analyzer", "classify_information_type"),
    "normalize_information_type": (".profiling.analyzer", "normalize_information_type"),
    "apply_constraints_before_training": (".preprocessing.transformer", "apply_constraints_before_training"),
    "prepare_training_frame": (".preprocessing.transformer", "prepare_training_frame"),
    "apply_constraints_after_generation": (".preprocessing.transformer", "apply_constraints_after_generation"),
    "infer_temporal_constraints": (".preprocessing.transformer", "infer_temporal_constraints"),
    "StatisticalSampler": (".generators.statistical.sampler", "StatisticalSampler"),
    "RuleEngine": (".generators.rule_based.engine", "RuleEngine"),
    "CTGANGenerator": (".generators.ml.ctgan", "CTGANGenerator"),
    "TVAEGenerator": (".generators.ml.tvae", "TVAEGenerator"),
    "GaussianCopulaGenerator": (".generators.ml.copula", "GaussianCopulaGenerator"),
    "HMARelationalSynthesizer": (".generators.relational.hma", "HMARelationalSynthesizer"),
    "TurboRelationalSampler": (".generators.relational.relational_sampler", "TurboRelationalSampler"),
    "PanelTimeSeriesSynthesizer": (".generators.time_series", "PanelTimeSeriesSynthesizer"),
    "DifferentialPrivacyManager": (".privacy.dp", "DifferentialPrivacyManager"),
    "apply_differential_privacy_noise": (".privacy.dp", "apply_differential_privacy_noise"),
    "ContextAwareFaker": (".privacy.faker", "ContextAwareFaker"),
    "build_pii_output": (".privacy.faker", "build_pii_output"),
    "apply_pii": (".privacy.faker", "apply_pii"),
    "project_token": (".privacy.token_vault", "project_token"),
    "evaluate_klt": (".privacy.klt", "evaluate_klt"),
    "import_schema": (".common.schema_import", "import_schema"),
    "AnonymeterValidator": (".validation.anonymeter", "AnonymeterValidator"),
    "evaluate_anonymeter": (".validation.anonymeter", "evaluate_anonymeter"),
    "jsd": (".quality.jsd", "jsd"),
    "categorical_jsd": (".quality.jsd", "categorical_jsd"),
    "numerical_jsd": (".quality.jsd", "numerical_jsd"),
    "wasserstein_distance": (".quality.jsd", "wasserstein_distance"),
    "wasserstein_similarity": (".quality.jsd", "wasserstein_similarity"),
    "categorical_tvd": (".quality.jsd", "categorical_tvd"),
    "calculate_wasserstein_distance": (".quality.jsd", "calculate_wasserstein_distance"),
    "calculate_tvd": (".quality.jsd", "calculate_tvd"),
    "total_variation_distance": (".quality.jsd", "total_variation_distance"),
    "binned_keys": (".quality.jsd", "binned_keys"),
    "build_auto_assessment": (".quality.assessment", "build_auto_assessment"),
    "compute_distribution_metrics": (".quality.assessment", "compute_distribution_metrics"),
    "compute_composite_quality_score": (".quality.assessment", "compute_composite_quality_score"),
    "status_by_threshold": (".quality.assessment", "status_by_threshold"),
    "status_label": (".quality.assessment", "status_label"),
    "evaluate": (".quality.assessment", "evaluate"),
    "compute_column_distributions": (".quality.assessment", "compute_column_distributions"),
    "build_review_documents": (".exporters.review_documents", "build_review_documents"),
    "generate_filled_hwp": (".exporters.hwp_exporter", "generate_filled_hwp"),
    "export_pseudonymized_document": (".exporters.document_exporter", "export_pseudonymized_document"),
    "DocumentExportError": (".exporters.errors", "DocumentExportError"),
    "make_submission_package_dirs": (".exporters.package_exporter", "make_submission_package_dirs"),
    "safe_path_part": (".exporters.package_exporter", "safe_path_part"),
    "BaseSynthesizer": (".generators.base", "BaseSynthesizer"),
    "register_synthesizer": (".generators.registry", "register_synthesizer"),
    "get_synthesizer": (".generators.registry", "get_synthesizer"),
    "list_synthesizers": (".generators.registry", "list_synthesizers"),
    "PrivacyGuardrails": (".privacy.guardrails", "PrivacyGuardrails"),
    "escape_unique_clones": (".privacy.guardrails", "escape_unique_clones"),
    "evaluate_subspace_dcr": (".privacy.guardrails", "evaluate_subspace_dcr"),
    "project_domain_constraints": (".privacy.projection", "project_domain_constraints"),
    "sample_empirical_lags": (".rules.lag_sampling", "sample_empirical_lags"),
    "resolve_rule_dependencies_dag": (".rules.discovery", "resolve_rule_dependencies_dag"),
    "DatasetRuleEngine": (".rules.engine", "DatasetRuleEngine"),
    "CorrelationEvaluator": (".quality.correlation", "CorrelationEvaluator"),
    "cramers_v": (".quality.correlation", "cramers_v"),
    "DomainCatalog": (".common.catalog", "DomainCatalog"),
    "DummyDataGenerator": (".generators.rule_based.dummy_generator", "DummyDataGenerator"),
    "SurveyFusionEngine": (".generators.survey.survey_fusion", "SurveyFusionEngine"),
    "SurveyModuleMeta": (".generators.survey.survey_fusion", "SurveyModuleMeta"),
    "SurveyInspectionResult": (".generators.survey.survey_fusion", "SurveyInspectionResult"),
    "SyntheticPipeline": (".pipeline", "SyntheticPipeline"),
}

__all__ = list(_EXPORTS)


# getattr 작업을 수행함
def __getattr__(name: str) -> Any:
    """Preserve public imports without loading unrelated optional engines."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


# 디렉터리 작업을 수행함
def __dir__() -> list[str]:
    """Expose lazy public exports to introspection tools."""
    return sorted(set(globals()) | set(_EXPORTS))
