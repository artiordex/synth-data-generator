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
import re
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree
from openpyxl import Workbook

from synthetic_api.application.services.ai_guide_document.binding import Contract,validate,pointer,canonical,finalize
from synthetic_api.application.services.ai_guide_document.profile import profile_bytes,compare_json_xml
from synthetic_api.application.services.ai_guide_document.service import generate,render
from synthetic_api.application.services.ai_guide_document.render import (
    bind_text, select_guide_profile, template_source, guide_outline,
    _semantic_section_key, _docx_remove_branch_sections, _hwpx_remove_branch,
    _hwpx_text, _docx_repeat_scope, _docx_scope_items,
)


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


# Canonical JSON Schema가 템플릿·표현 포맷보다 먼저 적용되는 최상위 계약인지 검증함
def test_canonical_json_schema_is_top_level_contract():
    contract=Contract()
    result=generate([('schema-check.json','json',b'{"items":[{"id":1}]}')],'Schema contract')
    assert contract.schema_path.name=='canonical-metadata.schema.json'
    assert contract.ontology_path.name=='ontology.ttl'
    assert 'urn:synthetic-data:ai-ready:v2:ontology' in result['jsonld']
    contract.validate_schema(result['canonical'])
    invalid=copy.deepcopy(result['canonical'])
    invalid.pop('schemaVersion')
    with pytest.raises(ValueError,match='Canonical JSON Schema 검증 실패'):
        validate(invalid,contract)


# 미지원 파일 확장자 입력 시 적절한 예외가 발생하는지 검증함
def test_xml_exchange_output_validates_against_machine_schema():
    result = generate([('exchange.xml.json', 'json', b'{"items":[{"id":1,"status":"ok"}]}')], 'XML exchange')
    schema_path = (Path(__file__).resolve().parents[1] / 'src' / 'synthetic_api' /
                   'data' / 'ai_guide' / 'templates' / 'ai_ready_metadata_schema.xsd')
    schema = etree.XMLSchema(file=str(schema_path))
    document = etree.fromstring(result['xml'])
    assert schema.validate(document)
    namespace = {'m': 'urn:synthetic-data:ai-ready:v2:'}
    assert document.xpath('count(/m:aiReadyDataset/m:processing)', namespaces=namespace) == 1


def test_jsonld_exchange_contains_processing_graph_node():
    result = generate([('exchange.json', 'json', b'{"items":[{"id":1,"status":"ok"}]}')], 'JSON-LD exchange')
    document = json.loads(result['jsonld'])
    graph = document['@graph'][0]
    assert document['@context']['processing'] == 'aig:processing'
    assert graph['processing']['@type'] == 'aig:Processing'
    assert 'integration' in graph['processing']


def test_exchange_processing_values_are_serialized_without_markers():
    result = generate([('exchange.processing.json', 'json', b'{"items":[{"id":1,"status":"ok"}]}')], 'Processing exchange')
    assert '{{' not in result['xml'].decode('utf-8')
    assert '{{' not in result['jsonld']


def test_unsupported_extension():
    with pytest.raises(ValueError,match='지원'):
        generate([('data.pdf','pdf',b'data')],'Unsupported')


# 반복되는 데이터 사전 행들이 실제 구조적 표(Table)로 파싱되는지 검증함
def test_repeated_dictionary_rows_are_real_tables():
    result=generate([('data.csv','csv',b'one,two\na,b\nc,d')],'Table')
    dictionary=next(b for b in result['document_model'] if b['kind']=='table' and b['rows'][0][0]=='번호')
    assert len(dictionary['rows'])==len(result['canonical']['fields'])+1
    assert not any(b.get('text','').startswith('|') for b in result['document_model'])


def test_render_semantic_outline_has_processing_and_ai_sections():
    sections, toc = guide_outline('file')
    assert list(sections['management']['children']) == [
        'sources_collection', 'integration', 'cleaning', 'derivation_transformation',
        'missing_outlier_processing', 'processing_validation', 'quality',
        'quality_flags', 'metadata_interoperability', 'lineage_changes',
        'privacy_deidentification', 'rights_conditions',
    ]
    assert list(sections['ai']['children']) == [
        'ai_summary', 'tasks', 'training_info', 'recommended_features',
        'bias_representativeness', 'limitations', 'corrected_estimated_usage',
        'usage_risks',
    ]
    assert sections['ai']['number'] == '4'
    assert _semantic_section_key('3. 파일데이터 제공 명세 (파일이 있을 경우)') == 'file_distribution'
    assert _semantic_section_key('4. OpenAPI 서비스 명세 (API가 있을 경우)') == 'api_service'
    assert toc[0]['line'].startswith('1. ')


