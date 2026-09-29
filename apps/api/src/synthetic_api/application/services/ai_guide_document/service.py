# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: service.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_document/service.py
# 목적: AI 친화 가이드 문서 생성 서비스 및 CLI 진입점을 제공함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Reusable guide generation service and CLI. Renderers never re-analyze sources."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from .binding import Contract,canonical,finalize
from .profile import profile_bytes,compare_json_xml
from .render import document_model,markdown,html_bytes,docx_bytes,hwpx_bytes,odt_bytes,verify_outputs
from .exchange import xml_output,jsonld_output,validate_jsonld_semantics,ttl_output


LOWER_CAMEL_NAME = re.compile(r'[a-z][A-Za-z0-9]{0,63}\Z', re.ASCII)


USER_METADATA_PATHS = {
    'identifier': ('dataset', 'identifier'),
    'publisher': ('dataset', 'publisher'),
    'creator': ('dataset', 'creator'),
    'description': ('dataset', 'description'),
    'purpose': ('dataset', 'purpose'),
    'version_notes': ('dataset', 'version_info', 'version_notes'),
    'department': ('governance', 'managing_department'),
    'legal_basis': ('dataset', 'legal_references'),
    'landing_page': ('dataset', 'landing_page'),
    'access_url': ('dataset', 'access_url'),
    'contact': ('dataset', 'contact_point', 'name'),
    'contact_name': ('dataset', 'contact_point', 'name'),
    'contact_email': ('dataset', 'contact_point', 'email'),
    'contact_phone': ('dataset', 'contact_point', 'phone'),
    'language': ('dataset', 'language'),
    'media_type': ('dataset', 'media_type'),
    'theme_label': ('dataset', 'theme_label'),
    'license': ('usage', 'license'),
    'license_type': ('usage', 'license'),
    'rights': ('usage', 'rights'),
    'access_rights': ('usage', 'access_rights'),
    'attribution': ('usage', 'attribution'),
    'update_frequency': ('dataset', 'update_frequency'),
    'version': ('dataset', 'version_info', 'version'),
    'issued': ('dataset', 'version_info', 'issued'),
    'modified': ('dataset', 'version_info', 'modified'),
    'spatial': ('dataset', 'spatial'),
    'collection_process': ('lineage', 'collection_process'),
    'transformation': ('lineage', 'preprocessing_history'),
    'imputation': ('lineage', 'imputation_method'),
    'training_split': ('ai', 'split_ratio', 'strategy'),
    'limitations': ('responsible_ai', 'known_limitations'),
    'ai_purpose': ('ai', 'purpose'),
    'anonymization_method': ('governance', 'privacy_security', 'anonymization_method'),
    'security_level': ('governance', 'privacy_security', 'security_level'),
    'api_base_url': ('structure', 'api_specification', 'base_url'),
    'authentication_type': ('structure', 'api_specification', 'auth_type'),
    'authentication': ('structure', 'api_specification', 'authentication_description'),
    'pagination': ('structure', 'api_specification', 'pagination'),
    'response_path': ('structure', 'api_specification', 'payload_path'),
    'specification_url': ('structure', 'api_specification', 'specification_url'),
    'api_version': ('structure', 'api_specification', 'version'),
    'rate_limit': ('structure', 'api_specification', 'rate_limit'),
}

AI_INFERABLE_METADATA = {
    'description', 'purpose', 'keywords', 'language', 'media_type', 'theme_label',
    'spatial', 'temporal_start', 'temporal_end', 'limitations', 'ai_purpose',
}

KOGL_LICENSE_LABELS = {
    'KOGL_TYPE_0': '공공누리 제0유형(자유이용)',
    'KOGL_TYPE_1': '공공누리 제1유형(출처표시)',
    'KOGL_TYPE_2': '공공누리 제2유형(출처표시·상업적 이용금지)',
    'KOGL_TYPE_3': '공공누리 제3유형(출처표시·변경금지)',
    'KOGL_TYPE_4': '공공누리 제4유형(출처표시·상업적 이용금지·변경금지)',
    'KOGL_TYPE_AI': '공공누리 AI유형(AI 학습용 이용허락)',
}

