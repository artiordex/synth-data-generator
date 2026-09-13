# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: serialization.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/serialization.py
# 목적: IR 문서 객체와 JSON 간 직렬화 및 역직렬화를 처리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Versioned, write-only audit snapshots; no parser or renderer dependencies.

IDs and source paths are retained. Stable output requires stable input IDs.
Binary values reference a deduplicated base64 resource manifest. Snapshots are
not a reconstruction format and do not preserve shared Python object identity.
"""
from __future__ import annotations

import base64
from dataclasses import fields, is_dataclass
from enum import Enum
import json
from math import isfinite

from .ir import DocumentIR, ImageIR
from .resources import ResourceStore


# document to dict 작업을 수행함
def document_to_dict(document: DocumentIR) -> dict:
    """Return a detached JSON-compatible snapshot without mutating the IR.

    Iterative traversal imposes no nesting limit and reports cycles as ValueError.
    Existing resources, including unattached resources, are retained.
    """
    if not isinstance(document, DocumentIR):
        raise TypeError("A DocumentIR is required")
    resources = ResourceStore()
    for digest in document.resources.digests():
        for mime_type in document.resources.get_metadata(digest).mime_types:
            resources.add(document.resources.get(digest), mime_type)
    active: set[int] = set()

    root = {}
    # Exit frames retain only ancestors, so shared occurrences remain legal.
    stack = [(document, root, "document", False)]
    while stack:
        value, parent, key, leaving = stack.pop()
        if leaving:
            active.remove(id(value))
            continue
        if isinstance(value, Enum):
            stack.append((value.value, parent, key, False))
            continue
        if value is None or isinstance(value, (str, bool, int)):
            parent[key] = value
            continue
        if isinstance(value, float):
            if not isfinite(value):
                raise ValueError("Snapshot numbers must be finite")
            parent[key] = value
            continue
        if isinstance(value, bytes):
            parent[key] = {"$resource": resources.add(value)}
            continue
        identity = id(value)
        if identity in active:
            raise ValueError("Snapshot object graph contains a cycle")
        active.add(identity)
        stack.append((value, parent, key, True))
        if is_dataclass(value) and not isinstance(value, type):
            result = {"$type": type(value).__name__}
            children = [(item.name, getattr(value, item.name)) for item in fields(value)
                        if not (isinstance(value, DocumentIR) and item.name == "resources")]
            if isinstance(value, ImageIR):
                digest = resources.add(value.image_bytes, value.mime_type)
                children = [(name, digest if name == "resource_id" else child)
                            for name, child in children]
        elif isinstance(value, (list, tuple)):
            result = [None] * len(value)
            children = list(enumerate(value))
        elif isinstance(value, dict):
            if not all(isinstance(name, str) for name in value):
                raise TypeError("Snapshot dictionary keys must be strings")
            result = {}
            children = list(value.items())
        else:
            raise TypeError(f"Unsupported snapshot value: {type(value).__name__}")
        parent[key] = result
        stack.extend((child, result, name, False) for name, child in reversed(children))

    manifest = {}
    for digest in sorted(resources.digests()):
        metadata = resources.get_metadata(digest)
        manifest[digest] = {
            "size_bytes": metadata.size_bytes,
            "mime_types": list(metadata.mime_types),
            "encoding": "base64",
            "data": base64.b64encode(resources.get(digest)).decode("ascii"),
        }
    return {"schema_version": 1, "document": root["document"], "resources": manifest}


# document to json 작업을 수행함
def document_to_json(document: DocumentIR) -> str:
    """Emit strict JSON; the stdlib encoder's recursion limit still applies.

    For documents exceeding that runtime limit, use document_to_dict instead.
    """
    snapshot = document_to_dict(document)
    try:
        return json.dumps(snapshot, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":"))
    except RecursionError as exc:
        raise ValueError("Standard-library JSON encoder recursion limit exceeded; "
                         "use document_to_dict for this document") from exc
