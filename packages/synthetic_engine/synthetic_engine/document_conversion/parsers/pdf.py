# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: pdf.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/pdf.py
# 목적: PDF 문서를 분석하여 텍스트 및 구조 IR 트리로 파싱함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Read positioned PDF content without claiming semantic table reconstruction."""
from pathlib import Path
from ..core.enums import PageOrientation

from ..core.ir import (
    ConversionWarning, DocumentIR, DocumentMetadata, ImageIR, ParagraphIR,
    SectionIR, TextRunIR,
)
from ..core.source_ref import BoundingBoxIR, SourceRef


# PDF 문서를 분석하여 텍스트 및 이미지 요소를 DocumentIR 구조로 파싱함
def parse_pdf(source: str | Path, *, max_pages: int = 100) -> DocumentIR:
    import pymupdf as fitz

    source = Path(source)
    if max_pages < 1:
        raise ValueError('max_pages must be positive')
    document = DocumentIR(source_format='pdf', source_path=str(source))
    with fitz.open(source) as pdf:
        if not pdf.is_pdf or pdf.is_encrypted:
            raise ValueError('An unencrypted PDF is required')
        if len(pdf) > max_pages:
            raise ValueError(f'PDF exceeds {max_pages} pages')
        # Keep source bytes for structures not interpreted by this parser.
        document.resources.add(source.read_bytes(), 'application/pdf')
        meta = pdf.metadata or {}
        document.metadata = DocumentMetadata(
            title=meta.get('title'), author=meta.get('author'), subject=meta.get('subject'),
            created=meta.get('creationDate'), modified=meta.get('modDate'), custom=meta,
        )
        for page_no, page in enumerate(pdf, 1):
            section = SectionIR(page_width_pt=page.rect.width, page_height_pt=page.rect.height,
                                orientation=PageOrientation.LANDSCAPE if page.rect.width > page.rect.height else PageOrientation.PORTRAIT,
                                source_ref=SourceRef('pdf', page_no=page_no))
            document.sections.append(section)
            if page.rotation:
                document.warnings.append(ConversionWarning(
                    'PDF_ROTATION', 'Coordinates are unrotated PDF page coordinates.',
                    source_ref=section.source_ref,
                ))
            for block_no, block in enumerate(page.get_text('dict')['blocks']):
                ref = SourceRef('pdf', page_no=page_no, object_id=f'block:{block_no}')
                box = BoundingBoxIR(*block['bbox'], page_no)
                if block['type'] == 1:
                    section.elements.append(ImageIR(
                        image_bytes=block['image'], mime_type=f"image/{block['ext']}",
                        format=block['ext'], width_pt=box.width_pt, height_pt=box.height_pt,
                        original_width_px=block['width'], original_height_px=block['height'],
                        bbox=box, source_ref=ref,
                    ))
                    continue
                for line_no, line in enumerate(block.get('lines', [])):
                    paragraph = ParagraphIR(
                        source_ref=SourceRef('pdf', page_no=page_no,
                                             object_id=f'block:{block_no}/line:{line_no}'),
                        bbox=BoundingBoxIR(*line['bbox'], page_no),
                    )
                    for span_no, span in enumerate(line['spans']):
                        paragraph.inlines.append(TextRunIR(
                            text=span['text'], font_family_ko=span['font'], font_family_en=span['font'],
                            size_pt=span['size'], bold=bool(span['flags'] & 16),
                            italic=bool(span['flags'] & 2), color_hex=f"{span['color']:06X}",
                            bbox=BoundingBoxIR(*span['bbox'], page_no),
                            source_ref=SourceRef('pdf', page_no=page_no,
                                object_id=f'block:{block_no}/line:{line_no}/span:{span_no}'),
                        ))
                    section.elements.append(paragraph)
        document.warnings.append(ConversionWarning(
            'PDF_POSITIONED_CONTENT',
            'Lines are positioned text, not recovered semantic paragraphs. Tables, '
            'drawings, links, annotations and font programs remain in the source PDF resource; '
            'this parser does not reconstruct or render them.',
        ))
    document.intern_resources()
    return document


# IR 문서 섹션별 텍스트 런을 추출하여 페이지별 텍스트 리스트를 반환함
def page_texts(document: DocumentIR) -> list[str]:
    """Extract line-ordered text without stripping or normalizing characters."""
    return [''.join(''.join(run.text for run in block.inlines if isinstance(run, TextRunIR)) + '\n'
                    for block in section.elements if isinstance(block, ParagraphIR))
            for section in document.sections]
