# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_native_document_privacy.py
# 경로: apps/api/tests/test_native_document_privacy.py
# 목적: 네이티브 HWPX/DOCX 개인정보 마스킹 및 서식 보존 API를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import zipfile

import pymupdf as fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from synthetic_api.core.config import settings
from synthetic_api.routes.v1.document_privacy import router
from synthetic_engine.exporters.preserve_document import process_document, replace_pdf, verify_pdf_pair, replace_hwpx
from synthetic_engine.privacy.document_replacements import validate_replacements

ITEMS = [{'original': '010-1234-5678', 'replacement': '010-8765-4321'}]


# rotated PDF 문서 direct edit and visual validation 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('rotation', [90, 180, 270])
@pytest.mark.parametrize('cropped', [False, True])
def test_rotated_pdf_direct_edit_and_visual_validation(tmp_path, rotation, cropped):
    source, target = tmp_path / 'rotated.pdf', tmp_path / 'result.pdf'
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((40, 100), 'Phone: 010-1234-5678')
        page.insert_text((40, 160), 'Unchanged')
        if cropped:
            page.set_cropbox(fitz.Rect(10, 20, 390, 280))
        page.set_rotation(rotation)
        doc.save(source)
    replace_pdf(source, target, ITEMS)
    assert verify_pdf_pair(source, target, ITEMS)['changed_regions'] == 1
    with fitz.open(target) as doc:
        assert doc[0].rotation == rotation
        assert ITEMS[0]['replacement'] in doc[0].get_text()


# missing search 용어 목록 are reported 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_search_terms_are_reported(tmp_path):
    source = tmp_path / 'source.pdf'
    make_pdf(source)
    with pytest.raises(ValueError, match='NOT_FOUND'):
        replace_pdf(source, tmp_path / 'result.pdf', [{'original': 'NOT_FOUND', 'replacement': 'REPLACED!'}])


# mixed rotation PDF 문서 multiple occurrences 기능의 정상 동작 및 제약조건을 테스트함
def test_mixed_rotation_pdf_multiple_occurrences(tmp_path):
    source, output = tmp_path / 'mixed.pdf', tmp_path / 'result.pdf'
    with fitz.open() as pdf:
        for rotation in (0, 90, 180, 270):
            page = pdf.new_page(width=400, height=300)
            page.insert_text((40, 90), 'Phone: 010-1234-5678')
            page.insert_text((40, 140), 'Phone: 010-1234-5678')
            page.set_rotation(rotation)
        pdf.save(source)
    replace_pdf(source, output, ITEMS)
    assert verify_pdf_pair(source, output, ITEMS)['changed_regions'] == 8


# PDF 문서 객체 또는 요소를 생성함
def make_pdf(path, metadata=False):
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.draw_rect(fitz.Rect(20, 20, 380, 270))
        page.insert_text((40, 60), 'Unchanged heading')
        page.insert_text((40, 100), 'Phone: 010-1234-5678')
        page.insert_text((40, 150), 'Unchanged body')
        if metadata: doc.set_metadata({'subject': ITEMS[0]['original']})
        doc.save(path)


# PDF 문서 direct edit retains layout 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_direct_edit_retains_layout(tmp_path):
    source, target = tmp_path / 'before.pdf', tmp_path / 'after.pdf'
    make_pdf(source)
    replace_pdf(source, target, ITEMS)
    report = verify_pdf_pair(source, target, ITEMS)
    assert report['changed_regions'] == 1
    with fitz.open(target) as doc:
        text = doc[0].get_text()
        assert 'Unchanged heading' in text and 'Unchanged body' in text
        assert ITEMS[0]['replacement'] in text
        assert ITEMS[0]['original'] not in text


# PDF 문서 replacement across 글꼴 runs 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_replacement_across_font_runs(tmp_path):
    source, target = tmp_path / 'mixed.pdf', tmp_path / 'result.pdf'
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 100), 'ABC', fontname='hebo')
        x = 40 + fitz.get_text_length('ABC', fontname='hebo', fontsize=11)
        page.insert_text((x, 100), '123', fontname='helv')
        doc.save(source)
    items = [{'original': 'ABC123', 'replacement': 'XYZ456'}]
    replace_pdf(source, target, items)
    assert verify_pdf_pair(source, target, items)['changed_regions'] == 1


# document context candidates exclude business 용어 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_document_context_candidates_exclude_business_terms():
    from synthetic_engine.privacy.document_replacements import propose
    text = '본인 인증 필요. 고객 박진우(생년월일: 1984-05-18), 신한은행 110-382-948123 (예금주: 박진우)'
    found = {item['original']: item for item in propose(text)}
    assert {'박진우', '1984-05-18', '110-382-948123'} <= found.keys()
    assert '인증' not in found and '신한은행' not in found
    assert found['1984-05-18']['replacement'] == '1990-06-15'