def test_docx_semantic_branch_removal_does_not_depend_on_chapter_number():
    from docx import Document

    doc = Document()
    for text in (
        '10. 공통 시작',
        '11. 파일데이터 제공 명세 (파일이 있을 경우)',
        '12. OpenAPI 서비스 명세 (API가 있을 경우)',
        '13. 공통 종료',
    ):
        paragraph = doc.add_paragraph(text)
        paragraph.style = 'Heading 2'
    _docx_remove_branch_sections(doc, 'file')
    text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
    assert '파일데이터 제공 명세' in text
    assert 'OpenAPI 서비스 명세' not in text


def test_hwpx_semantic_branch_removal_does_not_depend_on_chapter_number():
    template = Path(__file__).resolve().parents[1] / 'src' / 'synthetic_api' / 'data' / 'ai_guide' / 'templates' / 'ai_ready_public_data_guide_template.hwpx'
    with ZipFile(template) as archive:
        root = etree.fromstring(archive.read('Contents/section0.xml'))
    _hwpx_remove_branch(root, 'api')
    rendered = _hwpx_text(root)
    assert 'OpenAPI 서비스 명세' in rendered
    assert '파일데이터 제공 명세' not in rendered


def test_render_conditional_processing_sections_follow_observed_collections():
    plain = generate([('plain.csv', 'csv', b'id,value\n1,10\n2,20')], 'Plain', human_format='md')
    plain_headings = [block['text'] for block in plain['document_model'] if block['kind'] == 'heading']
    assert not any('데이터 연계·결합' in heading for heading in plain_headings)
    assert not any('품질 플래그 및 값 구분' in heading for heading in plain_headings)

    observed = generate(
        [('observed.csv', 'csv', b'timestamp,value,quality_flag\n2025-01-01,1,Y\n,2,N')],
        'Observed',
        human_format='md',
    )
    observed_headings = [block['text'] for block in observed['document_model'] if block['kind'] == 'heading']
    assert any('데이터 파생·변환' in heading for heading in observed_headings)
    assert any('결측·이상값 처리' in heading for heading in observed_headings)
    assert any('품질 플래그 및 값 구분' in heading for heading in observed_headings)
    assert '\ue000AI_GUIDE_OMIT\ue001' not in observed['markdown']


def test_processing_repeat_scopes_and_graceful_office_fallback():
    assert _docx_repeat_scope({'description', 'method', 'join_type'}) == 'integrations'
    assert _docx_repeat_scope({'field_id', 'field_name', 'derivation_type', 'formula_or_rule'}) == 'derivedFields'
    assert _docx_repeat_scope({'target_field_ids', 'detected_missing_count', 'method_description'}) == 'missingValueRules'
    assert _docx_repeat_scope({'detection_method', 'action', 'replacement_method'}) == 'outlierRules'
    assert _docx_repeat_scope({'flag_field', 'description', 'target_fields'}) == 'qualityFlags'
    assert _docx_repeat_scope({'field_id', 'field_name', 'reason'}) == 'aiRecommendedFeatures'
    model = {
        'integrations': [{'description': '기관 확인 결합', 'method': None, 'join_type': None}],
        'derivedFields': [{'field_id': 'f1'}],
        'missingValueRules': [], 'outlierRules': [], 'qualityFlags': [],
        'aiRecommendedFeatures': [{'field_id': 'f1'}],
    }
    assert _docx_scope_items(model, 'integrations')[0] == model['integrations']
    assert _docx_scope_items(model, 'derivedFields')[0] == model['derivedFields']
    # A template without a matching prototype simply returns an empty scope;
    # the office renderer can therefore preserve the user's existing layout.
    assert _docx_scope_items(model, 'qualityFlags')[0] == []


