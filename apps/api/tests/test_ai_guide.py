# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ai_guide.py
# 경로: apps/api/tests/test_ai_guide.py
# 목적: AI 친화 가이드(AI-Ready Guide) 엔드포인트 및 로컬 분석기 동작을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Unit tests for AI-Ready Guide rule generator API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from synthetic_api.main import app
from synthetic_api.application.services.ai_guide_analysis import analyze
from synthetic_api.application.services.ai_guide_document.binding import Contract, canonical, validate
from synthetic_api.application.services.ai_guide_document.profile import profile_bytes

client = TestClient(app)


def test_analysis_processing_candidates() -> None:
    result = analyze(
        'timestamp,value,quality_flag\n2025-01-01,1,Y\n,2,N',
        'csv',
    )
    processing = result['processing']
    assert processing['integration']['is_integrated'] is False
    assert processing['missing_value_processing'][0]['method'] is None
    assert processing['missing_value_processing'][0]['target_field_ids'] == ['/*/timestamp']
    assert processing['derived_fields'][0]['derivation_type'] == 'observed'
    assert any(flag['flag_field'] == '/*/quality_flag' for flag in processing['quality_flags'])


def test_binding_processing_contract() -> None:
    profile = profile_bytes(
        b'timestamp,value,quality_flag\n2025-01-01,1,Y\n,2,N',
        'csv',
        'generic.csv',
    )
    model = canonical([profile], 'Generic data', Contract())
    validate(model, Contract())
    assert model['processing']['integration']['is_integrated'] is False
    assert model['processing']['missing_value_processing']
    assert all(field['value_origin'] == 'observed' for field in model['fields'])
    assert any(item['bindingPath'].startswith('/processing/') for item in model['canonicalItems'])


def test_canonical_processing_is_reviewable_without_invented_rules() -> None:
    profile = profile_bytes(b'id,value\n1,10\n2,20', 'csv', 'values.csv')
    model = canonical([profile], 'Values', Contract())
    rules = model['processing']['missing_value_processing']
    assert rules == []
    assert model['processing']['outlier_processing'] == []
    assert not any(
        item['bindingPath'].startswith('/processing/missing_value_processing/')
        and item['status'] == 'AUTO_CONFIRMED'
        for item in model['canonicalItems']
    )