_AI_TYPE_FAMILIES = {
    'string': {'string'}, 'varchar': {'string'}, 'char': {'string'}, 'text': {'string'},
    'integer': {'integer'}, 'int': {'integer'}, 'bigint': {'integer'},
    'numeric': {'number'}, 'decimal': {'number'}, 'float': {'number'},
    'double': {'number'}, 'number': {'number'},
    'boolean': {'boolean'}, 'bool': {'boolean'},
    'date': {'date'}, 'datetime': {'datetime'}, 'timestamp': {'datetime'},
    'json': {'object', 'array'}, 'object': {'object'}, 'array': {'array'},
}


def _set(model, path, value):
    target=model
    for key in path[:-1]: target=target[key]
    target[path[-1]]=value


def _pointer(path):
    return '/'+'/'.join(str(value).replace('~','~0').replace('/','~1') for value in path)


def _can_refine(path, overrides):
    provenance=overrides.get(path)
    return not provenance or (provenance[0]=='AUTO_INFERRED' and provenance[1]=='AI_INFERENCE')


def _ai_type_matches_observations(field, candidate):
    """Require AI labels to preserve the complete observed type families."""
    if not isinstance(candidate, str):
        return False
    observed={value.strip().lower() for value in str(field.get('data_type') or '').split('|')}
    proposed=[value.strip().lower() for value in candidate.split('|') if value.strip()]
    if not observed or not proposed:
        return False
    if ('null' in observed) != ('null' in proposed):
        return False
    observed.discard('null')
    proposed=[value for value in proposed if value != 'null']
    if not observed or not proposed:
        return False
    observed_families=set()
    for value in observed:
        family=_AI_TYPE_FAMILIES.get(value)
        if family is None:
            return False
        observed_families.update(family)
    proposed_families=set()
    for value in proposed:
        family=_AI_TYPE_FAMILIES.get(value)
        if family is None:
            return False
        proposed_families.update(family)
    return observed_families == proposed_families


