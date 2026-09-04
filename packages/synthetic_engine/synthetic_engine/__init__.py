# -*- coding: utf-8 -*-
from .common.types import ColumnPlan, SynthesisConfig
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
from .privacy.dp import DifferentialPrivacyManager, apply_differential_privacy_noise
from .privacy.faker import ContextAwareFaker, build_pii_output, apply_pii
from .validation.anonymeter import AnonymeterValidator, evaluate_anonymeter
from .quality.jsd import jsd, categorical_jsd, numerical_jsd, binned_keys
from .quality.assessment import build_auto_assessment, status_by_threshold, status_label, evaluate
from .exporters.hwp_exporter import build_review_documents, generate_filled_hwp
from .exporters.package_exporter import make_submission_package_dirs, safe_path_part
from .pipeline import SyntheticPipeline

__version__ = "2.1.0"