def test_solar_pipeline_scenario_uses_generic_processing_contract():
    # This is a fixture scenario only.  Production code has no domain-specific
    # branch; an institution-confirmed processing contract is injected here to
    # verify that integration, derivation, imputation and quality flags bind.
    result = generate([
        ('generation.csv', 'csv', b'observation_time,generation_value\n2025-01-01T00:00,10\n2025-01-01T01:00,12'),
        ('weather.csv', 'csv', b'observation_time,irradiance,cloud_cover\n2025-01-01T00:00,100,20\n2025-01-01T01:00,,30'),
    ], 'Solar fixture', human_format='md')
    contract = Contract()
    model = result['canonical']
    field_ids = {field['name']: field['field_id'] for field in model['fields']}
    generation_id = field_ids['/*/generation_value']
    irradiance_id = field_ids['/*/irradiance']
    flag_id = field_ids.get('/*/cloud_cover')
    model['processing']['integration'].update(
        is_integrated=True,
        description='외부 기상 관측 원천과 시간 키를 기준으로 결합',
        method='기관 확인 시간키 결합',
        join_type='temporal',
        join_keys=['observation_time'],
        source_dataset_ids=[entry['sha256'] for entry in model['analysis']['sources']],
        limitations=None,
    )
    model['processing']['derived_fields']=[{
        'field_id': generation_id,
        'field_name': 'generation_value',
        'derivation_type': 'derived',
        'source_fields': [generation_id, irradiance_id],
        'description': '기관 확인 시간 단위 파생값',
        'method': '기관 제공 파생 규칙',
        'formula_or_rule': '기관 확인 필요',
        'aggregation': None, 'window': '1 hour', 'unit': None,
        'parameters': {}, 'fallback_rule': None, 'reproducible': None,
        'confidence': None, 'notes': '원천 계약 확인 전 확정하지 않음',
    }]
    model['processing']['missing_value_processing']=[{
        'target_field_ids': [irradiance_id],
        'detected_missing_count': 1,
        'detected_missing_ratio': 0.5,
        'method': 'linear_interpolation',
        'method_description': '기관 승인 선형 보간',
        'steps': [], 'grouping_keys': ['observation_time'], 'temporal_window': '1 hour',
        'parameters': {}, 'fallback_method': None, 'clipping_rule': None,
        'affected_record_count': 1, 'quality_flag_field': flag_id,
        'original_value_preserved': True, 'limitations': None,
    }]
    model['processing']['quality_flags']=[{
        'flag_field': flag_id,
        'description': '보정 여부 플래그',
        'target_fields': [irradiance_id],
        'values': [{'code': 'Y', 'name': '보정', 'meaning': '보간값', 'value_origin': 'observed'},
                   {'code': 'N', 'name': '원천', 'meaning': '관측값', 'value_origin': 'observed'}],
        'meaning': '기관 코드 정의 확인',
    }]
    model['ai']['recommended_features']=[
        {'field_id': irradiance_id, 'field_name': 'irradiance', 'reason': '시간 정렬 후 입력 후보'},
        {'field_id': field_ids['/*/cloud_cover'], 'field_name': 'cloud_cover', 'reason': '품질 플래그와 함께 검토'},
    ]
    finalized = finalize(model, contract=contract)
    rendered = render(finalized, contract, human_format='md')
    assert 'linear_interpolation' in rendered['markdown']
    assert '품질 플래그' in rendered['markdown']
    assert any(item['bindingPath'].startswith('/processing/') for item in finalized['canonicalItems'])


FILE_CHAPTERS = [
    '데이터셋 개요', '데이터 관리 메타데이터', '데이터셋 구성 및 데이터사전',
    '데이터 구축·수집·가공 방법', '데이터 계보 및 변경이력', '데이터 표준화 및 상호운용성',
    '데이터 이용·배포·접근', '데이터 품질', 'AI 활용성', '데이터 관리체계',
    '기관 확인 및 발간 전 점검',
]
API_CHAPTERS = [
    'API 데이터셋 개요', 'API 관리 메타데이터', 'API 서비스 및 접근 명세', 'API 기능 목록',
    'API 기능별 상세 명세', 'API 데이터 구조 및 스키마', 'API 데이터 품질', 'API 성능·운영',
    'API 오류 및 예외', '데이터 표준화 및 상호운용성', 'AI 활용성',
    'AI Agent·기계 접근 고려사항', 'API 생애주기 및 변경이력', 'API 관리체계',
    '기관 확인 및 발간 전 점검',
]