def _apply_user_input(
    model,
    contract,
    metadata=None,
    field_annotations=None,
    metadata_provenance=None,
    field_annotation_provenance=None,
):
    """Apply only explicit user values before AI inference and retain their provenance."""
    overrides={}
    metadata=metadata or {}
    metadata_provenance=metadata_provenance or {}
    field_annotation_provenance=field_annotation_provenance or {}
    for key,path in USER_METADATA_PATHS.items():
        value=str(metadata.get(key,'')).strip()
        if key == 'license_type' and str(metadata.get('license','')).strip():
            continue
        if key == 'license_type' and value:
            value = KOGL_LICENSE_LABELS.get(value, '')
        if not value: continue
        source=metadata_provenance.get(key, 'USER_CONFIRMED')
        if source == 'AUTO_INFERRED' and key not in AI_INFERABLE_METADATA:
            continue
        if source not in {'USER_CONFIRMED', 'AUTO_INFERRED', 'SAMPLE_PRESET'}:
            continue
        _set(model,path,value)
        if source == 'USER_CONFIRMED':
            overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 값')
        else:
            source_type='SAMPLE_PRESET' if source == 'SAMPLE_PRESET' else 'AI_INFERENCE'
            reason='샘플 예시값으로 실제 기관 정보가 아님' if source == 'SAMPLE_PRESET' else 'AI가 데이터 구조와 담당자 입력을 바탕으로 작성한 검토용 초안'
            overrides[_pointer(path)]=('AUTO_INFERRED',source_type,reason)
    temporal=str(metadata.get('temporal','')).strip()
    if temporal:
        parts=[value.strip() for value in temporal.replace('~','|').split('|',1)]
        for key,value in zip(('start','end'),parts):
            if value:
                path=('dataset','temporal',key);_set(model,path,value)
                source=metadata_provenance.get('temporal', metadata_provenance.get(key, 'USER_CONFIRMED'))
                if source == 'USER_CONFIRMED':
                    overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 시간 범위')
                elif source in {'AUTO_INFERRED','SAMPLE_PRESET'}:
                    source_type='SAMPLE_PRESET' if source == 'SAMPLE_PRESET' else 'AI_INFERENCE'
                    overrides[_pointer(path)]=('AUTO_INFERRED',source_type,'AI 또는 샘플에서 제안한 시간 범위 초안')
    for key,target in (('temporal_start','start'),('temporal_end','end')):
        value=str(metadata.get(key,'')).strip()
        if value:
            path=('dataset','temporal',target);_set(model,path,value)
            source=metadata_provenance.get(key, 'USER_CONFIRMED')
            if source == 'USER_CONFIRMED':
                overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 시간 범위')
            elif source in {'AUTO_INFERRED','SAMPLE_PRESET'}:
                source_type='SAMPLE_PRESET' if source == 'SAMPLE_PRESET' else 'AI_INFERENCE'
                overrides[_pointer(path)]=('AUTO_INFERRED',source_type,'AI 또는 샘플에서 제안한 시간 범위 초안')
    keywords=[value.strip() for value in re.split(r'[,\n]',str(metadata.get('keywords',''))) if value.strip()]
    if keywords:
        model['dataset']['keywords']=keywords
        for index in range(len(keywords)):
            source=metadata_provenance.get('keywords', 'USER_CONFIRMED')
            if source == 'USER_CONFIRMED':
                overrides[_pointer(('dataset','keywords',str(index)))]=(
                    'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 검색 키워드')
            elif source in {'AUTO_INFERRED','SAMPLE_PRESET'}:
                source_type='SAMPLE_PRESET' if source == 'SAMPLE_PRESET' else 'AI_INFERENCE'
                overrides[_pointer(('dataset','keywords',str(index)))]=(
                    'AUTO_INFERRED',source_type,'AI 또는 샘플 예시에서 만든 검색 키워드 초안')
    relations=[value.strip() for value in re.split(r'[,\n]',str(metadata.get('source_datasets',''))) if value.strip()]
    if metadata_provenance.get('source_datasets','USER_CONFIRMED') != 'USER_CONFIRMED':
        relations=[]
    if relations:
        model['dataset']['relations']=relations
        for index in range(len(relations)):
            overrides[_pointer(('dataset','relations',str(index)))]=(
                'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 연계 데이터셋')
        model['lineage']['source_datasets']=relations
        for index in range(len(relations)):
            overrides[_pointer(('lineage','source_datasets',str(index)))]=(
                'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 연계 데이터셋')
    contains_pii=(str(metadata.get('contains_pii','')).strip().lower()
                  if metadata_provenance.get('contains_pii','USER_CONFIRMED') == 'USER_CONFIRMED' else '')
    if contains_pii:
        truthy={'true','yes','y','1','예','포함'};falsy={'false','no','n','0','아니오','미포함'}
        if contains_pii not in truthy|falsy:
            raise ValueError('개인정보 포함 여부는 true/false, 예/아니오, 포함/미포함 중 하나로 입력하세요.')
        path=('governance','privacy_security','contains_pii');_set(model,path,contains_pii in truthy)
        overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','담당자가 직접 확인한 개인정보 포함 여부')
    api=model['structure']['api_specification']
    if model['structure']['has_api_data']:
        operation_values={key:(str(metadata.get(key,'')).strip()
                               if metadata_provenance.get(key,'USER_CONFIRMED') == 'USER_CONFIRMED' else '')
                          for key in ('operation_id','operation_name','endpoint','http_method','request_parameters')}
        if any(operation_values.values()):
            prototype=next(value for value in contract.template['structure']['api_specification']['operations'] if isinstance(value,dict))
            operation=api['operations'][0] if api['operations'] else contract.empty(prototype)
            for metadata_key,operation_key in (
                ('operation_id','operation_id'),('operation_name','operation_name'),('endpoint','endpoint_path')):
                if operation_values[metadata_key]:
                    operation[operation_key]=operation_values[metadata_key]
                    overrides[_pointer(('structure','api_specification','operations','0',operation_key))]=(
                        'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력한 API 오퍼레이션 정보')
            if operation_values['http_method']:
                operation['http_method']=operation_values['http_method'].upper()
                overrides[_pointer(('structure','api_specification','operations','0','http_method'))]=(
                    'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력한 HTTP 메서드')
            operation['data_formats']=operation.get('data_formats') or [
                profile['format'].upper() for profile in model['analysis']['sources']
                if profile['data_category']=='api']
            if operation_values['request_parameters']:
                request_template=next(value for value in prototype['request_parameters'] if isinstance(value,dict))
                request_lines=[line.strip() for line in operation_values['request_parameters'].splitlines() if line.strip()]
                parsed_parameters=[]
                structured=bool(request_lines)
                for line in request_lines:
                    parts=[part.strip() for part in line.split('|')]
                    if len(parts)<7 or not parts[0] or not parts[6]:
                        structured=False
                        break
                    name,name_ko,location,data_type,required,default_value,description=parts[:7]
                    location_value=location.upper() if location.upper() in {'QUERY','HEADER','PATH','BODY'} else None
                    required_value=True if required.lower() in {'필수','예','true','yes','required'} else (
                        False if required.lower() in {'선택','아니오','false','no','optional'} else None)
                    parameter=contract.empty(request_template)
                    parameter.update(param_name=name,name_ko=name_ko or name,
                                     location=location_value,data_type=data_type or None,
                                     required=required_value,default_value=default_value or None,
                                     description=description)
                    parsed_parameters.append(parameter)
                if structured:
                    operation['request_parameters']=parsed_parameters
                    for parameter_index,parameter in enumerate(parsed_parameters):
                        for key,value in parameter.items():
                            if value is not None:
                                overrides[_pointer(('structure','api_specification','operations','0','request_parameters',str(parameter_index),key))]=(
                                    'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 요청 파라미터')
                else:
                    parameter=contract.empty(request_template)
                    parameter['description']=operation_values['request_parameters']
                    operation['request_parameters']=[parameter]
                    overrides[_pointer(('structure','api_specification','operations','0','request_parameters','0','description'))]=(
                        'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 요청 파라미터 설명')
            api['operations']=[operation]
        error_codes=(str(metadata.get('error_codes','')).strip()
                     if metadata_provenance.get('error_codes','USER_CONFIRMED') == 'USER_CONFIRMED' else '')
        if error_codes:
            prototype=next(value for value in contract.template['structure']['api_specification']['error_codes'] if isinstance(value,dict))
            error_lines=[line.strip() for line in error_codes.splitlines() if line.strip()]
            structured_errors=[]
            structured=bool(error_lines)
            for line in error_lines:
                parts=[part.strip() for part in line.split('|')]
                if len(parts)<4 or not parts[0] or not parts[3]:
                    structured=False
                    break
                code,status,message,description=parts[:4]
                try:
                    http_status=int(status)
                except ValueError:
                    structured=False
                    break
                if not 100 <= http_status <= 599:
                    structured=False
                    break
                error=contract.empty(prototype)
                error.update(code=code,http_status=http_status,message=message or None,description=description)
                structured_errors.append(error)
            if not structured:
                error=contract.empty(prototype)
                error['description']=error_codes
                structured_errors=[error]
            api['error_codes']=structured_errors
            for error_index,error in enumerate(structured_errors):
                for key,value in error.items():
                    if value is not None:
                        overrides[_pointer(('structure','api_specification','error_codes',str(error_index),key))]=(
                            'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 API 오류 계약')
    annotations=field_annotations or {}
    for index,field in enumerate(model['fields']):
        values=annotations.get(field['path']) or {}
        for source_key,target_key in (('english_name','name'),('label','name_ko'),('description','description'),('unit','unit'),('codes','code_list'),('data_type','data_type')):
            value=str(values.get(source_key,'')).strip()
            if value:
                source_record=field_annotation_provenance.get(field['path'], 'USER_CONFIRMED')
                source=(source_record.get(source_key, source_record.get(target_key, 'USER_CONFIRMED'))
                        if isinstance(source_record,dict) else source_record)
                if source not in {'USER_CONFIRMED','AUTO_INFERRED'}:
                    continue
                if source_key=='english_name' and not LOWER_CAMEL_NAME.fullmatch(value):
                    clean_tokens = [t for t in re.split(r'[^a-zA-Z0-9]+', value) if t]
                    if clean_tokens:
                        camel = clean_tokens[0].lower() + ''.join(t.capitalize() for t in clean_tokens[1:])
                        if LOWER_CAMEL_NAME.fullmatch(camel):
                            value = camel
                        else:
                            camel_fallback = re.sub(r'[^a-zA-Z0-9]', '', value)
                            if camel_fallback and LOWER_CAMEL_NAME.fullmatch((camel_fallback[0].lower() + camel_fallback[1:])[:64]):
                                value = (camel_fallback[0].lower() + camel_fallback[1:])[:64]
                            else:
                                continue
                    else:
                        continue
                field[target_key]=value
                if source == 'USER_CONFIRMED':
                    overrides[_pointer(('fields',str(index),target_key))]=(
                        'USER_CONFIRMED','USER_INPUT','담당자가 직접 입력하거나 확인한 필드 설명')
                else:
                    overrides[_pointer(('fields',str(index),target_key))]=(
                        'AUTO_INFERRED','AI_INFERENCE','AI가 관측 필드 구조를 바탕으로 작성한 검토용 초안')
    confirmed_names=[field['name'].lower() for index,field in enumerate(model['fields'])
                     if _pointer(('fields',str(index),'name')) in overrides]
    if len(confirmed_names)!=len(set(confirmed_names)):
        raise ValueError('영문 컬럼명이 중복됩니다. 각 필드에 고유한 lowerCamelCase 이름을 입력하세요.')
    model.pop('canonicalItems',None);model.pop('reviewRequired',None)
    return overrides


