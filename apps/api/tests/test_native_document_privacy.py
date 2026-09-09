import zipfile

import pymupdf as fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from synthetic_api.core.config import settings
from synthetic_api.routes.v1.document_privacy import router
from synthetic_engine.exporters.preserve_document import replace_pdf, verify_pdf_pair, replace_hwpx
from synthetic_engine.privacy.document_replacements import validate_replacements

ITEMS = [{'original': '010-1234-5678', 'replacement': '010-8765-4321'}]


def make_pdf(path, metadata=False):
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.draw_rect(fitz.Rect(20, 20, 380, 270))
        page.insert_text((40, 60), 'Unchanged heading')
        page.insert_text((40, 100), 'Phone: 010-1234-5678')
        page.insert_text((40, 150), 'Unchanged body')
        if metadata: doc.set_metadata({'subject': ITEMS[0]['original']})
        doc.save(path)


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


def test_metadata_residual_blocks_output(tmp_path):
    source, target = tmp_path / 'before.pdf', tmp_path / 'after.pdf'
    make_pdf(source, metadata=True)
    replace_pdf(source, target, ITEMS)
    with pytest.raises(ValueError, match='내부 객체'):
        verify_pdf_pair(source, target, ITEMS)


def test_non_target_pixel_change_blocks_output(tmp_path):
    source, target, altered = (tmp_path / name for name in ('before.pdf', 'after.pdf', 'altered.pdf'))
    make_pdf(source)
    replace_pdf(source, target, ITEMS)
    with fitz.open(target) as doc:
        doc[0].insert_text((40, 220), 'Unexpected')
        doc.save(altered)
    with pytest.raises(ValueError, match='시각적 차이'):
        verify_pdf_pair(source, altered, ITEMS)


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


@pytest.fixture
def client(tmp_path, monkeypatch):
    for attr in ('UPLOAD_DIR', 'OUTPUT_DIR', 'STORAGE_DIR'):
        folder = tmp_path / attr
        folder.mkdir()
        monkeypatch.setattr(settings, attr, folder)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


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
    assert client.get(f'/document-privacy/{identifier}/pages/0', params={'attempt': response.json()['attempt']}).status_code == 200


def test_inspect_rejects_path_escape(client, tmp_path):
    make_pdf(tmp_path / 'outside.pdf')
    assert client.post('/document-privacy/inspect', json={'file_name': '../outside.pdf'}).status_code == 403


def test_replacements_cannot_cascade():
    with pytest.raises(ValueError):
        validate_replacements([{'original': 'AAA', 'replacement': 'BBB'}, {'original': 'BBB', 'replacement': 'CCC'}])


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

