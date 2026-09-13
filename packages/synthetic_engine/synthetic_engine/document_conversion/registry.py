# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: registry.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/registry.py
# 목적: 문서 포맷별 파서 및 렌더러 등록 레지스트리를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Lazy parser/renderer registry with content-based container identification."""
from importlib import import_module
import codecs
from pathlib import Path
from .exceptions import UnsupportedFeatureError, DocumentConversionError
from .parsers.package import DocumentPackage

PARSER_REGISTRY = {
    'hwp': ('hwp5_parser', 'Hwp5Parser'), 'hwpx': ('hwpx_parser', 'HwpxParser'),
    'docx': ('docx_parser', 'DocxParser'), 'html': ('html_parser', 'HtmlParser'),
    'md': ('markdown_parser', 'MarkdownParser'), 'xlsx': ('xlsx_parser', 'XlsxParser'),
    'pdf': ('pdf', None), 'image': ('image_parser', 'ImageParser'),
}
RENDERER_REGISTRY = {
    'html': ('html_renderer', 'HtmlRenderer'), 'docx': ('docx_renderer', 'DocxRenderer'),
    'hwpx': ('hwpx_renderer', 'HwpxRenderer'), 'pdf': ('pdf_renderer', 'PdfRenderer'),
    'md': ('markdown_renderer', 'MarkdownRenderer'), 'xlsx': ('xlsx_renderer', 'XlsxRenderer'),
}


# 이미지 signature 여부 및 유효성을 판별함
def _is_image_signature(signature: bytes) -> bool:
    if signature.startswith(b'\x89PNG\r\n\x1a\n'):
        return True
    if signature.startswith(b'\xff\xd8\xff'):
        return True
    if signature.startswith((b'II*\x00', b'MM\x00*')):
        return True
    if signature.startswith(b'BM'):
        return True
    if signature.startswith(b'RIFF') and len(signature) >= 12 and signature[8:12] == b'WEBP':
        return True
    if b'ftypheic' in signature[:32] or b'ftypmif1' in signature[:32]:
        return True
    return False


# 감지 format 작업을 수행함
def detect_format(path: Path) -> str:
    with path.open('rb') as stream:
        signature = stream.read(4096)
    if _is_image_signature(signature):
        return 'image'
    if signature.startswith(b'%PDF-'):
        return 'pdf'
    if signature.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        import olefile
        with olefile.OleFileIO(path) as document:
            if document.exists('FileHeader') and document.openstream('FileHeader').read(32).startswith(b'HWP Document File'):
                return 'hwp'
        raise UnsupportedFeatureError('OLE container is not HWP 5')
    if signature.startswith(b'PK'):
        with DocumentPackage(path) as archive:
            markers = [('Contents/header.xml', 'hwpx'), ('word/document.xml', 'docx'), ('xl/workbook.xml', 'xlsx')]
            matches = [fmt for marker, fmt in markers if marker in archive.names]
            if len(matches) != 1:
                raise DocumentConversionError('Ambiguous or unknown document package')
            return matches[0]
    suffix = path.suffix.lower()
    if suffix in {'.html', '.htm'} and b'<' in signature:
        return 'html'
    if suffix == '.md':
        decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')
        decoder.decode(signature, final=False)
        return 'md'
    raise UnsupportedFeatureError('Unrecognized document content')


# document 데이터를 분석하여 파싱함
def parse_document(path: Path):
    kind = detect_format(path)
    module, name = PARSER_REGISTRY[kind]
    implementation = import_module('.parsers.' + module, __package__)
    return implementation.parse_pdf(path) if name is None else getattr(implementation, name)().parse(path)


# renderer for 작업을 수행함
def renderer_for(kind: str):
    if kind not in RENDERER_REGISTRY:
        raise UnsupportedFeatureError(f'Unsupported IR output: {kind}')
    module, name = RENDERER_REGISTRY[kind]
    return getattr(import_module('.renderers.' + module, __package__), name)()