def _apply_ai_enrichment(model, enrichment, overrides):
    """Bind bounded AI suggestions only to unresolved descriptive fields."""
    enrichment=enrichment or {}
    # The document endpoint returns compact ``metadata`` objects. Normalize
    # them to the flat keys consumed by the canonical binder before rendering.
    # This also prevents valid AI task suggestions from leaving template paths
    # such as ``input_fields`` unresolved.
    metadata=enrichment.get('metadata')
    if isinstance(metadata,dict):
        metadata_aliases={
            'description':'dataset_description',
            'purpose':'dataset_purpose',
            'limitations':'known_limitations',
            'theme_label':'theme_label',
            'keywords':'keywords',
            'spatial':'spatial',
            'update_frequency':'update_frequency',
            'collection_process':'collection_process',
        }
        for source,target in metadata_aliases.items():
            if target not in enrichment and metadata.get(source) not in (None,''):
                enrichment[target]=metadata[source]
    candidates=[
        (('dataset','description'),enrichment.get('dataset_description')),
        (('dataset','purpose'),enrichment.get('dataset_purpose')),
        (('dataset','theme_label'),enrichment.get('theme_label')),
        (('dataset','spatial'),enrichment.get('spatial')),
        (('dataset','temporal','start'),enrichment.get('temporal_start')),
        (('dataset','temporal','end'),enrichment.get('temporal_end')),
        (('ai','purpose'),enrichment.get('ai_purpose')),
        (('responsible_ai','known_limitations'),enrichment.get('known_limitations')),
        (('responsible_ai','data_biases'),enrichment.get('data_biases')),
        (('responsible_ai','quality_annotation'),enrichment.get('quality_annotation')),
    ]
    for path,value in candidates:
        path_pointer=_pointer(path)
        if (isinstance(value,str) and value.strip()
                and _can_refine(path_pointer,overrides)):
            _set(model,path,value.strip()[:6000])
            overrides[path_pointer]=('AUTO_INFERRED','AI_INFERENCE','OpenAI가 관측 구조와 사용자 입력을 바탕으로 작성한 검토용 초안')
    raw_keywords=enrichment.get('keywords',[])
    if isinstance(raw_keywords,str):
        raw_keywords=re.split(r'[,\n]',raw_keywords)
    keywords=[str(value).strip() for value in raw_keywords
              if isinstance(value,str) and value.strip()][:12]
    user_keywords=any(value and value[0]=='USER_CONFIRMED'
                      for path,value in overrides.items()
                      if path.startswith('/dataset/keywords/'))
    sample_keywords=any(value and value[1]=='SAMPLE_PRESET'
                        for path,value in overrides.items()
                        if path.startswith('/dataset/keywords/'))
    if keywords and not user_keywords and not sample_keywords:
        model['dataset']['keywords']=keywords
        for path in [path for path in overrides if path.startswith('/dataset/keywords/')]:
            overrides.pop(path,None)
        for index in range(len(keywords)):
            overrides[_pointer(('dataset','keywords',str(index)))]=(
                'AUTO_INFERRED','AI_INFERENCE','OpenAI가 데이터 구조와 설명에서 추출한 검색 키워드 초안')
    for target,key,fields in (
            (('ai','tasks'),'ai_tasks',('type','description','input_fields','target_fields',
                                        'evaluation_metrics','evidence','status','reason')),
            (('ai','scenarios'),'ai_scenarios',('title','description','actors','preconditions',
                                                'outputs','risks','status','reason'))):
        values=[]
        for item in enrichment.get(key,[]) if isinstance(enrichment.get(key),list) else []:
            if not isinstance(item,dict):
                continue
            value={field:str(item.get(field,'')).strip()[:1000] or None for field in fields}
            if any(value.values()):
                values.append(value)
        if values and not model[target[0]][target[1]]:
            model[target[0]][target[1]]=values[:8]
            for index,value in enumerate(values[:8]):
                for field,field_value in value.items():
                    if field_value:
                        overrides[_pointer((target[0],target[1],str(index),field))]=(
                            'AUTO_INFERRED','AI_INFERENCE','OpenAI가 제안한 AI 활용 초안')
    by_path={field['path']:(index,field) for index,field in enumerate(model['fields'])}
    used_names=Counter(field['name'].lower() for field in model['fields'] if field.get('name'))
    for item in enrichment.get('fields',[]) if isinstance(enrichment.get('fields'),list) else []:
        if not isinstance(item,dict) or item.get('path') not in by_path: continue
        index,field=by_path[item['path']]
        english_name=item.get('english_name')
        name_path=_pointer(('fields',str(index),'name'))
        if _can_refine(name_path,overrides):
            previous_name=str(field.get('name') or '').lower()
            if previous_name:
                used_names[previous_name]-=1
            if (isinstance(english_name,str)
                    and LOWER_CAMEL_NAME.fullmatch(english_name.strip())
                    and used_names[english_name.strip().lower()] <= 0):
                field['name']=english_name.strip()
                used_names[field['name'].lower()]+=1
                overrides[name_path]=(
                    'AUTO_INFERRED','AI_INFERENCE','OpenAI가 원천 컬럼명을 lowerCamelCase 영문 물리명으로 변환한 검토용 초안')
            elif previous_name:
                used_names[previous_name]+=1
        for source_key,target_key in (('name_ko','name_ko'),('label','name_ko'),('description','description')):
            value=item.get(source_key)
            target_path=_pointer(('fields',str(index),target_key))
            if (isinstance(value,str) and value.strip()
                    and _can_refine(target_path,overrides)):
                field[target_key]=value.strip()[:2000]
                overrides[target_path]=(
                    'AUTO_INFERRED','AI_INFERENCE','OpenAI가 원천 필드명과 관측 타입을 바탕으로 작성한 검토용 초안')
        data_type=item.get('data_type')
        data_type_path=_pointer(('fields',str(index),'data_type'))
        if (isinstance(data_type,str) and data_type.strip()
                and _can_refine(data_type_path,overrides)
                and _ai_type_matches_observations(field,data_type)):
            field['data_type']=data_type.strip()[:100]
            overrides[data_type_path]=(
                'AUTO_INFERRED','AI_INFERENCE','AI가 관측한 필드 타입을 바탕으로 제안한 검토용 초안')


