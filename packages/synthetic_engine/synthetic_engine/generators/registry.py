# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Callable, Type
from .base import BaseSynthesizer

_SYNTHESIZER_REGISTRY: dict[str, Type[BaseSynthesizer]] = {}

def register_synthesizer(name: str) -> Callable[[Type[BaseSynthesizer]], Type[BaseSynthesizer]]:
    """Decorator to register a synthesizer class in the global registry."""
    def decorator(cls: Type[BaseSynthesizer]) -> Type[BaseSynthesizer]:
        normalized_name = name.strip().lower()
        _SYNTHESIZER_REGISTRY[normalized_name] = cls
        return cls
    return decorator

def get_synthesizer(name: str, **kwargs: Any) -> BaseSynthesizer:
    """Factory function to retrieve and instantiate a registered synthesizer."""
    normalized_name = name.strip().lower()
    if normalized_name not in _SYNTHESIZER_REGISTRY:
        available = ", ".join(sorted(_SYNTHESIZER_REGISTRY.keys()))
        raise ValueError(f"Unknown synthesizer type '{name}'. Available: [{available}]")
    cls = _SYNTHESIZER_REGISTRY[normalized_name]
    return cls(**kwargs)

def list_synthesizers() -> list[str]:
    """Return a list of all registered synthesizer names."""
    return sorted(list(_SYNTHESIZER_REGISTRY.keys()))
