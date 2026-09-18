"""Exceptions raised when an export cannot produce the requested artifact."""
from __future__ import annotations


class DocumentExportError(RuntimeError):
    """The requested document format could not be generated."""


__all__ = ["DocumentExportError"]
