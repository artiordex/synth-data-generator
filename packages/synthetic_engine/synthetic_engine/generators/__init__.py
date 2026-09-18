# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: __init__.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/__init__.py
# 목적: 합성 데이터 생성기 인터페이스 및 팩토리를 노출함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from importlib import import_module

from .base import BaseSynthesizer
from .registry import register_synthesizer, get_synthesizer, list_synthesizers

_LAZY_EXPORTS = {
    "StatisticalSampler": (".statistical.sampler", "StatisticalSampler"),
    "RuleEngine": (".rule_based.engine", "RuleEngine"),
    "GaussianCopulaGenerator": (".ml.copula", "GaussianCopulaGenerator"),
    "CTGANGenerator": (".ml.ctgan", "CTGANGenerator"),
    "TVAEGenerator": (".ml.tvae", "TVAEGenerator"),
    "HMARelationalSynthesizer": (".relational.hma", "HMARelationalSynthesizer"),
    "TurboRelationalSampler": (".relational.relational_sampler", "TurboRelationalSampler"),
}

__all__ = [
    "BaseSynthesizer",
    "register_synthesizer",
    "get_synthesizer",
    "list_synthesizers",
    "StatisticalSampler",
    "RuleEngine",
    "GaussianCopulaGenerator",
    "CTGANGenerator",
    "TVAEGenerator",
    "HMARelationalSynthesizer",
    "TurboRelationalSampler",
]


def __getattr__(name: str):
    """Load a concrete generator only when it is explicitly requested."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))