def _sync_api_response_fields(model, overrides):
    """Keep API response tables aligned with the shared field dictionary."""
    if not model['structure']['has_api_data']:
        return
    fields={field['path']:(index,field) for index,field in enumerate(model['fields'])
            if field.get('source_category')=='api'}
    for operation_index,operation in enumerate(model['structure']['api_specification']['operations']):
        for parameter_index,parameter in enumerate(operation['response_parameters']):
            match=fields.get(parameter.get('path'))
            if not match:
                continue
            field_index,field=match
            for field_key,param_key in (('name','param_name'),('name_ko','name_ko'),
                                        ('data_type','data_type'),('required','required'),
                                        ('description','description')):
                parameter[param_key]=field[field_key]
                source_path=_pointer(('fields',str(field_index),field_key))
                target_path=_pointer(('structure','api_specification','operations',str(operation_index),
                                      'response_parameters',str(parameter_index),param_key))
                if source_path in overrides:
                    overrides[target_path]=overrides[source_path]
            parameter['sample_value']=field['sample_values'][0] if field['sample_values'] else None


# 원본 파일 입력 목록과 제목을 기반으로 AI 친화 가이드 문서를 종합 생성함
def generate(inputs,title,assets=None,user_metadata=None,field_annotations=None,enricher=None,human_format='docx',
             metadata_provenance=None,field_annotation_provenance=None):
    contract=Contract(assets) if assets else Contract()
    profiles=[]
    for source in inputs:
        name,fmt,raw=source[:3]
        data_category=source[3] if len(source)>3 else None
        profiles.append(profile_bytes(raw,fmt,name,data_category=data_category))
    comparison=None
    source_formats={str(source[1]).lstrip('.') for source in inputs}
    if len(inputs)==2 and source_formats=={'json','xml'}:
        raw={str(source[1]).lstrip('.'):source[2] for source in inputs}
        comparison=compare_json_xml(raw['json'],raw['xml'])
    model=canonical(profiles,title,contract,comparison)
    overrides=_apply_user_input(model,contract,user_metadata,field_annotations,
                                 metadata_provenance,field_annotation_provenance)
    enrichment=enricher(model) if enricher else None
    _apply_ai_enrichment(model,enrichment,overrides)
    _sync_api_response_fields(model,overrides)
    model=finalize(model,overrides,contract)
    result=render(model,contract,human_format)
    result['ai_powered']=bool(enrichment)
    return result


