# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_document_converter.py
# 경로: apps/api/tests/test_document_converter.py
# 목적: HWP, HWPX, PDF 문서 서식 보존 변환 로직을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import xml.etree.ElementTree as ET

import pytest
import pymupdf as fitz
from fastapi import FastAPI
from fastapi.testclient import TestClient

from synthetic_api.core.config import settings
from synthetic_api.routes.v1 import converter
from synthetic_api.application.services.document_conversion_service import (
    _convert_hwpx_tbl_to_grid_and_html,
    _document_delivery_state,
    _extract_structured_tables,
    _make_document_soup,
)


# document converter six 컬럼 목록 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('target', ['html', 'md', 'docx', 'hwpx', 'xlsx'])
def test_document_converter_six_columns(tmp_path, monkeypatch, target):
    for name in ('UPLOAD_DIR', 'OUTPUT_DIR'):
        folder = tmp_path / name
        folder.mkdir()
        monkeypatch.setattr(settings, name, folder)
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=400)
        for y in (80, 120, 160):
            page.draw_line((30, y), (570, y))
        for x in range(30, 571, 90):
            page.draw_line((x, 80), (x, 160))
        for row in range(2):
            for col in range(6):
                page.insert_text((35 + 90 * col, 105 + 40 * row), f'R{row}C{col}')
        payload = pdf.tobytes()
    app = FastAPI()
    app.include_router(converter.router, prefix='/api/v1')
    with TestClient(app) as client:
        response = client.post('/api/v1/converter/convert',
                               files={'file': ('six.pdf', payload, 'application/pdf')},
                               data={'target_format': target})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['target_format'].lower() == target
    assert any(p.is_file() and p.stat().st_size for p in settings.OUTPUT_DIR.rglob('*'))
    assert result['document_structure']['quality']['layout_verified'] is False
    assert result['document_structure']['quality']['text_coverage'] >= 0.95
    assert result['download_ready'] is True
    assert result['document_structure']['quality']['ocr_status'] == 'not_required'
    assert result['document_structure']['quality']['page_progress'][0]['progress'] == 100


# document 품질 detects missing 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_document_quality_detects_missing_text(tmp_path):
    from synthetic_api.application.services.conversion_quality import assess_parse_quality
    source = tmp_path / 'text.txt'
    source.write_text('abcdefghij', encoding='utf-8')
    result = assess_parse_quality(source, 'abcde')
    assert result['text_coverage'] == 0.5
    assert result['warnings']
    assert result['layout_similarity'] is None
    assert result['requires_review'] is True


# document 품질 scanned 페이지 requires review 기능의 정상 동작 및 제약조건을 테스트함
def test_document_quality_scanned_page_requires_review(tmp_path):
    from synthetic_api.application.services.conversion_quality import assess_parse_quality
    source = tmp_path / 'scan.pdf'
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(source)
    result = assess_parse_quality(source, 'OCR result')
    assert result['text_coverage'] is None
    assert result['ocr_review_pages'] == [1]
    assert result['requires_review']


# 이미지 품질 without measured 인식 신뢰도 is not fabricated 기능의 정상 동작 및 제약조건을 테스트함
def test_image_quality_without_measured_confidence_is_not_fabricated(tmp_path):
    from synthetic_api.application.services.conversion_quality import assess_parse_quality

    source = tmp_path / 'scan.png'
    source.write_bytes(b'fixture')
    result = assess_parse_quality(source, 'OCR result', ocr_confidence=None)

    assert result['text_coverage'] is None
    assert result['requires_review'] is True
    assert any('신뢰도 측정값' in warning for warning in result['warnings'])


# document delivery state 블록 목록 review required output 기능의 정상 동작 및 제약조건을 테스트함
def test_document_delivery_state_blocks_review_required_output():
    assert _document_delivery_state({
        'quality': {'requires_review': True, 'ocr_status': 'review_required'}
    }) == ('review_required', False)
    assert _document_delivery_state({
        'quality': {'requires_review': False, 'ocr_status': 'not_required'}
    }) == ('success', True)


# OCR 인식 품질 요약 정보 reports review 페이지 목록 and progress 기능의 정상 동작 및 제약조건을 테스트함
def test_ocr_quality_summary_reports_review_pages_and_progress(tmp_path):
    from synthetic_api.application.services.conversion_quality import assess_parse_quality, build_ocr_quality_summary
    source = tmp_path / 'scan.pdf'
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(source)
    quality = assess_parse_quality(source, 'OCR result')

    summary = build_ocr_quality_summary(
        source,
        html_preview='<div class="ocr-quality">신뢰도 72.5% · 확인 필요</div>',
        tables=[],
        pages_count=1,
        base_quality=quality,
    )

    assert summary['ocr_status'] == 'review_required'
    assert summary['average_confidence'] == 0.725
    assert summary['page_progress'] == [{
        'page': 1,
        'stage': 'review',
        'progress': 100,
        'status': 'review_required',
        'message': 'OCR 결과 검토 필요',
    }]
    assert summary['low_confidence_regions'][0]['page'] == 1


