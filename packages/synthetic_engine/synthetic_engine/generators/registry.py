"""Synthesizer registration and lazy built-in loading."""
from __future__ import annotations

from importlib import import_module
from threading import Lock
from typing import Any, Callable, Type

from .base import BaseSynthesizer


_SYNTHESIZER_REGISTRY: dict[str, Type[BaseSynthesizer]] = {}
_BUILTINS_LOADED = False
_BUILTIN_LOAD_LOCK = Lock()
_BUILTIN_MODULES = (
    ".statistical.sampler",
    ".ml.copula",
    ".ml.ctgan",
    ".ml.tvae",
)
_BUILTIN_NAMES = frozenset({"statistical", "gaussian_copula", "ctgan", "tvae"})


def _ensure_builtin_synthesizers() -> None:
    """Load built-in generators once, on the first factory call."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    with _BUILTIN_LOAD_LOCK:
        if _BUILTINS_LOADED:
            return
        for module_name in _BUILTIN_MODULES:
            import_module(module_name, __package__)
        _BUILTINS_LOADED = True


def register_synthesizer(name: str) -> Callable[[Type[BaseSynthesizer]], Type[BaseSynthesizer]]:
    """Register a synthesizer subclass under a normalized name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("synthesizer name must be a non-empty string")
    normalized_name = name.strip().lower()

    def decorator(cls: Type[BaseSynthesizer]) -> Type[BaseSynthesizer]:
        if not isinstance(cls, type) or not issubclass(cls, BaseSynthesizer):
            raise TypeError("registered synthesizer must inherit BaseSynthesizer")
        _SYNTHESIZER_REGISTRY[normalized_name] = cls
        return cls

    return decorator


def get_synthesizer(name: str, **kwargs: Any) -> BaseSynthesizer:
    """Instantiate a registered synthesizer by name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("synthesizer name must be a non-empty string")
    _ensure_builtin_synthesizers()
    normalized_name = name.strip().lower()
    if normalized_name not in _SYNTHESIZER_REGISTRY:
        available = ", ".join(sorted(_SYNTHESIZER_REGISTRY))
        raise ValueError(f"Unknown synthesizer type '{name}'. Available: [{available}]")
    return _SYNTHESIZER_REGISTRY[normalized_name](**kwargs)


def list_synthesizers() -> list[str]:
    """Return registered and built-in synthesizer names without loading ML modules."""
    return sorted(set(_SYNTHESIZER_REGISTRY) | _BUILTIN_NAMES)


__all__ = ["register_synthesizer", "get_synthesizer", "list_synthesizers"]