@pytest.mark.parametrize('category,name,fmt,raw,chapters,appendices', [
    ('file','table.csv','csv',b'id,value\n1,0\n2,3',FILE_CHAPTERS,'ABC'),
    ('api','response.json','json',b'{"items":[{"id":1},{"id":2}]}',API_CHAPTERS,'ABCDE'),
])
def test_unified_guide_profiles_have_exact_chapters_and_shared_assets(
        category,name,fmt,raw,chapters,appendices):
    result=generate([(name,fmt,raw)],'Unified regression')
    headings=[b['text'] for b in result['document_model'] if b['kind']=='heading']
    sections,_=guide_outline(category)
    expected_top=[f"{section['number']}. {section['title']}"
                  for section in sections.values()]
    actual_top=[h for h in headings if re.match(r'^\d+\.\s',h)]
    assert actual_top==expected_top
    assert not any(h.startswith('[') for h in headings)
    assert headings[0].startswith('AI')
    assert '{{' not in result['markdown']
    assert result['validation']['reverse_extraction']=='PASS'
    assert result['validation']['xsd'].startswith('PASS')
    assert result['template_index']['profile']==category
    assert result['template_index']['source_md']=='ai_ready_public_data_guide_template.md'
    assert result['template_index']['source_docx']=='ai_ready_public_data_guide_template.docx'
    assert result['template_index']['normalized_docx']=='ai_ready_public_data_guide_template.docx'
    if category=='file':
        assert 'file_distribution' in sections
        child=sections['file_distribution']['children']['column_definition']
        assert f"{child['number']} {child['title']}" in headings
        assert 'api_service' not in sections
    else:
        assert 'api_service' in sections
        child=sections['api_service']['children']['functions_endpoints']
        assert f"{child['number']} {child['title']}" in headings
        assert 'file_distribution' not in sections


@pytest.mark.parametrize('category',[None,'','unknown','FILE'])
def test_unified_guide_rejects_unconfirmed_category(category):
    with pytest.raises(ValueError,match='file 또는 api'):
        template_source(Contract(),category)


@pytest.mark.parametrize('source',[
    '{{#guide.file}}file{{/guide.file}}',
    '{{#guide.file}}file{{/guide.api}}{{#guide.api}}api{{/guide.api}}',
    '{{#guide.file}}one{{/guide.file}}{{#guide.file}}two{{/guide.file}}{{#guide.api}}api{{/guide.api}}',
    '{{#guide.file}}file{{/guide.file}}{{#guide.api}}api{{/guide.api}}{{#guide.other}}bad{{/guide.other}}',
])
def test_unified_guide_rejects_bad_profile_markers(source):
    with pytest.raises(ValueError,match='분기'):
        select_guide_profile(source,'file')


def test_unified_api_operation_numbering_and_nested_contract_paths():
    contract=Contract()
    profile=profile_bytes(b'{"items":[{"id":1}]}','json','response.json')
    model=canonical([profile],'Operations',contract)
    operation_template=next(v for v in contract.template['structure']['api_specification']['operations']
                            if isinstance(v,dict))
    operations=[]
    for i in (1,2):
        op=contract.empty(operation_template)
        op.update(operation_id=f'op{i}',operation_name=f'Function {i}',endpoint_path=f'/items/{i}',
                  http_method='GET',description=f'Contract {i}',data_formats=['JSON'])
        op['sample_messages'].update(xml_sample=f'<r><id>{i}</id></r>',json_sample=json.dumps({'id':i}))
        for kind in ('request_parameters','response_parameters'):
            prototype=next(v for v in operation_template[kind] if isinstance(v,dict))
            param=contract.empty(prototype)
            param.update(param_name='id',name_ko='식별자',data_type='integer',required=True,
                         sample_value=i if kind=='request_parameters' else i+10,
                         description='Request identifier' if kind=='request_parameters' else 'Response identifier')
            if kind=='request_parameters': param['location']='QUERY'
            else: param['path']='/items/*/id'
            op[kind]=[param]
        operations.append(op)
    model['structure']['api_specification']['operations']=operations
    result=render(finalize(model),contract)
    headings=[b['text'] for b in result['document_model'] if b['kind']=='heading']
    sections,_=guide_outline('api')
    child=sections['api_service']['children']['functions_endpoints']
    assert f"{child['number']} {child['title']}" in headings
    assert '기능 계약 미제공' not in result['markdown']
    assert '<r><id>1</id></r>' in result['markdown']
    assert '<r><id>2</id></r>' in result['markdown']
    assert '| Function 1 |' in result['markdown'] and '| Function 2 |' in result['markdown']
    assert result['validation']['reverse_extraction']=='PASS'
    root=etree.fromstring(result['xml'])
    ns={'m':'urn:synthetic-data:ai-ready:v2:'}
    assert root.xpath('//m:requestParameters/m:param/@sampleValue',namespaces=ns)==['1','2']
    assert root.xpath('//m:responseParameters/m:param/@sampleValue',namespaces=ns)==['11','12']
    assert root.xpath('//m:requestParameters/m:param/m:description/text()',namespaces=ns)==[
        'Request identifier','Request identifier']
    assert root.xpath('//m:responseParameters/m:param/m:description/text()',namespaces=ns)==[
        'Response identifier','Response identifier']


