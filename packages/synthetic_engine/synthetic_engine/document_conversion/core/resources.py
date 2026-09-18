# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: resources.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/core/resources.py
# 목적: 문서 포함 이미지, 폰트 등 바이너리 리소스를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Document-scoped, content-addressed storage for unchanged resource bytes."""

from dataclasses import dataclass
from hashlib import sha256
import re


_MIME_TYPE = re.compile(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+/[A-Za-z0-9!#$%&'*+.^_`|~-]+", re.ASCII)


@dataclass(frozen=True)
class ResourceMetadata:
    """Immutable snapshot; MIME labels are source claims, not format detection."""

    digest: str
    size_bytes: int
    mime_types: tuple[str, ...]


class ResourceStore:
    """Deduplicate immutable bytes by SHA-256 within one document.

    Different MIME labels for identical bytes are retained as sorted metadata.
    The generic label is omitted once a more specific label is known. No MIME
    label changes the stored bytes or authorizes execution of the resource.
    """

    # ResourceStore 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self) -> None:
        """
            @description ResourceStore 인스턴스 멤버 변수 및 초기 설정을 구성함
        """
        self._data: dict[str, bytes] = {}
        self._mime_types: dict[str, set[str]] = {}

    # add 작업을 수행함
    def add(self, data: bytes, mime_type: str = "application/octet-stream") -> str:
        """Intern bytes and return their digest, retaining conflicting MIME labels."""
        if not isinstance(data, bytes):
            raise TypeError("Resource data must be immutable bytes.")
        if not isinstance(mime_type, str) or _MIME_TYPE.fullmatch(mime_type) is None:
            raise ValueError("A MIME type must contain a type/subtype token pair.")
        digest = sha256(data).hexdigest()
        if digest in self._data and self._data[digest] != data:
            raise ValueError("SHA-256 collision: refusing to replace resource bytes.")
        self._data.setdefault(digest, data)
        labels = self._mime_types.setdefault(digest, set())
        labels.add(mime_type.lower())
        if len(labels) > 1:
            labels.discard("application/octet-stream")
        return digest

    # get 작업을 수행함
    def get(self, digest: str) -> bytes:
        """Return canonical bytes; unknown digests raise KeyError."""
        return self._data[digest]

    # intern 작업을 수행함
    def intern(self, data: bytes) -> bytes:
        """Return a shared immutable instance for ImageIR.image_bytes."""
        return self.get(self.add(data))

    # metadata 정보를 조회하여 반환함
    def get_metadata(self, digest: str) -> ResourceMetadata:
        """Return metadata without exposing mutable internal storage."""
        return ResourceMetadata(
            digest=digest,
            size_bytes=len(self._data[digest]),
            mime_types=tuple(sorted(self._mime_types[digest])),
        )

    # digests 작업을 수행함
    def digests(self) -> tuple[str, ...]:
        """Return stable resource identifiers in insertion order."""
        return tuple(self._data)

    # total bytes 작업을 수행함
    @property
    def total_bytes(self) -> int:
        """Count unique binary payload bytes, excluding metadata overhead."""
        return sum(map(len, self._data.values()))

    # 포함된 요소의 전체 개수를 반환함
    def __len__(self) -> int:
        """
            @description 저장된 요소의 개수를 반환함
            @returns {int} - 메서드 실행 결과를 반환함
        """
        return len(self._data)

    # contains 작업을 수행함
    def __contains__(self, digest: object) -> bool:
        """
            @description 지정한 요소의 포함 여부를 확인함
            @param {digest} - 메서드 입력값임
            @returns {bool} - 메서드 실행 결과를 반환함
        """
        return digest in self._data
