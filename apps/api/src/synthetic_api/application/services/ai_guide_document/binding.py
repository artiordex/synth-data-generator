# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: binding.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py
# 목적: 템플릿 AST 분석, 명시적 별칭 매핑, 정형 데이터 바인딩 및 무결성 검증을 수행함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Template AST, explicit alias mapping, typed binding and review validation."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..ai_guide_analysis import kind

TOKEN = re.compile(r'{{\s*([^{}]+?)\s*}}')
ASSETS = Path(__file__).resolve().parents[7] / 'docs' / 'adr'


# 모델 객체에서 JSON 포인터 경로에 해당하는 값을 추출함
def pointer(model, path):
    value = model
    for key in path.lstrip('/').split('/') if path else []:
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


# JSON 포인터 특수문자(~, /)를 이스케이프함
def escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


class Contract:
    # 템플릿 계약 객체를 초기화하고 별칭 인덱스를 구축함
    def __init__(self, assets=ASSETS):
        self.assets = Path(assets)
        self.template = json.loads((self.assets/'AI친화_메타데이터_템플릿.json').read_text(encoding='utf-8'))
        self.aliases = {}
        self.repeat_aliases = {}
        # 템플릿 AST 노드를 순회하며 별칭 경로를 등록함
        def index(node, path=''):
            if isinstance(node, dict):
                for key, value in node.items():
                    if not key.startswith('_') and not key.endswith('_desc'):
                        index(value, path+'/'+escape(key))
            elif isinstance(node, list):
                for value in node:
                    if isinstance(value,str) and value.startswith('{{#'):
                        self.aliases[value[3:-2]] = path
                        self.repeat_aliases[path] = value[3:-2]
                    elif not isinstance(value,str) or not value.startswith('{{/'):
                        index(value, path+'/*')
            elif isinstance(node,str) and TOKEN.fullmatch(node):
                self.aliases[node[2:-2]] = path
        index(self.template)

    # 템플릿 노드의 플레이스홀더를 초기 빈 값으로 치환함
    def empty(self, node=None):
        node = self.template if node is None else node
        if isinstance(node,dict):
            return {k:self.empty(v) for k,v in node.items() if not k.startswith('_') and not k.endswith('_desc')}
        if isinstance(node,list):
            return [] if any(isinstance(v,str) and v.startswith('{{#') for v in node) else [self.empty(v) for v in node]
        return None if isinstance(node,str) and TOKEN.search(node) else node

    # 모델과 컨텍스트로부터 키에 해당하는 값과 바인딩 경로를 해석함
    def resolve(self, model, key, contexts=()):
        for prefix, index, item in reversed(contexts):
            if isinstance(item,dict) and key in item:
                return item[key], prefix+'/'+str(index)+'/'+escape(key)
        path = self.aliases.get(key, '/'+key.replace('.', '/'))
        for prefix, index, item in contexts:
            path = path.replace(prefix+'/*', prefix+'/'+str(index))
        try:
            return pointer(model,path), path
        except (KeyError,IndexError,ValueError,TypeError) as exc:
            # Scalar repeat aliases (keyword/model_name/format/etc.).
            if contexts and path == contexts[-1][0]+'/*':
                return contexts[-1][2], contexts[-1][0]+'/'+str(contexts[-1][1])
            raise ValueError(f'해석 불가능한 바인딩: {key} → {path}') from exc