# PDF 문서 without candidates is copied and verified as exact match 기능의 정상 동작 및 제약조건을 테스트함
def test_pdf_without_candidates_is_copied_and_verified_as_exact_match(tmp_path):
    source = tmp_path / 'before.pdf'
    work = tmp_path / 'work'
    work.mkdir()
    make_pdf(source)
    # The source has no selected PII in this scenario: no re-render or rebuild.
    (work / 'original.pdf').write_bytes(source.read_bytes())
    output, report = process_document(source, work, [])
    assert output.read_bytes() == source.read_bytes()
    assert report['similarity_percent'] == 100.0
    assert report['changed_regions'] == 0


# metadata residual 블록 목록 output 기능의 정상 동작 및 제약조건을 테스트함
def test_metadata_residual_blocks_output(tmp_path):
    source, target = tmp_path / 'before.pdf', tmp_path / 'after.pdf'
    make_pdf(source, metadata=True)
    replace_pdf(source, target, ITEMS)
    with pytest.raises(ValueError, match='내부 객체'):
        verify_pdf_pair(source, target, ITEMS)


# non target pixel change 블록 목록 output 기능의 정상 동작 및 제약조건을 테스트함
def test_non_target_pixel_change_blocks_output(tmp_path):
    source, target, altered = (tmp_path / name for name in ('before.pdf', 'after.pdf', 'altered.pdf'))
    make_pdf(source)
    replace_pdf(source, target, ITEMS)
    with fitz.open(target) as doc:
        doc[0].insert_text((40, 220), 'Unexpected')
        doc.save(altered)
    with pytest.raises(ValueError, match='시각적 차이'):
        verify_pdf_pair(source, altered, ITEMS)


# 한글 표준(HWPX) keeps 분할 runs and other entries 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_keeps_split_runs_and_other_entries(tmp_path):
    source, target = tmp_path / 'before.hwpx', tmp_path / 'after.hwpx'
    xml = b'<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"><hp:p id="1"><hp:run charPrIDRef="4"><hp:t>Phone: 010-1234-</hp:t></hp:run><hp:run charPrIDRef="4"><hp:t>5678 unchanged</hp:t></hp:run></hp:p></hp:sec>'
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('Contents/section0.xml', xml)
        z.writestr('BinData/image.png', b'unchanged image')
        z.writestr('Preview/PrvText.txt', ITEMS[0]['original'])
    validate_replacements(ITEMS)
    replace_hwpx(source, target, ITEMS)
    with zipfile.ZipFile(target) as z:
        data = z.read('Contents/section0.xml')
        assert b'010-8765-' in data and b'4321 unchanged' in data
        assert data.count(b'charPrIDRef="4"') == 2
        assert z.read('BinData/image.png') == b'unchanged image'
        assert 'Preview/PrvText.txt' not in z.namelist()


# client 작업을 수행함
@pytest.fixture
def client(tmp_path, monkeypatch):
    for attr in ('UPLOAD_DIR', 'OUTPUT_DIR', 'STORAGE_DIR'):
        folder = tmp_path / attr
        folder.mkdir()
        monkeypatch.setattr(settings, attr, folder)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# native api only publishes verified 파일 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_native_api_only_publishes_verified_files(client):
    make_pdf(settings.UPLOAD_DIR / 'test.pdf')
    response = client.post('/document-privacy/inspect', json={'file_name': 'test.pdf'})
    assert response.status_code == 200, response.text
    identifier = response.json()['id']
    assert client.get(f'/document-privacy/{identifier}/pages/0').headers['content-type'] == 'image/png'
    invalid = client.post(f'/document-privacy/{identifier}/process', json={'replacements': [{'original': 'missing', 'replacement': 'changed'}]})
    assert invalid.status_code == 422
    assert not list(settings.OUTPUT_DIR.rglob('*.pdf'))
    response = client.post(f'/document-privacy/{identifier}/process', json={'replacements': ITEMS})
    assert response.status_code == 200, response.text
    assert len(list(settings.OUTPUT_DIR.rglob('*.pdf'))) == 1
    assert response.json()['download_url'].endswith(f'/document-privacy/{identifier}/download/{response.json()["attempt"]}')
    download = client.get(response.json()['download_url'].replace('/api/v1', '', 1))
    assert download.status_code == 200
    assert download.content.startswith(b'%PDF')
    assert client.get(f'/document-privacy/{identifier}/pages/0', params={'attempt': response.json()['attempt']}).status_code == 200


# inspect rejects 파일 경로 escape 기능의 정상 동작 및 제약조건을 테스트함
def test_inspect_rejects_path_escape(client, tmp_path):
    make_pdf(tmp_path / 'outside.pdf')
    assert client.post('/document-privacy/inspect', json={'file_name': '../outside.pdf'}).status_code == 403