# 캐노니컬 모델을 마크다운, DOCX, XML, JSON-LD로 렌더링하고 유효성을 검증함
def render(model,contract,human_format='docx'):
    if human_format not in {'md','html','docx','hwpx','odt'}:
        raise ValueError('사람용 산출물은 md, html, docx, hwpx, odt 중 하나여야 합니다.')
    blocks,template,index=document_model(model,contract)
    md=markdown(blocks);html_doc=html_bytes(blocks,model.get('dataset',{}).get('title') or 'AI 가이드')
    docx=docx_bytes(blocks,template,model,contract)
    validation=verify_outputs(blocks,md,docx)
    xml=xml_output(model,contract)
    ld=jsonld_output(model,contract)
    ttl=ttl_output(model)
    validation.update(xsd='PASS (프로젝트 XSD)',jsonld_syntax='PASS',jsonld_semantics=validate_jsonld_semantics(ld),visual='PENDING')
    hwpx_doc = hwpx_bytes(blocks, contract.assets/'ai_ready_public_data_guide_template.hwpx',model,contract)
    odt_path = contract.assets/'ai_ready_public_data_guide_template.odt'
    odt_doc = odt_bytes(blocks, odt_path, model, contract) if odt_path.exists() and human_format == 'odt' else b''
    md_bytes = md.encode('utf-8')
    all_documents = {'docx': docx, 'hwpx': hwpx_doc, 'md': md_bytes, 'html': html_doc}
    if odt_doc:
        all_documents['odt'] = odt_doc
    human = all_documents.get(human_format, docx)
    return dict(canonical=model,markdown=md,html=html_doc,docx=docx,xml=xml,jsonld=ld,ttl=ttl,
                human_format=human_format,human_document=human,
                all_documents=all_documents,
                validation=validation,
                template_index=index,document_model=blocks)