# CSV 파일데이터 기반 AI 친화 가이드 생성 요청이 정상 처리되는지 검증함
def test_generate_rule_csv_file_category() -> None:
    csv_payload = "품목코드,제품명,가격\n101,타이레놀,5000\n102,아스피린,3000"
    res = client.post(
        "/api/v1/ai-guide/generate-rule",
        json={
            "payload_text": csv_payload,
            "format": "csv",
            "preset_style": "gov_standard",
            "document_title": "의약품 목록",
            "orientation": "landscape",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data_category"] == "file"
    assert data["ai_readiness_score"] >= 80
    assert len(data["ai_readiness_checklist"]) > 0
    assert data["document_title"] == "의약품 목록"
    assert len(data["columns"]) == 3
    assert data["columns"][0]["key"] == "품목코드"
    assert "AI 친화 가이드" in data["markdown_guide"]


# JSON API 데이터 기반 AI 친화 가이드 생성 요청이 정상 처리되는지 검증함
def test_generate_rule_json_api_category() -> None:
    json_payload = '[{"기관명": "식약처", "인원": 150}, {"기관명": "질병청", "인원": 200}]'
    res = client.post(
        "/api/v1/ai-guide/generate-rule",
        json={
            "payload_text": json_payload,
            "format": "json",
            "preset_style": "mfds_deliberation",
            "document_title": "기관 인원 통계",
            "orientation": "portrait",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data_category"] == "api"
    assert data["ai_readiness_score"] >= 80
    assert len(data["columns"]) == 2
    assert "기관명" in [c["key"] for c in data["columns"]]
    assert any("OpenAPI" in chk["item"] for chk in data["ai_readiness_checklist"])


# XML API 데이터 기반 정상 처리 및 컬럼 파싱을 검증함
def test_generate_rule_xml_api_category() -> None:
    xml_payload = """<response>
      <header><resultCode>00</resultCode></header>
      <body>
        <items>
          <item><병원명>서울대병원</병원명><병상수>1800</병상수></item>
          <item><병원명>연세대세브란스</병원명><병상수>2000</병상수></item>
        </items>
      </body>
    </response>"""
    res = client.post(
        "/api/v1/ai-guide/generate-rule",
        json={
            "payload_text": xml_payload,
            "format": "xml",
            "document_title": "병원 병상 통계",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data_category"] == "api"
    assert len(data["columns"]) >= 2


# 대용량 플래그 전달 시 대용량 최적화 가이드가 생성되는지 검증함
def test_generate_rule_large_dataset_guide() -> None:
    res = client.post(
        "/api/v1/ai-guide/generate-rule",
        json={
            "payload_text": "id,name,value\n1,a,10\n2,b,20",
            "format": "csv",
            "is_large_dataset": True,
            "file_size_bytes": 104857600,  # 100MB
            "estimated_total_rows": 500000,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_large_dataset"] is True
    assert data["large_data_guide"] is not None
    assert "Parquet" in data["large_data_guide"]


import base64
import io
import json
from pathlib import Path
import pytest
from synthetic_api.application.services.ai_guide_analysis import analyze


@pytest.fixture(autouse=True)
def no_external_ai(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)


# JSON 필드의 유니온 타입 및 null, false, 0 값 판별을 검증함
def test_json_union_and_null_false_zero():
    result=analyze('[{"a":false,"b":0},{"a":null,"b":"001","late":[]}]','json')
    fields={f['path']:f for f in result['fields']}
    assert fields['/*/a']['types']==['boolean','null']
    assert fields['/*/b']['types']==['integer','string']
    assert fields['/*/late']['types']==['array']
    assert fields['/*/a']['null_count']==1
    assert fields['/*/b']['empty_count']==0


# 다양한 JSON 루트 타입에 대한 가이드 생성 정상 동작을 검증함
@pytest.mark.parametrize('payload', ['null','42','false','"hello"','[]','{}'])
def test_json_root_types(payload):
    result=client.post('/api/v1/ai-guide/generate-rule',json={'format':'json','payload_text':payload,'provider':'local'})
    assert result.status_code==200
    assert '항목1' not in result.text


# JSON-LD @graph 및 @context 구조 파싱을 검증함
def test_jsonld_graph_and_context():
    payload={'@context':{'name':'https://schema.org/name'},'@graph':[{'@id':'urn:1','name':{'@value':'이름','@language':'ko'},'items':{'@list':[1,2]}}]}
    result=analyze(json.dumps(payload),'jsonld')
    assert {'json-ld','@context','@graph','@list','@language'}<=set(result['traits'])
    assert any(f['path']=='/@graph/*/name/@value' for f in result['fields'])


# XML 네임스페이스, 속성, 혼합 콘텐츠 및 xsi:nil 파싱을 검증함
def test_xml_namespaces_attributes_mixed_nil():
    result=analyze('<r xmlns:a="urn:a" xmlns:b="urn:b" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><a:x id="001">before<b:y/>after</a:x><b:x xsi:nil="true"/><z>1</z><z>2</z></r>','xml')
    paths={f['path'] for f in result['fields']}
    assert '/r/{urn:a}x/@attributes/id' in paths
    assert '/r/{urn:b}x/@attributes/{http:~1~1www.w3.org~12001~1XMLSchema-instance}nil' in paths
    assert '/r/z/*/#text' in paths
    assert {'mixed-content','xsi:nil'}<=set(result['traits'])


# 유효하지 않은 입력 데이터에 대해 422 오류 응답이 반환되는지 검증함
@pytest.mark.parametrize('fmt,payload', [('json','{"x":1,"x":2}'),('json','[1,'),('json','NaN'),('xml','<r>'),('xml','<!DOCTYPE r [<!ENTITY x SYSTEM "file:///x">]><r>&x;</r>'),('csv','id,id\n1,2'),('csv','a,b\n1,2,3')])
def test_invalid_inputs_are_errors(fmt,payload):
    response=client.post('/api/v1/ai-guide/generate-rule',json={'format':fmt,'payload_text':payload})
    assert response.status_code==422


# 따옴표로 감싸진 줄바꿈이 포함된 CSV 파싱을 검증함
def test_csv_quoted_newline():
    result=analyze('id,note\r\n001,"hello,\nworld"\r\n002,"a""b"','csv')
    assert result['tables'][0]['row_count']==2
    fields={f['path']:f for f in result['fields']}
    assert fields['/*/note']['examples']==['hello,\nworld','a"b']
    assert fields['/*/id']['types']==['string']


# 다중 시트 및 수식이 포함된 XLSX 파일 분석을 검증함
def test_xlsx_multiple_sheets_formula():
    from openpyxl import Workbook
    workbook=Workbook(); workbook.active.append(['id','value']); workbook.active.append(['001','=1+1'])
    second=workbook.create_sheet('second'); second.append(['name']); second.append(['a'])
    out=io.BytesIO(); workbook.save(out)
    result=analyze('','xlsx',base64.b64encode(out.getvalue()).decode())
    assert len(result['tables'])==2
    assert result['tables'][0]['row_count']==1
    assert any('=1+1' in f['examples'] for f in result['fields'])


# local 프로바이더 설정 시 네트워크 호출 방지 및 카테고리 자동 판별을 검증함
def test_local_prevents_network_and_category_override(monkeypatch):
    from synthetic_api.routes.v1 import ai_guide
    monkeypatch.setenv('OPENAI_API_KEY','do-not-use')
    # 네트워크 차단 검증용 모의 함수임
    def denied(*args,**kwargs): raise AssertionError('Network call')
    monkeypatch.setattr(ai_guide.urllib.request,'urlopen',denied)
    response=client.post('/api/v1/ai-guide/generate-rule',json={'format':'json','data_category':'file','payload_text':'{"x":1}','provider':'local'})
    assert response.status_code==200
    assert response.json()['data_category']=='api'
    assert response.json()['ai_powered'] is False


# 외부 AI 호출 실패 시에도 기본 구조 분석 결과가 온전히 보존되는지 검증함
def test_ai_failure_preserves_analysis(monkeypatch):
    from synthetic_api.routes.v1 import ai_guide
    # AI 호출 실패 시뮬레이션용 모의 함수임
    def fail(*args,**kwargs): raise OSError('offline')
    monkeypatch.setattr(ai_guide.urllib.request,'urlopen',fail)
    response=client.post('/api/v1/ai-guide/generate-rule',json={'format':'json','payload_text':'{"x":1}','provider':'openai','api_key':'test'})
    assert response.status_code==200
    assert response.json()['ai_powered'] is False
    assert response.json()['canonical_metadata']['fields'][1]['types']==['integer']


# HWPX 내보내기 및 파서 간 라운드트립 일치성을 검증함
def test_hwpx_export_roundtrip_and_parser_parity(tmp_path):
    from synthetic_api.application.services.ai_guide_document.hwpx_parser import HwpxParser
    from synthetic_engine.document_conversion.parsers.hwpx_parser import HwpxParser as Original
    response=client.post('/api/v1/ai-guide/export-hwpx',json={'markdown':'# 가이드\n중첩 구조 및 결측 검토'})
    assert response.status_code==200
    path=tmp_path/'guide.hwpx';path.write_bytes(response.content)
    parsed=HwpxParser().parse(path); original=Original().parse(path)
    assert len(parsed.sections)==len(original.sections)>0
    assert repr(parsed.sections)==repr(original.sections)
    assert '중첩 구조' in repr(parsed.sections)


# 특수문자 포함 경로 충돌 방지 및 누락 필드 개수 계산을 검증함
def test_paths_do_not_collide_and_missing_fields_count():
    result=analyze('{"":1,"a/b":2,"*":3,"rows":[{"x":0},{"y":false}]}','json')
    fields={f['path']:f for f in result['fields']}
    assert {'$','/','/a~1b','/~2','/rows/*/x'}<=set(fields)
    assert fields['/rows/*/x']['missing_count']==1


# 복합 스칼라 타입에서 false와 0 값이 유실되지 않고 보존되는지 검증함
def test_mixed_scalar_types_preserve_false_and_zero():
    result=analyze('[false,0,null,""]','json')
    field=next(f for f in result['fields'] if f['path']=='/*')
    assert field['examples']==[False,0,None]
    assert field['types']==['boolean','integer','null','string']


# 생성된 HWPX 문서에 데이터 사전 표가 포함되는지 검증함
def test_generated_hwpx_has_data_dictionary_table(tmp_path):
    from synthetic_api.application.services.ai_guide_document.hwpx_parser import HwpxParser
    response=client.post('/api/v1/ai-guide/export-hwpx',json={'markdown':'# 가이드\n| 경로 | 타입 |\n|---|---|\n| /name | string |'})
    assert response.status_code==200
    path=tmp_path/'table.hwpx';path.write_bytes(response.content)
    doc=HwpxParser().parse(path)
    assert any(type(block).__name__=='TableIR' for section in doc.sections for block in section.elements)


# 임의의 키가 포함된 JSON이 유효한 XML로 직렬화되는지 검증함
def test_xml_export_preserves_arbitrary_json_key():
    from lxml import etree
    response=client.post('/api/v1/ai-guide/generate-rule',json={'format':'json','payload_text':'{"a\\u0000b":"value"}','provider':'local'})
    assert response.status_code==200
    etree.fromstring(response.json()['metadata_xml'].encode())


# AI 엔진이 구조를 임의 조작하지 않고 필드 노트만 안전하게 보강하는지 검증함
def test_ai_only_adds_notes_and_receives_complete_structure(monkeypatch):
    from synthetic_api.routes.v1 import ai_guide
    requests=[]
    class Result:
        # 컨텍스트 매니저 진입 메서드임
        def __enter__(self): return self
        # 컨텍스트 매니저 종료 메서드임
        def __exit__(self,*args): pass
        # 모의 응답 바이트를 반환함
        def read(self):
            content={'summary':'검토 초안','metadata':{'description':'수치 관측 데이터'},
                     'fields':[{'path':'/data/*/x','english_name':'observedValue','label':'관측값',
                                'description':'관측된 수치','unit':'','codes':''},
                               {'path':'/invented','english_name':'invented','label':'임의','description':'임의','unit':'','codes':''}]}
            return json.dumps({'choices':[{'message':{'content':json.dumps(content,ensure_ascii=False)}}]}).encode()
    # 가짜 HTTP 요청 핸들러 함수임
    def fake(request,**kwargs):
        requests.append(json.loads(request.data)); return Result()
    monkeypatch.setattr(ai_guide.urllib.request,'urlopen',fake)
    response=client.post('/api/v1/ai-guide/generate-rule',json={
        'format':'json','payload_text':'{"data":[{"x":1}]}','provider':'openai','api_key':'test',
        'user_metadata':{'publisher':'테스트 제공기관','creator':'테스트 소관부서','contact_name':'담당자 연락처'},
    })
    assert response.status_code==200
    result=response.json()
    assert result['ai_powered'] is True
    assert 'invented' not in result['json_rule']
    assert result['suggested_metadata']['description']=='수치 관측 데이터'
    assert result['suggested_field_annotations']['/data/*/x']['english_name']=='observedValue'
    assert '/invented' not in result['suggested_field_annotations']
    payload=json.loads(requests[0]['messages'][1]['content'])
    assert payload['institution_context']['publisher']=='테스트 제공기관'
    assert payload['institution_context']['creator']=='테스트 소관부서'
    assert any(f['path']=='/data/*/x' for f in payload['fields'])
    assert all('examples' not in f for f in payload['fields'])


def test_generate_documents_calls_ai_after_user_input_and_returns_required_outputs(monkeypatch):
    from synthetic_api.routes.v1 import ai_guide
    requests=[]
    class Result:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self):
            content={'dataset_purpose':'AI 데이터 개방 목적 초안','ai_purpose':'분류 활용 초안',
                     'known_limitations':'제공 표본 범위 한계','fields':[{'path':'/*/id','english_name':'itemId','name_ko':'식별자','description':'식별자 초안'}]}
            return json.dumps({'choices':[{'message':{'content':json.dumps(content,ensure_ascii=False)}}]}).encode()
    def fake(request,**kwargs):
        requests.append(json.loads(request.data));return Result()
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setattr(ai_guide.urllib.request,'urlopen',fake)
    payload=base64.b64encode(b'[{"id":1}]').decode()
    response=client.post('/api/v1/ai-guide/generate-documents',json={
        'sources':[{'filename':'sample.json','file_base64':payload}],
        'document_title':'기관 데이터',
        'user_metadata':{'publisher':'사용자 입력 기관'},
        'field_annotations':{},
        'human_format':'odt',
        'provider':'openai',
    })
    assert response.status_code==200
    result=response.json()
    assert result['ai_powered'] is True
    assert result['human_format']=='odt' and result['human_document_base64']
    assert json.loads(result['canonical_json'])['dataset']['publisher']=='사용자 입력 기관'
    assert next(field for field in json.loads(result['canonical_json'])['fields'] if field['path']=='/*/id')['name']=='itemId'
    assert '사용자 입력 기관' in result['metadata_xml']
    assert '사용자 입력 기관' in result['json_ld']
    prompt=json.loads(requests[0]['messages'][1]['content'])
    assert prompt['dataset']['publisher']=='사용자 입력 기관'
    assert 'lowerCamelCase' in prompt['instructions']
