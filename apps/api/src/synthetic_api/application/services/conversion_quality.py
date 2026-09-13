# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: conversion_quality.py
# 경로: apps/api/src/synthetic_api/application/services/conversion_quality.py
# 목적: 문서 변환 결과 품질 평가 및 OCR 신뢰도 통계를 계산함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
"""Source-to-preview text coverage and OCR review metadata."""
from collections import Counter
from pathlib import Path
import logging
import re
import zipfile
import xml.etree.ElementTree as ET


# 신뢰도 점수 값을 0.0 ~ 1.0 범위로 유효성 검증 및 제한함
def _clamp_confidence(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 1:
        return None
    return score


# 원본 문서와 변환 텍스트 간의 문자 단위 커버리지 및 변환 품질을 평가함
def assess_parse_quality(source: Path, parsed_text: str, ocr_confidence: float | None = None) -> dict:
    warnings = []
    source_text = ''
    page_count = None
    unreadable_pages = []
    supported = True
    metric = 'non_whitespace_character_coverage'
    try:
        suffix = source.suffix.lower()
        if suffix == '.pdf':
            import pymupdf
            with pymupdf.open(source) as pdf:
                if pdf.needs_pass:
                    raise ValueError('Password-protected document')
                page_count = len(pdf)
                texts = []
                for index, page in enumerate(pdf):
                    text = page.get_text()
                    texts.append(text)
                    if not text.strip():
                        unreadable_pages.append(index + 1)
                source_text = '\n'.join(texts)
            if unreadable_pages:
                warnings.append('텍스트를 직접 읽을 수 없는 페이지가 있어 OCR 결과를 검토해야 합니다.')
        elif suffix in ('.docx', '.hwpx'):
            with zipfile.ZipFile(source) as archive:
                names = [n for n in archive.namelist() if
                         (n.startswith('word/') and re.search(r'(document|header\d+|footer\d+|footnotes|endnotes)\.xml$', n)) or
                         re.fullmatch(r'Contents/section\d+\.xml', n)]
                if sum(archive.getinfo(n).file_size for n in names) > 64 * 1024 * 1024:
                    raise ValueError('Document XML exceeds inspection limit')
                source_text = '\n'.join(''.join(e.itertext()) for n in names
                                        for e in ET.fromstring(archive.read(n)).iter()
                                        if e.tag.rsplit('}', 1)[-1] == 't')
        elif suffix in ('.md', '.txt'):
            source_text = source.read_text(encoding='utf-8-sig', errors='strict')
        elif suffix in ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp', '.heic'):
            supported = True
            metric = 'ocr_confidence_weighted_coverage'
        else:
            supported = False
            warnings.append('이 형식은 원본 대비 텍스트 보존율을 자동 측정하지 않았습니다.')
    except Exception as exc:
        logging.warning('Source coverage inspection failed for %s: %s', source.suffix, exc)
        warnings.append('원본 비교 검사에 실패했습니다. 결과를 직접 검토해야 합니다.')
        supported = False

    if metric == 'ocr_confidence_weighted_coverage':
        coverage = _clamp_confidence(ocr_confidence) if ocr_confidence is not None else None
        if coverage is None and parsed_text.strip():
            warnings.append('OCR 신뢰도 측정값이 없어 결과를 자동 승인할 수 없습니다.')
        if coverage is not None and coverage < 0.85:
            warnings.append('OCR 텍스트 인식 신뢰도가 85% 미만입니다. 결과를 직접 검토해야 합니다.')
    else:
        # Count occurrences, so repeating one recovered word cannot conceal other missing characters.
        expected = Counter(c for c in source_text if not c.isspace())
        actual = Counter(c for c in parsed_text if not c.isspace())
        coverage = sum((expected & actual).values()) / expected.total() if expected and supported else None
        if coverage is not None and coverage < 0.95:
            warnings.append('원본 대비 텍스트 추출 보존율이 95% 미만입니다.')
    requires_review = bool(warnings) or bool(unreadable_pages) or (coverage is not None and coverage < 0.85)
    return {
        'text_coverage': round(coverage, 4) if coverage is not None else None,
        'metric': metric,
        'scope': 'source_to_preview',
        'layout_similarity': None,
        'layout_verified': False,
        'source_pages_count': page_count,
        'ocr_review_pages': unreadable_pages,
        'requires_review': requires_review,
        'warnings': warnings,
    }


# OCR 엔진 실행 결과의 페이지별 신뢰도 및 품질 요약을 생성함
def build_ocr_quality_summary(
    source: Path,
    *,
    html_preview: str,
    tables: list[dict],
    pages_count: int,
    base_quality: dict,
    ocr_confidence: float | None = None,
) -> dict:
    """Summarize OCR state from local parse outputs without invoking OCR again."""
    suffix = source.suffix.lower()
    review_pages = list(base_quality.get('ocr_review_pages') or [])
    warnings = list(base_quality.get('warnings') or [])
    low_confidence_regions = []
    confidence_scores = []

    valid_ocr_conf = _clamp_confidence(ocr_confidence)
    if valid_ocr_conf is not None:
        confidence_scores.append(valid_ocr_conf)

    for table in tables or []:
        table_conf = _clamp_confidence(table.get('confidence'))
        if table_conf is not None:
            confidence_scores.append(table_conf)
            if table_conf < 0.85:
                low_confidence_regions.append({
                    'type': 'table',
                    'page': None,
                    'label': f"표 {table.get('index', '?')}",
                    'confidence': round(table_conf, 4),
                    'reason': '표 병합 또는 좌표 충돌',
                })
        for cell in table.get('cells') or []:
            cell_conf = _clamp_confidence(cell.get('confidence'))
            if cell_conf is None:
                continue
            confidence_scores.append(cell_conf)
            if cell_conf < 0.85:
                low_confidence_regions.append({
                    'type': 'cell',
                    'page': None,
                    'label': f"표 {table.get('index', '?')} {cell.get('row', 0) + 1}행 {cell.get('col', 0) + 1}열",
                    'confidence': round(cell_conf, 4),
                    'reason': '셀 구조 신뢰도 낮음',
                })

    for match in re.finditer(r'신뢰도\s*([0-9]+(?:\.[0-9]+)?)%', html_preview or ''):
        score = _clamp_confidence(float(match.group(1)) / 100)
        if score is not None:
            confidence_scores.append(score)

    average_confidence = None
    if confidence_scores:
        average_confidence = round(sum(confidence_scores) / len(confidence_scores), 4)

    is_ocr_source = suffix in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp', '.heic'} or bool(review_pages)
    if is_ocr_source:
        status = 'review_required' if (
            average_confidence is None
            or average_confidence < 0.85
            or base_quality.get('requires_review')
            or low_confidence_regions
        ) else 'completed'
    else:
        status = 'not_required'

    if review_pages:
        for page in review_pages:
            low_confidence_regions.append({
                'type': 'page',
                'page': page,
                'label': f'{page}페이지',
                'confidence': None,
                'reason': '원본 텍스트 레이어가 없어 OCR 검토 필요',
            })

    total_pages = max(1, int(pages_count or base_quality.get('source_pages_count') or 1))
    page_progress = []
    for page in range(1, total_pages + 1):
        needs_review = page in review_pages
        page_progress.append({
            'page': page,
            'stage': 'review' if needs_review else ('ocr' if is_ocr_source else 'parse'),
            'progress': 100,
            'status': 'review_required' if needs_review else 'completed',
            'message': 'OCR 결과 검토 필요' if needs_review else '페이지 분석 완료',
        })

    if low_confidence_regions and not any('신뢰도가 낮은 영역' in warning for warning in warnings):
        warnings.append('신뢰도가 낮은 영역이 있어 결과 검토가 필요합니다.')

    return {
        'ocr_status': status,
        'ocr_engine': 'local',
        'average_confidence': average_confidence,
        'low_confidence_regions': low_confidence_regions[:50],
        'page_progress': page_progress,
        'warnings': warnings,
        'requires_review': bool(status == 'review_required' or low_confidence_regions),
    }
