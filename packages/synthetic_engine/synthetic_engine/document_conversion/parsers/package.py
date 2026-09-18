# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: package.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/package.py
# 목적: ZIP 기반 패키지 문서 압축 및 내부 XML을 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Bounded ZIP/XML access shared by document package parsers."""
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
from lxml import etree
from ..exceptions import DocumentConversionError


class DocumentPackage:
    # DocumentPackage 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, path):
        """
            @description DocumentPackage 인스턴스 멤버 변수 및 초기 설정을 구성함
            @param {path} - 메서드 입력값임
        """
        self.archive = ZipFile(path)
        try:
            entries = self.archive.infolist()
            if len(entries) > 10000 or sum(e.file_size for e in entries) > 256 * 1024 ** 2:
                raise DocumentConversionError('Package exceeds entry or expanded-size limits')
            names = set()
            for entry in entries:
                name = entry.filename
                raw_name = entry.orig_filename
                parts = PurePosixPath(name).parts
                canonical = str(PurePosixPath(name))
                if (canonical in names or '\\' in raw_name or ':' in raw_name or raw_name.startswith('/')
                        or '..' in parts or canonical != name.rstrip('/') or not parts
                        or any(ord(c) < 32 for c in raw_name)):
                    raise DocumentConversionError('Unsafe or duplicate package path')
                names.add(canonical)
                if entry.flag_bits & 1 or entry.file_size > 64 * 1024 ** 2:
                    raise DocumentConversionError('Encrypted or oversized package entry')
                if entry.file_size / max(entry.compress_size, 1) > 1000:
                    raise DocumentConversionError('Package compression ratio exceeds limit')
            self.names = {entry.filename for entry in entries}
        except Exception:
            self.archive.close()
            raise

    # 컨텍스트 매니저 진입 처리를 수행함
    def __enter__(self):
        """
            @description 컨텍스트 매니저 진입 처리를 수행함
        """
        return self

    # 컨텍스트 매니저 종료 및 리소스 정리를 수행함
    def __exit__(self, *args):
        """
            @description 컨텍스트 매니저 종료 및 리소스 정리를 수행함
            @param {args} - 메서드 입력값임
        """
        self.archive.close()

    # read 작업을 수행함
    def read(self, name):
        """
            @description read 작업을 수행함
            @param {name} - 메서드 입력값임
        """
        if name not in self.names:
            raise DocumentConversionError('Package member is missing')
        return self.archive.read(name)

    # resolve 작업을 수행함
    def resolve(self, source, target):
        """Resolve an internal URI relative to a part, never to the filesystem."""
        uri = urlsplit(target)
        if uri.scheme or uri.netloc or uri.query or uri.fragment:
            raise DocumentConversionError('External or ambiguous package reference')
        path = unquote(uri.path)
        if not path or '\\' in path or ':' in path or any(ord(c) < 32 for c in path):
            raise DocumentConversionError('Unsafe package reference')
        parts = [] if path.startswith('/') else list(PurePosixPath(source).parent.parts)
        for part in path.split('/'):
            if part in {'', '.'}:
                continue
            if part == '..':
                if not parts:
                    raise DocumentConversionError('Package reference escapes root')
                parts.pop()
            else:
                parts.append(part)
        resolved = '/'.join(parts)
        if resolved not in self.names or resolved.endswith('/'):
            raise DocumentConversionError('Package reference is missing')
        return resolved

    # xml 작업을 수행함
    def xml(self, name):
        """
            @description xml 작업을 수행함
            @param {name} - 메서드 입력값임
        """
        data = self.read(name)
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
            raise DocumentConversionError('Document XML entities are not supported')
        root = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
        if root.getroottree().docinfo.doctype:
            raise DocumentConversionError('Document XML DTD is not supported')
        return root