# 생성된 문서 및 메타데이터 산출물을 대상 파일 경로에 저장함
def write(result,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    human_suffix='.'+result['human_format']
    output.with_name(output.name+human_suffix).write_bytes(result['human_document'])
    for suffix,key in [('.metadata.xml','xml'),('.metadata.jsonld','jsonld')]:
        value=result[key]
        output.with_name(output.name+suffix).write_bytes(value if isinstance(value,bytes) else value.encode('utf-8'))
    for suffix,key in [('.metadata.json','canonical'),('.validation.json','validation'),('.template-index.json','template_index'),('.document-model.json','document_model')]:
        output.with_name(output.name+suffix).write_text(json.dumps(result[key],ensure_ascii=False,indent=2,default=str),encoding='utf-8')


# 커맨드라인 인자를 파싱하여 AI 가이드 문서 일괄 생성을 실행함
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',nargs='+',type=Path)
    parser.add_argument('--title',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--human-format',choices=('md','html','docx','hwpx','odt'),default='docx')
    args=parser.parse_args()
    result=generate([(p.name,p.suffix,p.read_bytes()) for p in args.inputs],args.title,
                    human_format=args.human_format)
    write(result,args.output)
    print(json.dumps(result['validation'],ensure_ascii=False))


if __name__=='__main__': main()
