# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ai_guide_documents.py
# 경로: apps/api/tests/test_ai_guide_documents.py
# 목적: AI 가이드 문서 바인딩, 프로파일링 및 형식 변환 회귀 테스트를 수행함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Behavioral regressions for shared guide analysis, binding and typed exports."""
import copy
import io
import json

import pytest
from openpyxl import Workbook

from synthetic_api.application.services.ai_guide_document.binding import Contract,validate,pointer
from synthetic_api.application.services.ai_guide_document.profile import profile_bytes,compare_json_xml
from synthetic_api.application.services.ai_guide_document.service import generate
from synthetic_api.application.services.ai_guide_document.render import bind_text


# XLSX 파일의 결측치, 0, 불리언, 수식 및 시계열 간격 프로파일링을 검증함
def test_xlsx_null_empty_zero_false_formula_and_temporal():
    workbook=Workbook();sheet=workbook.active
    sheet.append(['date','hour','sensor id','value','flag','empty','formula'])
    sheet.append([20250101,0,'a',0,False,'','=1+2'])
    sheet.append([20250101,1,'a',2,True,None,None])
    sheet.append([20250101,3,'a',None,False,None,None])
    stream=io.BytesIO();workbook.save(stream)
    result=profile_bytes(stream.getvalue(),'xlsx','another.xlsx')
    fields={f['name']:f for f in result['fields']}
    assert fields['value']['numeric_count']==2
    assert fields['value']['mean']==1
    assert fields['value']['zero_count']==1
    assert fields['flag']['false_count']==2
    assert fields['empty']['empty_count']==1
    assert fields['empty']['null_count']==2
    assert fields['formula']['uncached_formula_count']==1
    assert fields['formula']['numeric_count']==0
    temporal=result['tables'][0]['temporal']
    assert temporal['modal_interval_seconds']==3600
    assert len(temporal['groups'][0]['gaps'])==1


# JSON 상태값(null, 빈문자열, 빈배열) 및 XML xsi:nil 파싱 처리를 검증함
def test_json_states_and_xml_nil():
    result=profile_bytes(b'[{"a":null,"z":0,"f":false,"x":[]},{"a":""}]','json','a.json')
    fields={f['path']:f for f in result['fields']}
    assert fields['/*/a']['null_count']==1
    assert fields['/*/a']['empty_count']==1
    assert fields['/*/z']['zero_count']==1
    assert fields['/*/z']['missing_count']==1
    assert fields['/*/x']['empty_array_count']==1
    xml=profile_bytes(b'<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><v xsi:nil="true"/><v/></r>','xml','a.xml')
    leaf=next(f for f in xml['fields'] if f['path']=='/r/v/*/#text')
    assert leaf['null_count']==1 and leaf['empty_count']==1


# JSON과 XML 비교 시 코드 값 강제 형변환이나 유실이 발생하지 않는지 검증함
def test_comparison_does_not_union_or_coerce_codes():
    a=b'{"r":{"totalCount":100,"items":[{"code":"001"},{"code":"002"}]}}'
    b=b'<r><totalCount>100</totalCount><items><item><code>001</code></item><item><code>002</code></item></items></r>'
    assert compare_json_xml(a,b)['equivalent']
    assert not compare_json_xml(a,b.replace(b'002',b'2'))['equivalent']
    assert not compare_json_xml(a,b.replace(b'<item><code>002</code></item>',b''))['equivalent']


# 데이터 라운드트립 시 샘플 데이터 누출 방지 및 포인터 유효성을 검증함
def test_other_data_roundtrip_no_case_leak_and_no_fake_contract():
    result=generate([('inventory.json','json',b'{"items":[{"part":"a|b","qty":0},{"qty":2}]}')],'Inventory')
    assert result['validation']['reverse_extraction']=='PASS'
    assert result['validation']['xsd'].startswith('PASS')
    for text in (result['markdown'],result['xml'].decode(),result['jsonld']):
        assert 'cheongju' not in text and '태양광' not in text and 'aimsService' not in text
        assert '{{' not in text and 'example.com' not in text
    model=result['canonical']
    assert model['structure']['api_specification']['base_url'] is None
    assert model['quality']['metrics']['accuracy']['score'] is None
    assert model['statistics']['total_records']==2
    for entry in model['canonicalItems']:
        assert pointer(model,entry['bindingPath'])==entry['value']
    bad=copy.deepcopy(model);bad['canonicalItems'][0]['value']='bad'
    with pytest.raises(ValueError): validate(bad)


# 템플릿 별칭 바인딩 및 알 수 없는 경로에 대한 예외 처리를 검증함
def test_template_aliases_and_unknown_paths():
    contract=Contract()
    model={'dataset':{'contact_point':{'name':'x'}},'canonicalItems':[]}
    assert bind_text('{{dataset.contact.name}} / {{dataset.contact_point.name}}',model,contract)=='x / x'
    with pytest.raises(ValueError,match='해석 불가능'):
        bind_text('{{dataset.invented}}',model,contract)


# 미지원 파일 확장자 입력 시 적절한 예외가 발생하는지 검증함
def test_unsupported_extension():
    with pytest.raises(ValueError,match='지원'):
        generate([('data.pdf','pdf',b'data')],'Unsupported')


# 반복되는 데이터 사전 행들이 실제 구조적 표(Table)로 파싱되는지 검증함
def test_repeated_dictionary_rows_are_real_tables():
    result=generate([('data.csv','csv',b'one,two\na,b\nc,d')],'Table')
    dictionary=next(b for b in result['document_model'] if b['kind']=='table' and b['rows'][0][0]=='컬럼 물리명')
    assert len(dictionary['rows'])==len(result['canonical']['fields'])+1
    assert not any(b.get('text','').startswith('|') for b in result['document_model'])
