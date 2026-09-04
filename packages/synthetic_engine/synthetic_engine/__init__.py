# -*- coding: utf-8 -*-
from .common.types import ColumnPlan, SynthesisConfig, TableRelationship
from .common.provenance import calculate_sha256, detect_system_device
from .profiling.analyzer import read_table, infer_columns, scan_pii_columns, build_column_plan
from .preprocessing.transformer import (
    apply_constraints_before_training,
    prepare_training_frame,
    apply_constraints_after_generation
)
from .generators.statistical.sampler import StatisticalSampler
from .generators.rule_based.engine import RuleEngine
from .generators.ml.ctgan import CTGANGenerator
from .generators.ml.tvae import TVAEGenerator
from .generators.ml.copula import GaussianCopulaGenerator
from .generators.relational.hma import HMARelationalSynthesizer
from .generators.relational.relational_sampler import TurboRelationalSampler
from .privacy.dp import DifferentialPrivacyManager, apply_differential_privacy_noise
from .privacy.faker import ContextAwareFaker, build_pii_output, apply_pii
from .validation.anonymeter import AnonymeterValidator, evaluate_anonymeter
from .quality.jsd import jsd, categorical_jsd, numerical_jsd, binned_keys
from .quality.assessment import build_auto_assessment, status_by_threshold, status_label, evaluate, compute_column_distributions
from .exporters.review_documents import build_review_documents
from .exporters.hwp_exporter import generate_filled_hwp
from .exporters.package_exporter import make_submission_package_dirs, safe_path_part
from .generators.base import BaseSynthesizer
from .generators.registry import register_synthesizer, get_synthesizer, list_synthesizers
from .privacy.guardrails import PrivacyGuardrails
from .quality.correlation import CorrelationEvaluator, cramers_v
from .common.catalog import DomainCatalog
from .generators.rule_based.dummy_generator import DummyDataGenerator
from .pipeline import SyntheticPipeline

__version__ = "2.4.0"