# 프로파일 목록과 계약을 결합하여 표준화된 캐노니컬 모델을 생성함
def canonical(profiles, title, contract, comparison=None):
    model = contract.empty()
    now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    primary = profiles[0]
    category = primary['data_category']
    if any(p['data_category'] != category for p in profiles):
        raise ValueError('서로 다른 가이드 종류의 입력은 별도로 생성하세요.')
    model['document'].update(status='REVIEW_REQUIRED',generated_utc=now,doc_type=category+'_dataset',
                             review_status='INCOMPLETE_REVIEW',is_draft=True,
                             review_notice='임시 검토본 - 기관 공식 확인 필요')
    model['dataset'].update(title=title,byte_size=sum(p['byte_size'] for p in profiles),
                            uri_or_id='urn:sha256:'+primary['sha256'])
    model['structure'].update(data_category=category,root_type=primary['root_type'],
                              traits=sorted({v for p in profiles for v in p['traits']}),is_large_dataset=False)
    model['structure']['distribution'].update(format=', '.join(p['format'] for p in profiles),encoding=primary['encoding'],
                                             folder_structure=[p['name'] for p in profiles])
    model['structure']['api_specification']['contract_status']='REVIEW_REQUIRED' if category=='api' else 'NOT_APPLICABLE'
    model['structure']['api_specification']['namespaces']=[p['namespaces'] for p in profiles]
    model['structure']['api_specification']['payload_path']=[p['record_sets'] for p in profiles] if category=='api' else None
    model['structure']['api_specification']['path_syntax']='Structural Path; /* = 관측 항목 합집합' if category=='api' else None
    for key, block in model['modality_specifications'].items():
        if isinstance(block,dict):
            block['is_applicable'] = key=='tabular_numeric_metadata'
    model['modality_specifications']['tabular_numeric_metadata']['record_set_id'] = model['dataset']['uri_or_id']+'#observed-records'
    fields=[]
    field_template = next(v for v in contract.template['fields'] if isinstance(v,dict))
    for p in profiles:
        for f in p['fields']:
            field=contract.empty(field_template)
            stats=field['statistics']
            stats.update({k:v for k,v in f.items() if k not in {'path','name','sheet','types'}})
            field.update(dict(field_id=model['dataset']['uri_or_id']+f"#field-{len(fields)+1}",path=f['path'],name=f.get('name',f['path']),
                               name_ko=None,order=len(fields)+1,data_type=' | '.join(f['types']),inferred_type=None,
                               required=None,is_pk=None,description=None,unit=None,code_list=None,constraints=None,
                               statistics=stats,
                               sample_values=[],path_syntax='Structural Path',source=p['name']))
            fields.append(field)
    model['fields']=fields
    model['statistics'].update(total_records=primary['observed_records'] if len(profiles)==1 or comparison and comparison['equivalent'] else None,
                               total_fields=len(fields),total_bytes=sum(p['byte_size'] for p in profiles),
                               missing_cells_total=sum(f['statistics'].get('null_count',0)+f['statistics'].get('empty_count',0) for f in fields))
    for key,metric in model['quality']['metrics'].items():
        metric.update(status='REVIEW_REQUIRED',scope='FULL',reason='정답·업무 규칙·기준일·키 계약 기관 확인 필요',
                      evidence='미평가; 점수 null')
    observed=sum(p['quality_metrics'][0].get('observed',0) for p in profiles)
    missing=sum(p['quality_metrics'][0].get('missing',0) for p in profiles)
    model['quality']['metrics']['completeness'].update(score=100*(observed-missing)/observed if observed else None,
        status='AUTO_CONFIRMED' if observed else 'REVIEW_REQUIRED',scope='FULL',
        evidence=f'관측 {observed}개, null/빈 문자열 {missing}개; (관측-결측)/관측×100. 누락 선택 필드 제외; 업무 필수성 미확정.',
        reason='직접 관측값의 완전성. 모집단·필수 필드 완전성 인증 아님')
    model['usage']['status']='REVIEW_REQUIRED'
    model['analysis'].update(scope='FULL',sample_size=primary['observed_records'],population_size=None,
                             sampling_method='제공 파일 전수 조사',record_boundary_preserved=True,
                             limitations='제공 샘플의 전수 조사. 응답 선언 전체 건수는 모집단 관측 수가 아님. 외부 링크 대상 미열람.',analyzed_at=now,
                             sources=profiles,comparison=comparison)
    model['lineage'].update(source_datasets=[dict(name=p['name'],sha256=p['sha256'],byte_size=p['byte_size']) for p in profiles],
                            preprocessing_history='이 생성 경로는 원본을 수정하거나 보간하지 않음. 원본 생성 이전 가공 이력은 기관 확인 필요.')
    model['provenance'].update(generator_version='3.0',source_file_sha256=primary['sha256'],generated_utc=now)
    names=' '.join(f['name'] for f in fields)
    temporal=any(f['statistics'].get('temporal') for f in fields) or any(t.get('temporal') for t in primary['tables'])
    if temporal:
        model['ai']['purpose']='관측된 시간·수치 필드로 예측 가능성을 검토. 목표 변수와 단위 확정 후 과거 구간 기준모델과 비교.'
        model['ai']['split_ratio']['strategy']='시간순 분리 및 개체별 분리 검토. 동일 개체·중복 시각과 파생/예측값이 학습·시험 양쪽에 유입되지 않도록 확인.'
    elif all(name in names for name in ('lbl','skeletonLink','anomalyScoreLink','rsltJsonDownloadLink')):
        model['ai']['purpose']='관측된 라벨·외부 링크 구조를 기반으로 이상행동 탐지 및 포즈 추정 결과 연계를 검토하는 추론 초안. 링크 대상·정답·성능은 미확인.'
    else:
        model['ai']['purpose']='관측 필드의 업무 의미·목표 변수·권리 확인 후 분석 임무를 선정하는 추론 초안.'
    model['ai']['large_data_optimization'].update(is_chunk_applied=False,sample_size=primary['observed_records'],
                                                 parquet_recommended=True)
    return finalize(model)