# 한글 표준(HWPX) HTML 웹 문서 preserves source 컬럼 ratios and line breaks 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_html_preserves_source_column_ratios_and_line_breaks():
    namespace = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
    table = ET.fromstring(f'''
      <hp:tbl xmlns:hp="{namespace}" colCnt="2">
        <hp:tr>
          <hp:tc><hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="2"/><hp:cellSz width="11483" height="2000"/>
            <hp:subList><hp:p><hp:run><hp:t>구분</hp:t></hp:run></hp:p></hp:subList></hp:tc>
          <hp:tc><hp:cellAddr colAddr="1" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="39083" height="1000"/>
            <hp:subList><hp:p><hp:run><hp:t>첫 문단</hp:t></hp:run></hp:p><hp:p><hp:run><hp:t>둘째 문단</hp:t></hp:run></hp:p></hp:subList></hp:tc>
        </hp:tr>
        <hp:tr>
          <hp:tc><hp:cellAddr colAddr="1" rowAddr="1"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="39083" height="1000"/>
            <hp:subList><hp:p><hp:run><hp:t>다음 행</hp:t></hp:run></hp:p></hp:subList></hp:tc>
        </hp:tr>
      </hp:tbl>
    ''')

    html, markdown = _convert_hwpx_tbl_to_grid_and_html(table, {'hp': namespace})

    assert '<col style="width:22.7089%"' in html
    assert '<col style="width:77.2911%"' in html
    assert '<td rowspan="2" data-row="0" data-col="0"' in html
    assert '첫 문단<br/>둘째 문단' in html
    assert '첫 문단<br/>둘째 문단' in markdown
    assert '|  | 다음 행 |' in markdown


# structured 표(테이블) metadata keeps rowspan 기하 좌표 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_table_metadata_keeps_rowspan_coordinates():
    soup = _make_document_soup(
        '<table><tr><td rowspan="2" data-col="0">개요</td><td data-col="1">배경</td>'
        '<td data-col="2">내용</td></tr><tr><td data-col="1">설명</td>'
        '<td data-col="2">상세</td></tr></table>'
    )

    table = _extract_structured_tables(soup)[0]

    assert (table['rows'], table['columns']) == (2, 3)
    assert table['preview'] == [['개요', '배경', '내용'], ['', '설명', '상세']]
    assert table['cells'][0] == {
        'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1,
        'text': '개요', 'confidence': 1.0,
    }
    assert table['confidence'] == 1.0
    assert table['warnings'] == []


# 데이터셋 xml round trip through converter api 기능의 정상 동작 및 제약조건을 테스트함
def test_dataset_xml_round_trip_through_converter_api(tmp_path, monkeypatch):
    for name in ('UPLOAD_DIR', 'OUTPUT_DIR'):
        folder = tmp_path / name
        folder.mkdir()
        monkeypatch.setattr(settings, name, folder)
    app = FastAPI()
    app.include_router(converter.router, prefix='/api/v1')
    csv_payload = '항목명,설명\n지역,개인의 거주지역\n성별,개인의 성별\n'.encode('utf-8')

    with TestClient(app) as client:
        to_xml = client.post(
            '/api/v1/converter/convert',
            files={'file': ('records.csv', csv_payload, 'text/csv')},
            data={'target_format': 'xml'},
        )
        assert to_xml.status_code == 200, to_xml.text
        xml_path = next((settings.OUTPUT_DIR / 'converted').glob('records_*.xml'))
        root = ET.parse(xml_path).getroot()
        assert root.find("./record/field[@name='항목명']").text == '지역'

        to_csv = client.post(
            '/api/v1/converter/convert',
            files={'file': ('records.xml', xml_path.read_bytes(), 'application/xml')},
            data={'target_format': 'csv'},
        )
        assert to_csv.status_code == 200, to_csv.text
        csv_path = sorted((settings.OUTPUT_DIR / 'converted').glob('records_*.csv'))[-1]
        converted = csv_path.read_text(encoding='utf-8-sig')
        assert '항목명,설명' in converted
        assert '지역,개인의 거주지역' in converted


# 데이터셋 xml rejects dtd 기능의 정상 동작 및 제약조건을 테스트함
def test_dataset_xml_rejects_dtd(tmp_path, monkeypatch):
    for name in ('UPLOAD_DIR', 'OUTPUT_DIR'):
        folder = tmp_path / name
        folder.mkdir()
        monkeypatch.setattr(settings, name, folder)
    app = FastAPI()
    app.include_router(converter.router, prefix='/api/v1')
    payload = b'<!DOCTYPE records [<!ENTITY x "unsafe">]><records><record>&x;</record></records>'

    with TestClient(app) as client:
        response = client.post(
            '/api/v1/converter/convert',
            files={'file': ('unsafe.xml', payload, 'application/xml')},
            data={'target_format': 'csv'},
        )

    assert response.status_code == 400
    assert 'DTD' in response.json()['detail']
