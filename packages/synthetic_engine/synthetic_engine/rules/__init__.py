# -*- coding: utf-8 -*-
from importlib import import_module

from .base import RuleType, ActionType, RuleViolation, DatasetRule, DatasetSchemaConfig
from .catalog import get_dataset_catalog, match_dataset_schema, resolve_column_name
from .profile_registry import ProfileRegistry, ProfileRegistryError, default_profile_registry

_LAZY_EXPORTS = {
    "DependencyDiscoveryEngine": (".discovery", "DependencyDiscoveryEngine"),
    "resolve_rule_dependencies_dag": (".discovery", "resolve_rule_dependencies_dag"),
    "DatasetRuleEngine": (".engine", "DatasetRuleEngine"),
    "sample_empirical_lags": (".lag_sampling", "sample_empirical_lags"),
    "RuleExecutionContext": (".operators", "RuleExecutionContext"),
    "execute_rule": (".operators", "execute_rule"),
}


def __getattr__(name):
    """Load transformer-dependent modules only after package initialization."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value

__all__ = [
    "RuleType",
    "ActionType",
    "RuleViolation",
    "DatasetRule",
    "DatasetSchemaConfig",
    "get_dataset_catalog",
    "match_dataset_schema",
    "resolve_column_name",
    "ProfileRegistry",
    "ProfileRegistryError",
    "default_profile_registry",
    "DependencyDiscoveryEngine",
    "resolve_rule_dependencies_dag",
    "sample_empirical_lags",
    "DatasetRuleEngine",
    "RuleExecutionContext",
    "execute_rule",
]
