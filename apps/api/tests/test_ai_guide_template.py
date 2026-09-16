# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ai_guide_template.py
# 경로: apps/api/tests/test_ai_guide_template.py
# 목적: HWPX 서식 템플릿 바인딩 및 생성 검증 단위 테스트를 수행함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Template binding must preserve styles, cover all fields, and exclude sample facts."""
import base64
from copy import deepcopy
import io
import json
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from synthetic_api.main import app
from synthetic_api.application.services.ai_guide_analysis import analyze
from synthetic_api.application.services.ai_guide_template import (
    HP, TEMPLATE, TemplateGuideRequest, build_contract, render_template, parse_generated_template,
)

client = TestClient(app)


# 테스트용 템플릿 가이드 요청 객체를 생성함
def request(fmt='csv', text='id,name\n001,Alpha\n002,Beta'):
    model = analyze(text, fmt)
    model['title'] = '새로운 기관 데이터'
    return TemplateGuideRequest(canonical_metadata=model, metadata={'publisher': '새로운 기관'})


# 템플릿 서식 유지, 전 필드 바인딩 및 원본 샘플 텍스트 배제를 검증함
def test_template_styles_all_fields_and_no_sample_facts():
    req = request()
    data = render_template(req)
    with ZipFile(io.BytesIO(data)) as z, ZipFile(TEMPLATE) as original:
        assert z.read('Contents/header.xml') == original.read('Contents/header.xml')
        root = etree.fromstring(z.read('Contents/section0.xml'))
        text = '\n'.join(n.text or '' for n in root.iter(f'{{{HP}}}t'))
        assert '새로운 기관 데이터' in text
        for forbidden in ['113,880', '22,706', '13개 발전소', 'ASOS', 'solar_weather_hourly']:
            assert forbidden not in text
            assert forbidden not in z.read('Preview/PrvText.txt').decode()
        assert 'Preview/PrvImage.png' not in z.namelist()
        ids = [node.get('id') for node in root.iter() if node.tag in {f'{{{HP}}}p', f'{{{HP}}}tbl'}]
        assert len(ids) == len(set(ids))
        assert z.infolist()[0].filename == 'mimetype'
    contract = parse_generated_template(data)
    assert len(contract['dictionary']) == 2
    assert contract['metadata']['publisher']['status'] == 'USER_PROVIDED'
    assert contract['metadata']['license']['status'] == 'REVIEW_REQUIRED'
    assert contract['analysis']['sha256'] == req.canonical_metadata['sha256']


# API 데이터 분기 및 필드 주석이 정상 반영되는지 검증함
def test_api_branch_and_annotations():
    req = request('json', '{"response":{"items":[{"code":"001","amount":12}]}}')
    req.metadata.update({'endpoint': 'https://data.example.test/items', 'http_method': 'GET'})
    from synthetic_api.application.services.ai_guide_template import FieldAnnotation
    req.field_annotations['/response/items/*/amount'] = FieldAnnotation(unit='원', description='금액')
    data = render_template(req)
    contract = parse_generated_template(data)
    assert contract['metadata']['endpoint']['value'] == 'https://data.example.test/items'
    assert contract['dictionary'][1]['annotation']['unit'] == '원'
    with ZipFile(io.BytesIO(data)) as z:
        text = z.read('Preview/PrvText.txt').decode()
        assert 'API 서비스·요청·응답·오류 계약' in text
        assert '파일 적재·변환 지침' not in text


# 샘플 행 수를 초과하는 대량 필드가 모두 확장되어 생성되는지 검증함
def test_all_fields_expand_over_sample_rows():
    req = request('json', json.dumps([{f'field_{i}': i for i in range(40)}]))
    contract = parse_generated_template(render_template(req))
    assert len(contract['dictionary']) == 40
    assert contract['dictionary'][-1]['path'] == '/*/field_39'


# HWPX 본문 텍스트가 임의 변경되었을 때 무결성 오류를 검출하는지 검증함
def test_changed_visible_content_is_not_accepted():
    data = render_template(request())
    out = io.BytesIO()
    with ZipFile(io.BytesIO(data)) as src, ZipFile(out, 'w') as dst:
        for item in src.infolist():
            payload = src.read(item.filename)
            if item.filename == 'Contents/section0.xml':
                payload = payload.replace('새로운 기관 데이터'.encode(), '변경된 데이터명'.encode())
            dst.writestr(item, payload)
    with pytest.raises(ValueError, match='불일치'):
        parse_generated_template(out.getvalue())


# 원본 샘플 HWPX 파일에 메타데이터가 없는 상태를 올바르게 판별하는지 검증함
def test_original_sample_is_not_generated_contract():
    with pytest.raises(ValueError, match='메타데이터가 없습니다'):
        parse_generated_template(TEMPLATE.read_bytes())


# 잘못된 메타데이터나 경로가 전달되었을 때 바인딩이 거부되는지 검증함
@pytest.mark.parametrize('change', ['unknown_metadata', 'unknown_path', 'bad_count', 'duplicate_path'])
def test_reject_invalid_bindings(change):
    req = request()
    if change == 'unknown_metadata': req.metadata['invented'] = 'value'
    elif change == 'unknown_path':
        from synthetic_api.application.services.ai_guide_template import FieldAnnotation
        req.field_annotations['/not-present'] = FieldAnnotation(unit='m')
    elif change == 'bad_count': req.canonical_metadata['fields'][1]['null_count'] = 100
    else: req.canonical_metadata['fields'].append(deepcopy(req.canonical_metadata['fields'][0]))
    with pytest.raises(ValueError): build_contract(req)


# 템플릿 HWPX 내보내기 및 재파싱 API 엔드포인트를 검증함
def test_export_and_parse_endpoints():
    result = client.post('/api/v1/ai-guide/export-template-hwpx', json=request().model_dump())
    assert result.status_code == 200, result.text
    parsed = client.post('/api/v1/ai-guide/parse-template-hwpx', json={'file_base64': base64.b64encode(result.content).decode()})
    assert parsed.status_code == 200
    assert parsed.json()['title'] == '새로운 기관 데이터'


# 내부 메타데이터가 변조되었을 때 무결성 검증 실패를 확인합
def test_changed_embedded_metadata_is_not_accepted():
    data = render_template(request())
    out = io.BytesIO()
    with ZipFile(io.BytesIO(data)) as src, ZipFile(out, 'w') as dst:
        for item in src.infolist():
            payload = src.read(item.filename)
            if item.filename == 'AIReady/metadata.json':
                value = json.loads(payload)
                value['metadata']['publisher']['value'] = '다른 기관'
                payload = json.dumps(value, ensure_ascii=False).encode()
            dst.writestr(item, payload)
    with pytest.raises(ValueError, match='불일치'):
        parse_generated_template(out.getvalue())
