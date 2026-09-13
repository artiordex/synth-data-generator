# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: pipeline.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/pipeline.py
# 목적: IR(중간 표현) 기반 문서 포맷 변환 및 손실 감사 파이프라인을 실행함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-10
# =============================================================================
"""IR-only conversion with explicit supported pairs and loss reports."""
from dataclasses import asdict
from copy import deepcopy
import json
import logging
from pathlib import Path
import tempfile
import uuid

from .registry import parse_document, renderer_for
from .core.ir import TableIR, ConversionWarning
from .geometry.table_geometry import validate_spans, repair_table_geometry, normalize_column_widths
from .exceptions import UnsupportedFeatureError
from .qa.qa_auditor import audit
from .qa.capability_audit import capability_warnings

logger = logging.getLogger(__name__)


# 블록 목록 보유 여부를 확인함
def _has_blocks(document) -> bool:
    """Return whether a document contains any logical body/header/footer block."""
    return any(True for _ in document.iter_blocks())


# 입력 문서를 대상 포맷으로 변환하고 품질 감사 리포트를 생성함
def convert_document(input_file: Path, output_format: str, *, output_dir: Path | None = None,
                     fidelity_profile: str = 'auto', strict: bool = False) -> Path:
    """
    @description 입력 문서를 파싱하여 IR 트리로 정규화한 후 타깃 렌더러로 변환 출력함
    @param input_file: 변환 대상 원본 문서 파일 경로임
    @param output_format: 출력 목표 포맷 확장자 문자열(hwpx, docx, xlsx, pdf, html, md 등)임
    @param output_dir: 결과물이 저장될 출력 디렉터리 경로임
    @param fidelity_profile: 시각/구조적 충실도 프로파일 모드임
    @param strict: 엄격 변환 모드 플래그임
    @return: 최종 생성된 타깃 문서 파일 경로를 반환함
    @throws ValueError: 알 수 없는 충실도 프로파일인 경우 발생함
    @throws UnsupportedFeatureError: 엄격 모드 미지원 또는 미지원 기능인 경우 발생함
    """
    input_file = Path(input_file)
    output_format = output_format.lower().lstrip('.')
    if fidelity_profile not in {'auto', 'text', 'structural', 'visual'}:
        raise ValueError('Unknown fidelity profile')
    renderer = renderer_for(output_format)
    document = parse_document(input_file)
    source_document = deepcopy(document)
    for section in document.sections:
        roots = list(section.elements)
        for area in (section.header, section.footer):
            if area:
                roots.extend(area.elements)
        available = (section.page_width_pt - section.margin_left_pt - section.margin_right_pt
                     if section.page_width_pt is not None else None)
        for block in roots:
            if isinstance(block, TableIR):
                before = block.total_width_pt
                repair_table_geometry(block)
                if available is not None:
                    normalize_column_widths(block, available)
                if before != block.total_width_pt:
                    document.warnings.append(ConversionWarning('TABLE_WIDTH_NORMALIZED',
                        'Table tracks were resolved or resized to the section content width.',
                        source_ref=block.source_ref, feature='table_width'))
    for block in document.iter_blocks():
        if isinstance(block, TableIR):
            validate_spans(block)
    document.intern_resources()
    document.warnings.extend(capability_warnings(document, renderer.capabilities))
    # Current renderers deliberately declare partial mapping. Strict requests
    # cannot silently receive an approximate document.
    if strict:
        raise UnsupportedFeatureError('Strict rendering is not available until style/resource round-trip QA is implemented')
    directory = Path(output_dir) if output_dir else input_file.parent
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / f'{input_file.stem}_{uuid.uuid4().hex[:8]}.{output_format}'
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        staged = Path(temporary) / final.name
        renderer.render(document, staged)
        if not staged.is_file() or staged.stat().st_size == 0:
            raise ValueError('Renderer produced an empty output document')
        report = {'source_format': document.source_format, 'target_format': output_format,
                  'fidelity_profile': 'structural' if output_format == 'md' else fidelity_profile,
                  'warnings': [asdict(w) for w in document.warnings],
                  'unsupported_features': sorted({'full fidelity verification'} | {
                      w.feature or w.code for w in document.warnings}),
                  'text_fidelity': None, 'structure_fidelity': None,
                  'visual_fidelity': None, 'resource_fidelity': None}
        target_document = parse_document(staged)
        if _has_blocks(source_document) and not _has_blocks(target_document):
            raise ValueError('Renderer produced no recoverable document content')
        report.update(audit(source_document, target_document))
        report['warnings'].extend(asdict(w) for w in target_document.warnings)
        report['warnings'].extend(report['qa_warnings'])
        report_file = staged.with_suffix('.conversion-report.json')
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        staged.replace(final)
        report_file.replace(final.with_suffix('.conversion-report.json'))
    logger.info('Document conversion audited', extra={'document_id': document.document_id,
                'source_format': document.source_format, 'target_format': output_format})
    return final