# 리프 노드별 검토 항목을 생성하고 캐노니컬 모델을 완성함
def finalize(model):
    """One typed review record per leaf/empty collection; no phantom pointers."""
    entries=[]
    # 모델 트리를 순회하며 검토 항목을 수집함
    def walk(value,path):
        if isinstance(value,dict) and value:
            for k,v in value.items(): walk(v,path+'/'+escape(k))
        elif isinstance(value,list) and value:
            for i,v in enumerate(value): walk(v,path+'/'+str(i))
        else:
            status='REVIEW_REQUIRED' if value is None else 'AUTO_CONFIRMED'
            reason='직접 관측·계산 또는 생성 계약 값' if value is not None else '원천에서 확인되지 않음; 기관 확인 필요'
            if path.startswith('/analysis/sources/') or path.startswith('/analysis/comparison'):
                status='AUTO_CONFIRMED'; reason='원천 관측 결과 또는 비교 결과; null도 관측 상태로 보존'
            if re.match(r'/fields/\d+/statistics/',path) and value is None:
                status='NOT_APPLICABLE'; reason='해당 통계에 유효 관측값이 없거나 해당 구조에 적용되지 않음'
            if path.startswith('/ai/') and value is not None and not path.endswith(('is_chunk_applied','sample_size')):
                status='AUTO_INFERRED'; reason='관측 구조를 바탕으로 한 활용 권고 초안'
            if path.startswith('/modality_specifications/') and value is None:
                block=pointer(model,'/'.join(path.split('/')[:3]))
                if isinstance(block,dict) and block.get('is_applicable') is False:
                    status='NOT_APPLICABLE'; reason='해당 미디어 원본은 분석 입력에 포함되지 않음'
            if path.startswith('/structure/api_specification/') and model['structure']['data_category']=='file' and value is None:
                status='NOT_APPLICABLE'; reason='파일데이터 입력의 API 계약은 비해당'
            entry=dict(id=hashlib.sha256(path.encode()).hexdigest()[:16],bindingPath=path,label=path,
                       property=path,namespace='urn:synthetic-data:ai-ready:v2:',value=value,valueType=kind(value),
                       sourceType='UNKNOWN' if status=='REVIEW_REQUIRED' else 'AI_INFERENCE' if status=='AUTO_INFERRED' else 'FILE_PROFILE',
                       status=status,confidence=None,reason=reason,updatedAt=model['document']['generated_utc'],sourceReference='입력 파일 프로파일 / 템플릿 계약')
            entries.append(entry)
    for key,value in model.items():
        if key not in {'canonicalItems','reviewRequired','document'}: walk(value,'/'+escape(key))
    model['canonicalItems']=entries
    model['reviewRequired']=[dict(e,category=e['bindingPath'].split('/')[1],action='기관 근거 자료로 확인') for e in entries if e['status']=='REVIEW_REQUIRED']
    statuses={e['status'] for e in entries}
    if 'REVIEW_REQUIRED' in statuses:
        model['document'].update(status='REVIEW_REQUIRED',review_status='INCOMPLETE_REVIEW',is_draft=True,review_notice='임시 검토본 - 기관 공식 확인 필요')
    elif 'AUTO_INFERRED' in statuses:
        model['document'].update(status='AUTO_INFERRED',review_status='INFERRED_DRAFT',is_draft=True,review_notice='AI 작성 초안 - 검토 필요')
    else:
        model['document'].update(status='AUTO_CONFIRMED',review_status='COMPLETE_REVIEW',is_draft=False,review_notice='')
    validate(model)
    return model


# 캐노니컬 모델의 포인터 값 일치성과 검토 목록 무결성을 검증함
def validate(model):
    paths=set()
    for e in model['canonicalItems']:
        if e['bindingPath'] in paths: raise ValueError('중복 bindingPath')
        paths.add(e['bindingPath'])
        actual=pointer(model,e['bindingPath'])
        if type(actual) is not type(e['value']) or actual != e['value']: raise ValueError('Canonical 값 불일치')
        if e['status'] in {'REVIEW_REQUIRED','NOT_APPLICABLE'} and actual is not None:
            raise ValueError('미확정 값은 null이어야 합니다')
    expected=[e['id'] for e in model['canonicalItems'] if e['status']=='REVIEW_REQUIRED']
    if expected != [e['id'] for e in model['reviewRequired']]: raise ValueError('검토 목록 불일치')
    for item in model['reviewRequired']:
        entry=next(e for e in model['canonicalItems'] if e['id']==item['id'])
        if any(item.get(k)!=v for k,v in entry.items()): raise ValueError('파생 검토 레코드 불일치')
    expected_paths=set()
    # 검토 필수 경로 목록을 재귀적으로 수집함
    def required(value,path):
        if isinstance(value,dict) and value:
            for key,child in value.items(): required(child,path+'/'+escape(key))
        elif isinstance(value,list) and value:
            for index,child in enumerate(value): required(child,path+'/'+str(index))
        else: expected_paths.add(path)
    for key,value in model.items():
        if key not in {'canonicalItems','reviewRequired','document'}: required(value,'/'+escape(key))
    if expected_paths != paths: raise ValueError('검토 바인딩 누락 또는 초과')
    if TOKEN.search(json.dumps(model,ensure_ascii=False)): raise ValueError('미치환 플레이스홀더')