# replacements cannot cascade 기능의 정상 동작 및 제약조건을 테스트함
def test_replacements_cannot_cascade():
    with pytest.raises(ValueError):
        validate_replacements([{'original': 'AAA', 'replacement': 'BBB'}, {'original': 'BBB', 'replacement': 'CCC'}])


# 세션 exclusions persist and remain isolated 기능의 정상 동작 및 제약조건을 테스트함
def test_session_exclusions_persist_and_remain_isolated(client):
    make_pdf(settings.UPLOAD_DIR / 'test.pdf')
    first = client.post('/document-privacy/inspect', json={'file_name': 'test.pdf'}).json()['id']
    second = client.post('/document-privacy/inspect', json={'file_name': 'test.pdf'}).json()['id']
    word = ITEMS[0]['original']
    response = client.post(f'/document-privacy/{first}/ignored', json={'word': word})
    assert response.status_code == 200
    assert response.json()['ignored'] == [word]
    again = client.get(f'/document-privacy/{first}/candidates').json()
    assert again['candidates'] == [] and again['ignored'] == [word]
    assert client.get(f'/document-privacy/{second}/candidates').json()['candidates']
    blocked = client.post(f'/document-privacy/{first}/process', json={'replacements': ITEMS})
    assert blocked.status_code == 422
    assert not list(settings.OUTPUT_DIR.rglob('*.pdf'))
    client.post(f'/document-privacy/{first}/ignored', json={'word': word, 'action': 'remove'})
    assert client.get(f'/document-privacy/{first}/candidates').json()['candidates']


# 화이트리스트 api is read only 기능의 정상 동작 및 제약조건을 테스트함
def test_whitelist_api_is_read_only(client, tmp_path, monkeypatch):
    path = tmp_path / 'domain.json'
    path.write_text('["domain-term"]', encoding='utf-8')
    monkeypatch.setenv('SYNTHETIC_PII_WHITELIST_PATH', str(path))
    response = client.get('/document-privacy/whitelist')
    assert response.json()['words'] == ['domain-term']
    assert client.post('/document-privacy/whitelist', json={'words': []}).status_code == 405


# 세션 ignore validation 기능의 정상 동작 및 제약조건을 테스트함
def test_session_ignore_validation(client):
    assert client.post('/document-privacy/not-a-session/ignored', json={'word': 'test'}).status_code == 404
    make_pdf(settings.UPLOAD_DIR / 'test.pdf')
    identifier = client.post('/document-privacy/inspect', json={'file_name': 'test.pdf'}).json()['id']
    assert client.post(f'/document-privacy/{identifier}/ignored', json={'word': ' '}).status_code == 422
    assert client.post(f'/document-privacy/{identifier}/ignored', json={'word': 'test', 'action': 'invalid'}).status_code == 422


# korean name masking with 폴백 글꼴 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_name_masking_with_fallback_font(tmp_path):
    source, target = tmp_path / 'korean_before.pdf', tmp_path / 'korean_after.pdf'
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=250)
        page.draw_rect(fitz.Rect(20, 20, 380, 230))
        # Insert Korean text using fitz font buffer
        k_buf = fitz.Font('korean').buffer
        page.insert_font(fontname='CustomKorean', fontbuffer=k_buf)
        page.insert_text((40, 60), '임상시험 보고서', fontname='CustomKorean', fontsize=14)
        page.insert_text((40, 100), '연구책임자: 홍길동 박사', fontname='CustomKorean', fontsize=12)
        page.insert_text((40, 140), '승인완료 본문 내용 유지', fontname='CustomKorean', fontsize=11)
        doc.save(source)

    items = [{'original': '홍길동', 'replacement': '홍*동'}]
    replace_pdf(source, target, items)
    report = verify_pdf_pair(source, target, items)
    assert report['layout'] == 'PASS'
    assert report['selected_text_residual'] == 'PASS'
    assert report['changed_regions'] == 1

    with fitz.open(target) as doc:
        text = doc[0].get_text()
        assert '홍*동' in text
        assert '홍길동' not in text
        assert '연구책임자:' in text
        assert '임상시험 보고서' in text


# propose korean names 기능의 정상 동작 및 제약조건을 테스트함
def test_propose_korean_names():
    from synthetic_engine.privacy.document_replacements import propose
    text = (
        '임상연구 심의서\n'
        '연구책임자: 홍길동\n'
        '수검자: 김철수\n'
        '확인자: 남궁민수\n'
        '추가 피험자 황보연 및 선우용녀 심사관'
    )
    candidates = propose(text)
    items_by_orig = {c['original']: c for c in candidates}
    assert '홍길동' in items_by_orig
    assert items_by_orig['홍길동']['replacement'] == '홍*동'
    assert '김철수' in items_by_orig
    assert items_by_orig['김철수']['replacement'] == '김*수'
    assert '남궁민수' in items_by_orig
    assert items_by_orig['남궁민수']['replacement'] == '남궁*수'