def test_inverse_collection_sections_and_number_scope():
    contract=Contract()
    model={'fields':[],'canonicalItems':[]}
    text='{{#fields}}{{@number}} {{name}}{{/fields}}{{^fields}}미확정{{/fields}}'
    assert bind_text(text,model,contract)=='미확정'
    model['fields']=[{'name':'a'},{'name':'b'}]
    assert bind_text(text,model,contract)=='1 a2 b'
    with pytest.raises(ValueError,match='반복 블록'):
        bind_text('{{@number}}',model,contract)


@pytest.mark.parametrize('human_format', ['md','docx','hwpx'])
def test_user_input_precedes_inference_and_all_human_formats_are_generated(human_format):
    seen={}
    def enrich(model):
        seen['publisher']=model['dataset']['publisher']
        return {
            'dataset_purpose':'기관 입력 이후 작성한 데이터 개방 목적 초안',
            'ai_purpose':'관측 필드 기반 분류 모델 활용 검토',
            'fields':[{'path':'/*/id','english_name':'itemId','name_ko':'식별자','description':'항목 식별자 초안'}],
        }
    result=generate(
        [('sample.json','json',b'[{"id":1,"name":"a"}]')],
        '기관 데이터 가이드',
        user_metadata={'publisher':'테스트 기관','license':'공공누리 제1유형'},
        field_annotations={'/*/name':{'english_name':'itemName','label':'명칭','description':'기관 확인 설명','unit':'해당 없음','codes':'해당 없음'}},
        enricher=enrich,
        human_format=human_format,
    )
    assert seen['publisher']=='테스트 기관'
    model=result['canonical']
    statuses={entry['bindingPath']:entry['status'] for entry in model['canonicalItems']}
    assert statuses['/dataset/publisher']=='USER_CONFIRMED'
    assert statuses['/fields/3/description']=='USER_CONFIRMED'
    assert statuses['/fields/2/description']=='AUTO_INFERRED'
    assert statuses['/fields/2/name']=='AUTO_INFERRED'
    assert statuses['/fields/3/name']=='USER_CONFIRMED'
    assert {field['path']:field['name'] for field in model['fields']}['/*/id']=='itemId'
    assert {field['path']:field['name'] for field in model['fields']}['/*/name']=='itemName'
    assert json.loads(json.dumps(model,ensure_ascii=False))['dataset']['publisher']=='테스트 기관'
    assert '테스트 기관' in result['xml'].decode('utf-8')
    assert '테스트 기관' in result['jsonld']
    assert '테스트 기관' in result['markdown']
    if human_format=='md':
        assert result['human_document'].decode('utf-8')==result['markdown']
    else:
        with ZipFile(io.BytesIO(result['human_document'])) as package:
            assert package.testzip() is None
            assert ('word/document.xml' if human_format=='docx' else
                    'Contents/section0.xml' if human_format=='hwpx' else 'content.xml') in package.namelist()


# DOCX 및 HWPX 가이드 문서 렌더링 시 목차의 들여쓰기, 점선 채움선, 페이지 번호 무결성을 검증함
def test_docx_and_hwpx_table_of_contents_formatting():
    from docx import Document
    result = generate(
        [('sample.json', 'json', b'[{"id":1,"name":"a"}]')],
        '목차 테스트 가이드',
        user_metadata={'publisher': '식약처'},
        human_format='docx',
    )
    # DOCX TOC 검증
    doc = Document(io.BytesIO(result['docx']))
    toc_p = doc.paragraphs[22]
    assert len(toc_p.text) > 500, 'DOCX 목차 문단이 누락되거나 축약되었습니다.'
    assert '1. 데이터셋 개요' in toc_p.text
    assert '    1.1' in toc_p.text
    assert '....' in toc_p.text
    assert '{{' not in toc_p.text

    # HWPX TOC 검증
    hwpx_result = generate(
        [('sample.json', 'json', b'[{"id":1,"name":"a"}]')],
        '목차 테스트 가이드',
        user_metadata={'publisher': '식약처'},
        human_format='hwpx',
    )
    with ZipFile(io.BytesIO(hwpx_result['human_document'])) as package:
        assert package.testzip() is None
        sec0 = package.read('Contents/section0.xml').decode('utf-8')
    toc_lines = [
        ''.join(re.findall(r'<hp:t>(.*?)</hp:t>', p))
        for p in re.findall(r'<hp:p\b[^>]*>.*?</hp:p>', sec0)
        if '....' in ''.join(re.findall(r'<hp:t>(.*?)</hp:t>', p))
    ]
    assert len(toc_lines) == 46
    assert '1. 데이터셋 개요' in toc_lines[0]
    assert '    1.1' in toc_lines[1]
    assert '6. 참고 기준' in toc_lines[-3]
    assert '{{toc.' not in sec0
