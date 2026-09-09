# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: registry.py
# 경로: packages/synthetic_engine/synthetic_engine/generators/registry.py
# 목적: 합성 생성기를 이름으로 등록하고 조회함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
from __future__ import annotations
from typing import Any, Callable, Type
from .base import BaseSynthesizer

_SYNTHESIZER_REGISTRY: dict[str, Type[BaseSynthesizer]] = {}

def register_synthesizer(name: str) -> Callable[[Type[BaseSynthesizer]], Type[BaseSynthesizer]]:
    """생성기 클래스를 전역 레지스트리에 등록하는 데코레이터를 반환함"""
    """Decorator to register a synthesizer class in the global registry."""
    def decorator(cls: Type[BaseSynthesizer]) -> Type[BaseSynthesizer]:
        normalized_name = name.strip().lower()
        _SYNTHESIZER_REGISTRY[normalized_name] = cls
        return cls
    return decorator

def get_synthesizer(name: str, **kwargs: Any) -> BaseSynthesizer:
    """이름에 해당하는 합성 생성기 인스턴스를 반환함"""
    """Factory function to retrieve and instantiate a registered synthesizer."""
    normalized_name = name.strip().lower()
    if normalized_name not in _SYNTHESIZER_REGISTRY:
        available = ", ".join(sorted(_SYNTHESIZER_REGISTRY.keys()))
        raise ValueError(f"Unknown synthesizer type '{name}'. Available: [{available}]")
    cls = _SYNTHESIZER_REGISTRY[normalized_name]
    return cls(**kwargs)

def list_synthesizers() -> list[str]:
    """등록된 합성 생성기 이름 목록을 반환함"""
    """Return a list of all registered synthesizer names."""
    return sorted(list(_SYNTHESIZER_REGISTRY.keys()))
