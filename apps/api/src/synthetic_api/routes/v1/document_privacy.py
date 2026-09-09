"""
파일명: document_privacy.py
경로: apps/api/src/synthetic_api/routes/v1/document_privacy.py
목적: 문서 개인정보 검사와 원본 서식 편집 API를 제공함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
import json
import re
import shutil
import uuid
from pathlib import Path

import pymupdf
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from synthetic_api.core.config import settings
from synthetic_api.infrastructure.file_access import confined_file
from synthetic_engine.exporters.preserve_document import native_hancom, process_document, render_pages
from synthetic_engine.privacy.document_replacements import propose

router = APIRouter(prefix='/document-privacy', tags=['document-privacy'])


class InspectRequest(BaseModel):
    file_name: str


class Replacement(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    replacement: str = Field(min_length=1, max_length=200)


class EditRequest(BaseModel):
    replacements: list[Replacement] = Field(min_length=1, max_length=500)


def work_root():
    return settings.STORAGE_DIR / 'temp' / 'document-privacy'


def session_path(identifier):
    if not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise HTTPException(404, '작업을 찾을 수 없습니다.')
    folder = work_root() / identifier
    confined_file(folder / 'manifest.json', work_root())
    return folder


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
            native_hancom(frozen, pdf)
        pages = render_pages(pdf, folder, 'original')
        with pymupdf.open(pdf) as doc:
            text = '\n'.join(page.get_text() for page in doc)
        if not text.strip():
            raise ValueError('추출 가능한 텍스트가 없습니다. 스캔 문서는 현재 원본 편집 대상이 아닙니다.')
        (folder / 'manifest.json').write_text(json.dumps({'source': frozen.name}), encoding='utf-8')
        return {'id': identifier, 'page_count': pages, 'format': frozen.suffix[1:].upper(),
                'candidates': propose(text)}
    except Exception as exc:
        # This directory is generated here, never a client-supplied path.
        shutil.rmtree(folder)
        raise HTTPException(422, f'문서 분석 실패: {exc}') from exc


@router.post('/{identifier}/process', summary='문서 원본 서식 보존 치환 및 가명처리', description='지정한 원본-치환값 쌍으로 문서를 변환하고 서식 무결성을 검증한 뒤 결과물을 생성합니다.')
def edit_document(identifier: str, req: EditRequest):
    folder = session_path(identifier)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    source = confined_file(folder / manifest['source'], folder)
    attempt = uuid.uuid4().hex
    work = folder / attempt
    work.mkdir()
    try:
        shutil.copyfile(folder / 'original.pdf', work / 'original.pdf')
        output, report = process_document(source, work, [item.model_dump() for item in req.replacements])
        render_pages(work / 'processed.pdf', work, 'processed')
        target = settings.OUTPUT_DIR / 'pseudonymized' / f'document_{attempt}{source.suffix}'
        target.parent.mkdir(parents=True, exist_ok=True)
        # No public path is created until every verification and preview succeeds.
        shutil.copyfile(output, target)
        (work / 'verified.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
        return {'attempt': attempt, 'report': report,
                'download_url': '/api/v1/files/download?path=' + target.as_posix()}
    except Exception as exc:
        shutil.rmtree(work)
        raise HTTPException(422, f'검증 실패 · 다운로드 차단: {exc}') from exc


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
