# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: document_privacy.py
# 경로: apps/api/src/synthetic_api/routes/v1/document_privacy.py
# 목적: 비정형 문서 비식별화 및 개인정보 마스킹 API 엔드포인트를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import json
import re
import shutil
import uuid
import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from synthetic_api.core.config import settings
from synthetic_api.application.services.document_conversion_service import inspect_pdf_text
from synthetic_api.infrastructure.file_access import confined_file
from synthetic_engine.exporters.preserve_document import native_hancom, process_document, render_pages
from synthetic_engine.privacy.document_replacements import propose
from synthetic_engine.privacy.domain_whitelist import load_whitelist, normalize
from synthetic_engine.profiling.pseudonym_input import read_pseudonym_input

router = APIRouter(prefix='/document-privacy', tags=['document-privacy'])


class InspectRequest(BaseModel):
    file_name: str


class Replacement(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    replacement: str = Field(min_length=1, max_length=200)


class EditRequest(BaseModel):
    replacements: list[Replacement] = Field(default_factory=list, max_length=500)


class IgnoreRequest(BaseModel):
    word: str = Field(min_length=1, max_length=200)
    action: Literal['add', 'remove'] = 'add'


# 세션 폴더 내 저장된 제외 단어 목록을 파싱하여 반환함
def ignored_words(folder: Path) -> list[str]:
    directory = folder / 'ignored'
    if not directory.is_dir():
        return []
    values = []
    for path in directory.glob('*.json'):
        try:
            word = json.loads(path.read_text(encoding='utf-8')).get('word', '').strip()
            if word:
                values.append(word)
        except (OSError, ValueError, AttributeError):
            continue
    return sorted(set(values))


# 제외 단어를 반영한 현재 문서 내 개인정보 치환 후보 목록을 추출함
def candidate_state(folder: Path):
    ignored = ignored_words(folder)
    text = inspect_pdf_text(confined_file(folder / 'original.pdf', folder))
    return {'ignored': ignored, 'candidates': propose(text, ignored=ignored)}


# 비정형 문서 비식별화 임시 작업 디렉터리 경로를 반환함
def work_root():
    return settings.STORAGE_DIR / 'temp' / 'document-privacy'


# 유효한 식별자 검증을 거쳐 해당 작업 세션의 디렉터리 경로를 반환함
def session_path(identifier):
    if not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise HTTPException(404, '작업을 찾을 수 없습니다.')
    folder = work_root() / identifier
    confined_file(folder / 'manifest.json', work_root())
    return folder


# 시스템 전역 설정 기반 비식별화 제외 도메인 목록을 조회함
@router.get('/whitelist', summary='설정 기반 도메인 제외 목록 조회')
def domain_whitelist():
    return {'words': sorted(load_whitelist()), 'scope': 'configured', 'read_only': True}


# 세션 제외 목록을 적용하여 개인정보 치환 후보를 재검사함
@router.get('/{identifier}/candidates', summary='세션 제외 목록을 적용하여 재검사')
def rescan_document(identifier: str):
    return candidate_state(session_path(identifier))


# 해당 문서 세션의 제외 단어를 추가하거나 삭제함
@router.post('/{identifier}/ignored', summary='해당 문서 세션의 제외 단어 추가 및 복원')
def update_ignored(identifier: str, req: IgnoreRequest):
    folder = session_path(identifier)
    word = req.word.strip()
    if not word or '\n' in word or '\r' in word:
        raise HTTPException(422, '제외 단어는 비어 있지 않은 한 줄이어야 합니다.')
    directory = folder / 'ignored'
    directory.mkdir(exist_ok=True)
    key = hashlib.sha256(normalize(word).encode()).hexdigest()
    path = directory / f'{key}.json'
    if req.action == 'add':
        if not path.exists() and len(ignored_words(folder)) >= 500:
            raise HTTPException(422, '세션 제외 단어는 최대 500개입니다.')
        temporary = directory / f'{uuid.uuid4().hex}.tmp'
        try:
            temporary.write_text(json.dumps({'word': word}, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        path.unlink(missing_ok=True)
    return {'ignored': ignored_words(folder)}


# 문서 텍스트 추출 및 초기 개인정보 치환 후보 탐색을 수행함
@router.post('/inspect', summary='문서 서식 유지 개인정보 검사 및 치환 후보 추출', description='PDF, HWP, HWPX 문서에서 텍스트를 추출하고 개인정보(PII) 치환 후보를 자동 탐색합니다.')
def inspect_document(req: InspectRequest):
    source = confined_file(settings.UPLOAD_DIR / req.file_name, settings.UPLOAD_DIR)
    if source.suffix.lower() not in {'.pdf', '.hwp', '.hwpx'}:
        raise HTTPException(422, 'PDF, HWP, HWPX 문서만 지원합니다.')
    if source.stat().st_size > 100 * 1024 * 1024:
        raise HTTPException(422, '100MB 이하의 문서를 선택하세요.')
    identifier = uuid.uuid4().hex
    folder = work_root() / identifier
    folder.mkdir(parents=True)
    try:
        frozen = folder / ('source' + source.suffix.lower())
        shutil.copyfile(source, frozen)
        pdf = folder / 'original.pdf'
        if source.suffix.lower() == '.pdf':
            shutil.copyfile(frozen, pdf)
        else:
            # Read the native text first. A document with no selected PII can
            # be copied byte-for-byte without opening Hancom or re-saving it.
            parsed = read_pseudonym_input(frozen)
            text = '\n'.join(parsed['문서_내용'].astype(str))
            candidates = propose(text)
            printable = sum(char.isprintable() or char in '\n\r\t' for char in text)
            text_is_usable = bool(text.strip()) and printable / max(len(text), 1) >= 0.95
            if text_is_usable and not candidates:
                (folder / 'manifest.json').write_text(json.dumps({'source': frozen.name}), encoding='utf-8')
                return {'id': identifier, 'page_count': 0, 'format': frozen.suffix[1:].upper(),
                        'preview_available': False, 'candidates': [], 'ignored': []}
            native_hancom(frozen, pdf)
        pages = render_pages(pdf, folder, 'original')
        text = inspect_pdf_text(pdf)
        if not text.strip():
            raise ValueError('추출 가능한 텍스트가 없습니다. 스캔 문서는 현재 원본 편집 대상이 아닙니다.')
        (folder / 'manifest.json').write_text(json.dumps({'source': frozen.name}), encoding='utf-8')
        return {'id': identifier, 'page_count': pages, 'preview_available': True, 'format': frozen.suffix[1:].upper(),
                'candidates': propose(text), 'ignored': []}
    except Exception as exc:
        # This directory is generated here, never a client-supplied path.
        shutil.rmtree(folder)
        raise HTTPException(422, f'문서 분석 실패: {exc}') from exc


# 문서 원본 서식 보존 치환 및 가명처리 파이프라인을 실행함
@router.post('/{identifier}/process', summary='문서 원본 서식 보존 치환 및 가명처리', description='지정한 원본-치환값 쌍으로 문서를 변환하고 서식 무결성을 검증한 뒤 결과물을 생성합니다.')
def edit_document(identifier: str, req: EditRequest):
    folder = session_path(identifier)
    excluded = load_whitelist() | {normalize(word) for word in ignored_words(folder)}
    if any(normalize(item.original) in excluded for item in req.replacements):
        raise HTTPException(422, '제외 목록에 있는 항목입니다. 먼저 제외를 해제하세요.')
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    source = confined_file(folder / manifest['source'], folder)
    attempt = uuid.uuid4().hex
    work = folder / attempt
    work.mkdir()
    try:
        if (folder / 'original.pdf').is_file():
            shutil.copyfile(folder / 'original.pdf', work / 'original.pdf')
        elif req.replacements:
            raise ValueError('원본 페이지 렌더링이 없어 치환 검증을 진행할 수 없습니다.')
        else:
            shutil.copyfile(source, work / 'original.pdf')
        output, report = process_document(source, work, [item.model_dump() for item in req.replacements])
        render_pages(work / 'processed.pdf', work, 'processed')
        target = settings.OUTPUT_DIR / 'pseudonymized' / f'document_{attempt}{source.suffix}'
        target.parent.mkdir(parents=True, exist_ok=True)
        (work / 'verified.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
        # Publish only after the verification marker has been committed.
        shutil.copyfile(output, target)
        return {'attempt': attempt, 'verified': True, 'report': report,
                'download_url': f'/api/v1/document-privacy/{identifier}/download/{attempt}'}
    except Exception as exc:
        shutil.rmtree(work)
        raise HTTPException(422, f'검증 실패 · 다운로드 차단: {exc}') from exc


# 검증을 통과한 가명처리 결과 문서를 안전하게 다운로드함
@router.get('/{identifier}/download/{attempt}', summary='검증 완료 문서 다운로드', description='페이지·레이아웃·선택 원문 잔존 검증을 통과한 문서만 다운로드합니다.')
def download_document(identifier: str, attempt: str):
    if not re.fullmatch(r'[0-9a-f]{32}', attempt):
        raise HTTPException(404, '처리 결과를 찾을 수 없습니다.')
    folder = session_path(identifier)
    confined_file(folder / attempt / 'verified.json', folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    suffix = Path(manifest['source']).suffix.lower()
    target = settings.OUTPUT_DIR / 'pseudonymized' / f'document_{attempt}{suffix}'
    return FileResponse(confined_file(target, settings.OUTPUT_DIR), filename=target.name,
                        media_type='application/octet-stream',
                        headers={'X-Content-Type-Options': 'nosniff'})


# 원본 또는 가명처리 완료된 문서의 지정 페이지 미리보기 이미지를 반환함
@router.get('/{identifier}/pages/{page}', summary='문서 페이지 미리보기 이미지 조회', description='원본 또는 가명처리된 문서의 특정 페이지 고해상도 렌더링 이미지를 조회합니다.')
def preview_page(identifier: str, page: int, attempt: str | None = None):
    folder = session_path(identifier)
    if page < 0 or page >= 100:
        raise HTTPException(404, '페이지를 찾을 수 없습니다.')
    if attempt is None:
        path = folder / f'original-{page}.png'
    else:
        if not re.fullmatch(r'[0-9a-f]{32}', attempt):
            raise HTTPException(404, '처리 결과를 찾을 수 없습니다.')
        confined_file(folder / attempt / 'verified.json', folder)
        path = folder / attempt / f'processed-{page}.png'
    return FileResponse(confined_file(path, folder), media_type='image/png',
                        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
