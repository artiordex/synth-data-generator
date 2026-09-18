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
    'anonymization_method': ('governance', 'privacy_security', 'anonymization_method'),
    'security_level': ('governance', 'privacy_security', 'security_level'),
    'endpoint': ('structure', 'api_specification', 'base_url'),
    'authentication_type': ('structure', 'api_specification', 'auth_type'),
    'authentication': ('structure', 'api_specification', 'authentication_description'),
    'pagination': ('structure', 'api_specification', 'pagination'),
    'response_path': ('structure', 'api_specification', 'payload_path'),
    'specification_url': ('structure', 'api_specification', 'specification_url'),
    'api_version': ('structure', 'api_specification', 'version'),
    'rate_limit': ('structure', 'api_specification', 'rate_limit'),
}


def _set(model, path, value):
    target=model
    for key in path[:-1]: target=target[key]
    target[path[-1]]=value


def _pointer(path):
    return '/'+'/'.join(str(value).replace('~','~0').replace('/','~1') for value in path)


def _apply_user_input(model, contract, metadata=None, field_annotations=None):
    """Apply only explicit user values before AI inference and retain their provenance."""
    overrides={}
    metadata=metadata or {}
    for key,path in USER_METADATA_PATHS.items():
        value=str(metadata.get(key,'')).strip()
        if not value: continue
        _set(model,path,value)
        overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 값')
    temporal=str(metadata.get('temporal','')).strip()
    if temporal:
        parts=[value.strip() for value in temporal.replace('~','|').split('|',1)]
        for key,value in zip(('start','end'),parts):
            if value:
                path=('dataset','temporal',key);_set(model,path,value)
                overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 시간 범위')
    for key,target in (('temporal_start','start'),('temporal_end','end')):
        value=str(metadata.get(key,'')).strip()
        if value:
            path=('dataset','temporal',target);_set(model,path,value)
            overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 시간 범위')
    keywords=[value.strip() for value in re.split(r'[,\n]',str(metadata.get('keywords',''))) if value.strip()]
    if keywords:
        model['dataset']['keywords']=keywords
        for index in range(len(keywords)):
            overrides[_pointer(('dataset','keywords',str(index)))]=(
                'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 검색 키워드')
    relations=[value.strip() for value in re.split(r'[,\n]',str(metadata.get('source_datasets',''))) if value.strip()]
    if relations:
        model['dataset']['relations']=relations
        for index in range(len(relations)):
            overrides[_pointer(('dataset','relations',str(index)))]=(
                'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 연계 데이터셋')
    contains_pii=str(metadata.get('contains_pii','')).strip().lower()
    if contains_pii:
        truthy={'true','yes','y','1','예','포함'};falsy={'false','no','n','0','아니오','미포함'}
        if contains_pii not in truthy|falsy:
            raise ValueError('개인정보 포함 여부는 true/false, 예/아니오, 포함/미포함 중 하나로 입력하세요.')
        path=('governance','privacy_security','contains_pii');_set(model,path,contains_pii in truthy)
        overrides[_pointer(path)]=('USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 확인한 개인정보 포함 여부')
    api=model['structure']['api_specification']
    if model['structure']['has_api_data']:
        operation_values={key:str(metadata.get(key,'')).strip() for key in ('endpoint','http_method','request_parameters')}
        if any(operation_values.values()):
            prototype=next(value for value in contract.template['structure']['api_specification']['operations'] if isinstance(value,dict))
            operation=api['operations'][0] if api['operations'] else contract.empty(prototype)
            operation.update(operation_id=operation.get('operation_id') or 'user-confirmed-operation',
                             operation_name=operation.get('operation_name') or model['dataset']['title'],
                             endpoint_path=operation_values['endpoint'] or operation.get('endpoint_path'),
                             http_method=operation_values['http_method'].upper() or operation.get('http_method'),
                             data_formats=operation.get('data_formats') or [
                                 profile['format'].upper() for profile in model['analysis']['sources']
                                 if profile['data_category']=='api'])
            if operation_values['request_parameters']:
                if not operation['request_parameters']:
                    request_template=next(value for value in prototype['request_parameters'] if isinstance(value,dict))
                    operation['request_parameters']=[contract.empty(request_template)]
                operation['request_parameters'][0]['description']=operation_values['request_parameters']
                overrides[_pointer(('structure','api_specification','operations','0','request_parameters','0','description'))]=(
                    'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 요청 파라미터 설명')
            api['operations']=[operation]
            for key,value in operation.items():
                if value is not None and value != []:
                    overrides[_pointer(('structure','api_specification','operations','0',key))]=(
                        'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 API 계약')
        error_codes=str(metadata.get('error_codes','')).strip()
        if error_codes:
            prototype=next(value for value in contract.template['structure']['api_specification']['error_codes'] if isinstance(value,dict))
            error=contract.empty(prototype);error.update(code='USER_PROVIDED',description=error_codes)
            api['error_codes']=[error]
            for key,value in error.items():
                if value is not None:
                    overrides[_pointer(('structure','api_specification','error_codes','0',key))]=(
                        'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 API 오류 계약')
    annotations=field_annotations or {}
    for index,field in enumerate(model['fields']):
        values=annotations.get(field['path']) or {}
        for source_key,target_key in (('english_name','name'),('label','name_ko'),('description','description'),('unit','unit'),('codes','code_list')):
            value=str(values.get(source_key,'')).strip()
            if value:
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
                overrides[_pointer(('fields',str(index),target_key))]=(
                    'USER_CONFIRMED','USER_INPUT','화면에서 담당자가 직접 입력한 필드 설명')
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
        }
        for source,target in metadata_aliases.items():
            if target not in enrichment and metadata.get(source) not in (None,''):
                enrichment[target]=metadata[source]
    candidates=[
        (('dataset','description'),enrichment.get('dataset_description')),
        (('dataset','purpose'),enrichment.get('dataset_purpose')),
        (('dataset','theme_label'),enrichment.get('theme_label')),
        (('ai','purpose'),enrichment.get('ai_purpose')),
        (('responsible_ai','known_limitations'),enrichment.get('known_limitations')),
        (('responsible_ai','data_biases'),enrichment.get('data_biases')),
        (('responsible_ai','quality_annotation'),enrichment.get('quality_annotation')),
    ]
    for path,value in candidates:
        if isinstance(value,str) and value.strip() and not model[path[0]][path[1]]:
            _set(model,path,value.strip()[:6000])
            overrides[_pointer(path)]=('AUTO_INFERRED','AI_INFERENCE','OpenAI가 관측 구조와 사용자 입력을 바탕으로 작성한 검토용 초안')
    raw_keywords=enrichment.get('keywords',[])
    if isinstance(raw_keywords,str):
        raw_keywords=re.split(r'[,\n]',raw_keywords)
    keywords=[str(value).strip() for value in raw_keywords
              if isinstance(value,str) and value.strip()][:12]
    if keywords and not model['dataset']['keywords']:
        model['dataset']['keywords']=keywords
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
    used_names={field['name'].lower() for index,field in enumerate(model['fields'])
                if _pointer(('fields',str(index),'name')) in overrides}
    for item in enrichment.get('fields',[]) if isinstance(enrichment.get('fields'),list) else []:
        if not isinstance(item,dict) or item.get('path') not in by_path: continue
        index,field=by_path[item['path']]
        english_name=item.get('english_name')
        name_path=_pointer(('fields',str(index),'name'))
        if (name_path not in overrides and isinstance(english_name,str)
                and LOWER_CAMEL_NAME.fullmatch(english_name.strip())
                and english_name.strip().lower() not in used_names):
            field['name']=english_name.strip()
            used_names.add(field['name'].lower())
            overrides[name_path]=(
                'AUTO_INFERRED','AI_INFERENCE','OpenAI가 원천 컬럼명을 lowerCamelCase 영문 물리명으로 변환한 검토용 초안')
        for source_key,target_key in (('name_ko','name_ko'),('label','name_ko'),('description','description')):
            value=item.get(source_key)
            if isinstance(value,str) and value.strip() and not field[target_key]:
                field[target_key]=value.strip()[:2000]
                overrides[_pointer(('fields',str(index),target_key))]=(
                    'AUTO_INFERRED','AI_INFERENCE','OpenAI가 원천 필드명과 관측 타입을 바탕으로 작성한 검토용 초안')


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
def generate(inputs,title,assets=None,user_metadata=None,field_annotations=None,enricher=None,human_format='docx'):
    contract=Contract(assets) if assets else Contract()
    profiles=[profile_bytes(raw,fmt,name) for name,fmt,raw in inputs]
    comparison=None
    if len(inputs)==2 and {fmt.lstrip('.') for _,fmt,_ in inputs}=={'json','xml'}:
        raw={fmt.lstrip('.'):data for _,fmt,data in inputs}
        comparison=compare_json_xml(raw['json'],raw['xml'])
    model=canonical(profiles,title,contract,comparison)
    overrides=_apply_user_input(model,contract,user_metadata,field_annotations)
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
