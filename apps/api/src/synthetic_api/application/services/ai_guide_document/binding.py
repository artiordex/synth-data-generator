# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: binding.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py
# 목적: 템플릿 AST 분석, 명시적 별칭 매핑, 정형 데이터 바인딩 및 무결성 검증을 수행함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Canonical JSON Schema validation, binding and review validation."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..ai_guide_analysis import kind

TOKEN = re.compile(r'{{\s*([^{}]+?)\s*}}')
ASSETS = Path(__file__).resolve().parents[3] / 'data' / 'ai_guide' / 'templates'
CANONICAL_SCHEMA_NAME = 'canonical-metadata.schema.json'
METADATA_TEMPLATE_NAME = 'ai_ready_metadata_template.json'
ONTOLOGY_NAME = 'ontology.ttl'


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
    # Canonical JSON Schema와 렌더링 템플릿을 로드하고 별칭 인덱스를 구축함
    def __init__(self, assets=ASSETS):
        self.assets = Path(assets)
        self.schema_path = self.assets / 'schemas' / CANONICAL_SCHEMA_NAME
        if not self.schema_path.is_file():
            raise FileNotFoundError(f'Canonical JSON Schema를 찾을 수 없습니다: {self.schema_path}')
        self.ontology_path = self.assets / ONTOLOGY_NAME
        if not self.ontology_path.is_file():
            raise FileNotFoundError(f'프로젝트 온톨로지를 찾을 수 없습니다: {self.ontology_path}')
        self.canonical_schema = json.loads(self.schema_path.read_text(encoding='utf-8'))
        try:
            from jsonschema import Draft202012Validator
            Draft202012Validator.check_schema(self.canonical_schema)
        except ImportError:
            pass
        self.template = json.loads((self.assets/METADATA_TEMPLATE_NAME).read_text(encoding='utf-8'))
        self.aliases = {}
        self.alias_candidates = {}
        self.repeat_aliases = {}
        def register(key, path):
            self.aliases[key] = path
            candidates=self.alias_candidates.setdefault(key, [])
            if path not in candidates: candidates.append(path)
        # 템플릿 AST 노드를 순회하며 별칭 경로를 등록함
        def index(node, path=''):
            if isinstance(node, dict):
                for key, value in node.items():
                    if not key.startswith('_') and not key.endswith('_desc'):
                        index(value, path+'/'+escape(key))
            elif isinstance(node, list):
                for value in node:
                    if isinstance(value,str) and value.startswith('{{#'):
                        register(value[3:-2], path)
                        self.repeat_aliases[path] = value[3:-2]
                    elif not isinstance(value,str) or not value.startswith('{{/'):
                        index(value, path+'/*')
            elif isinstance(node,str) and TOKEN.fullmatch(node):
                    register(node[2:-2], path)
        index(self.template)
        # Processing collections have stable semantic aliases so office and
        # Markdown templates can use concise repeat markers without knowing
        # the canonical snake_case path.
        for alias, path in {
            'derived': '/processing/derived_fields',
            'missing_rule': '/processing/missing_value_processing',
            'outlier_rule': '/processing/outlier_processing',
            'quality_flag': '/processing/quality_flags',
        }.items():
            register(alias, path)

    # Canonical 모델을 최상위 JSON Schema로 검증함
    def validate_schema(self, model):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            return
        errors = sorted(
            Draft202012Validator(self.canonical_schema).iter_errors(model),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            error = errors[0]
            path = '/' + '/'.join(str(part) for part in error.absolute_path) if error.absolute_path else '/'
            raise ValueError(f'Canonical JSON Schema 검증 실패: {path}: {error.message}')

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
        # Office templates historically used semantic prefixes (field.name,
        # operation.type, param.name, …) while the repeat item already
        # contains the corresponding canonical key. Resolve those aliases
        # relative to the active row.
        if contexts and '.' in key:
            prefix, remainder = key.split('.', 1)
            aliases = {
                'field': {name: name for name in (
                    'field_id', 'name', 'name_ko', 'statistics', 'description',
                    'data_type', 'inferred_type', 'required', 'unit', 'sample_values',
                    'min', 'max', 'length', 'value_origin', 'derivation_ref',
                    'missing_processing_ref', 'quality_flag_ref')},
                'task': {name: name for name in (
                    'type', 'description', 'input_fields', 'target_fields',
                    'evaluation_metrics', 'evidence', 'status', 'reason')},
                'scenario': {name: name for name in (
                    'title', 'description', 'actors', 'preconditions', 'outputs',
                    'risks', 'status', 'reason')},
                'pipeline': {name: name for name in (
                    'step', 'name', 'rules', 'output', 'agent', 'input',
                    'parameters', 'quality_gate', 'executed_at')},
                'operation': {
                    'id': 'operation_id', 'name': 'operation_name',
                    'type': 'operation_type', 'formats': 'data_formats',
                    'request_parameters': 'request_parameters',
                    'response_parameters': 'response_parameters',
                    'sample_json': 'sample_messages.json_sample',
                    'sample_xml': 'sample_messages.xml_sample',
                },
                'param': {
                    'name': 'param_name', 'name_ko': 'name_ko',
                    'data_type': 'data_type', 'required': 'required',
                    'sample_value': 'sample_value', 'description': 'description',
                    'location': 'location', 'length': 'length', 'path': 'path',
                },
                'error': {'code': 'code', 'message': 'message',
                          'description': 'description', 'http_status': 'http_status'},
                'derived': {
                    'field_id': 'field_id', 'field_name': 'field_name',
                    'derivation_type': 'derivation_type', 'source_fields': 'source_fields',
                    'description': 'description', 'method': 'method',
                    'formula_or_rule': 'formula_or_rule', 'aggregation': 'aggregation',
                    'window': 'window', 'unit': 'unit', 'parameters': 'parameters',
                    'fallback_rule': 'fallback_rule', 'reproducible': 'reproducible',
                    'confidence': 'confidence', 'notes': 'notes',
                },
                'missing_rule': {
                    'target_field_ids': 'target_field_ids',
                    'detected_missing_count': 'detected_missing_count',
                    'detected_missing_ratio': 'detected_missing_ratio',
                    'method': 'method', 'method_description': 'method_description',
                    'steps': 'steps', 'grouping_keys': 'grouping_keys',
                    'temporal_window': 'temporal_window', 'parameters': 'parameters',
                    'fallback_method': 'fallback_method', 'clipping_rule': 'clipping_rule',
                    'affected_record_count': 'affected_record_count',
                    'quality_flag_field': 'quality_flag_field',
                    'original_value_preserved': 'original_value_preserved',
                    'limitations': 'limitations',
                },
                'outlier_rule': {
                    'target_field_ids': 'target_field_ids', 'detection_method': 'detection_method',
                    'threshold': 'threshold', 'rule': 'rule', 'action': 'action',
                    'affected_count': 'affected_count', 'replacement_method': 'replacement_method',
                    'quality_flag_field': 'quality_flag_field', 'notes': 'notes',
                },
                'quality_flag': {
                    'flag_field': 'flag_field', 'description': 'description',
                    'target_fields': 'target_fields', 'values': 'values', 'meaning': 'meaning',
                },
            }
            mapped = aliases.get(prefix, {}).get(remainder.split('.', 1)[0])
            if mapped:
                suffix = remainder.split('.', 1)[1] if '.' in remainder else ''
                key = mapped + ('.' + suffix if suffix else '')
        for prefix, index, item in reversed(contexts):
            if isinstance(item,dict) and key in item:
                return item[key], prefix+'/'+str(index)+'/'+escape(key)
            # The guide catalog exposes friendly feature aliases.  Older
            # callers may provide only field_id/field_name/reason, so the
            # optional role and importance cells remain nullable instead of
            # making the whole exchange fail.
            if prefix == '/ai/recommended_features' and isinstance(item, dict):
                if key == 'name':
                    return item.get('name', item.get('field_name')), prefix+'/'+str(index)+'/name'
                if key in {'role', 'importance'}:
                    return item.get(key), prefix+'/'+str(index)+'/'+escape(key)
            if isinstance(item,dict) and '.' in key:
                # Nested paths such as sample_messages.json_sample belong to the
                # current operation, not the global Canonical root.
                relative='/'.join(escape(part) for part in key.split('.'))
                try:
                    return pointer(item,'/'+relative), prefix+'/'+str(index)+'/'+relative
                except (KeyError,IndexError,ValueError,TypeError):
                    pass
        # param.* aliases occur in both request and response arrays. Select the
        # candidate fully resolved by the active repeat scope, not the last
        # occurrence in the JSON template.
        for candidate in self.alias_candidates.get(key, ()) if contexts else ():
            path=candidate
            for prefix, index, item in contexts:
                path=path.replace(prefix+'/*', prefix+'/'+str(index))
            if '*' in path: continue
            if not any(path.startswith(prefix+'/'+str(index)+'/') or path==prefix+'/'+str(index)
                       for prefix,index,item in contexts): continue
            try:
                return pointer(model,path), path
            except (KeyError,IndexError,ValueError,TypeError):
                pass
        path = self.aliases.get(key, '/'+key.replace('.', '/'))
        for prefix, index, item in contexts:
            path = path.replace(prefix+'/*', prefix+'/'+str(index))
        try:
            return pointer(model,path), path
        except (KeyError,IndexError,ValueError,TypeError) as exc:
            # Scalar repeat aliases (keyword/model_name/format/etc.).
            if contexts and path == contexts[-1][0]+'/*':
                return contexts[-1][2], contexts[-1][0]+'/'+str(contexts[-1][1])
            if path.startswith('/toc/') or path.startswith('/toc_lines/'):
                return '', path
            raise ValueError(f'해석 불가능한 바인딩: {key} → {path}') from exc


# 프로파일 목록과 계약을 결합하여 표준화된 캐노니컬 모델을 생성함
def _source_dataset_id(profile):
    digest = profile.get('sha256') or hashlib.sha256(str(profile.get('name', '')).encode()).hexdigest()
    return 'urn:sha256:' + digest


def _remap_processing_paths(value, path_to_field_id):
    """Map analyzer paths to canonical field IDs without changing unknown values."""
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key in {'target_field_ids', 'source_fields', 'grouping_keys', 'target_fields'} and isinstance(child, list):
                value[key] = [path_to_field_id.get(str(item), str(item)) for item in child]
            elif key in {'field_id', 'flag_field', 'quality_flag_field'} and isinstance(child, str):
                value[key] = path_to_field_id.get(child, child)
            else:
                _remap_processing_paths(child, path_to_field_id)
    elif isinstance(value, list):
        for child in value:
            _remap_processing_paths(child, path_to_field_id)
    return value


def _processing_for_profiles(profiles, category, model, field_ids_by_source_path):
    """Merge source-grounded processing observations into the canonical model."""
    processing = copy.deepcopy(model.get('processing') or {})
    integration = copy.deepcopy(processing.get('integration') or {})
    arrays = {
        'derived_fields': [],
        'transformations': [],
        'missing_value_processing': [],
        'outlier_processing': [],
        'quality_flags': [],
    }
    source_ids = [_source_dataset_id(profile) for profile in profiles]
    def remap_source_processing(profile):
        source_id = _source_dataset_id(profile)
        source_map = {
            path: field_id
            for (candidate_source, path), field_id in field_ids_by_source_path.items()
            if candidate_source == source_id
        }
        source_processing = copy.deepcopy(profile.get('processing') or {})
        _remap_processing_paths(source_processing, source_map)
        return source_processing

    if len(profiles) == 1:
        source_processing = remap_source_processing(profiles[0])
        integration.update(source_processing.get('integration') or {})
        for key in arrays:
            value = source_processing.get(key)
            if isinstance(value, list):
                arrays[key].extend(value)
    else:
        explicit_integrated = any(
            (profile.get('processing') or {}).get('integration', {}).get('is_integrated') is True
            for profile in profiles
            if isinstance((profile.get('processing') or {}).get('integration'), dict)
        )
        integration.update({
            'is_integrated': True if explicit_integrated else None,
            'description': '여러 입력 원천이 함께 제출되었으나 결합 결과는 원천에서 확인되지 않음',
            'method': None,
            'join_type': None,
            'join_keys': [],
            'temporal_alignment': None,
            'spatial_alignment': None,
            'source_dataset_ids': source_ids,
            'external_sources': [profile.get('name') for profile in profiles],
            'output_description': None,
            'limitations': '결합키·결합 방식·시간 및 공간 정렬 규칙은 기관 확인 필요',
        })
        for profile in profiles:
            source_processing = remap_source_processing(profile)
            for key in arrays:
                value = source_processing.get(key)
                if isinstance(value, list):
                    arrays[key].extend(copy.deepcopy(value))
    integration['source_dataset_ids'] = source_ids
    if integration.get('is_integrated') is None and len(profiles) == 1:
        integration['is_integrated'] = False
    for key, value in arrays.items():
        processing[key] = value
    processing['integration'] = integration
    return processing


def canonical(profiles, title, contract, comparison=None):
    model = contract.empty()
    now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    primary = profiles[0]
    file_profiles = [profile for profile in profiles if profile['data_category'] == 'file']
    api_profiles = [profile for profile in profiles if profile['data_category'] == 'api']
    has_file = bool(file_profiles)
    has_api = bool(api_profiles)
    category = 'hybrid' if has_file and has_api else 'file' if has_file else 'api'
    model['document'].update(status='REVIEW_REQUIRED',generated_utc=now,doc_type=category+'_dataset',
                             review_status='INCOMPLETE_REVIEW',is_draft=True,
                             review_notice='임시 검토본 - 기관 공식 확인 필요')
    model['dataset'].update(title=title,byte_size=sum(p['byte_size'] for p in profiles),
                            uri_or_id='urn:sha256:'+primary['sha256'])
    root_types=sorted({profile['root_type'] for profile in profiles})
    model['structure'].update(data_category=category,has_file_data=has_file,has_api_data=has_api,
                              root_type=', '.join(root_types),
                              traits=sorted({v for p in profiles for v in p['traits']}),is_large_dataset=False)
    distribution=model['structure']['distribution']
    distribution.update(
        format=', '.join(profile['format'].upper() for profile in file_profiles) or None,
        encoding=', '.join(sorted({profile['encoding'] for profile in file_profiles if profile.get('encoding')})) or None,
        folder_structure=[profile['name'] for profile in file_profiles] or None,
    )
    api_spec=model['structure']['api_specification']
    api_spec['contract_status']='REVIEW_REQUIRED' if has_api else 'NOT_APPLICABLE'
    api_spec['namespaces']=[profile['namespaces'] for profile in api_profiles] or None
    api_spec['payload_path']=[profile['record_sets'] for profile in api_profiles] or None
    api_spec['path_syntax']='Structural Path; /* = 관측 항목 합집합' if has_api else None
    for key, block in model['modality_specifications'].items():
        if isinstance(block,dict):
            block['is_applicable'] = key=='tabular_numeric_metadata'
    model['modality_specifications']['tabular_numeric_metadata']['record_set_id'] = model['dataset']['uri_or_id']+'#observed-records'
    fields=[]
    field_ids_by_source_path={}
    field_template = next(v for v in contract.template['fields'] if isinstance(v,dict))
    for p in profiles:
        source_id = _source_dataset_id(p)
        for f in p['fields']:
            field=contract.empty(field_template)
            stats=field['statistics']
            stats.update({k:v for k,v in f.items() if k not in {'path','name','sheet','types','sample_values'}})
            field_id=model['dataset']['uri_or_id']+f"#field-{len(fields)+1}"
            field.update(dict(field_id=field_id,path=f['path'],name=f.get('name',f['path']),
                               name_ko=None,order=len(fields)+1,data_type=' | '.join(f['types']),inferred_type=None,
                               required=None,is_pk=None,description=None,unit=None,code_list=None,constraints=None,
                               statistics=stats,
                               sample_values=f.get('sample_values',[]),path_syntax='Structural Path',
                               source=p['name'],source_category=p['data_category'],
                               value_origin=f.get('value_origin') or 'observed',
                               source_dataset_id=source_id,source_field=f.get('path'),
                               derived=bool(f.get('derived', False)),derivation_ref=None,
                               missing_processing_ref=None,quality_flag_ref=None))
            fields.append(field)
            field_ids_by_source_path[(source_id, f['path'])] = field_id
    model['fields']=fields
    # Analyzer paths are source-local.  Resolve them to canonical field IDs;
    # unresolved paths remain visible and are therefore reviewable rather than
    # being silently dropped.
    model['processing'] = _processing_for_profiles(profiles, category, model, field_ids_by_source_path)
    processing_refs={}
    for key, field_key in (('missing_value_processing','missing_processing_ref'),
                           ('quality_flags','quality_flag_ref'), ('derived_fields','derivation_ref')):
        for index, item in enumerate(model['processing'].get(key) or []):
            if not isinstance(item, dict):
                continue
            targets=list(item.get('target_field_ids') or item.get('target_fields') or [])
            if key == 'derived_fields':
                targets=list(item.get('source_fields') or []) + ([item.get('field_id')] if item.get('field_id') else [])
            for target in targets:
                processing_refs.setdefault(str(target), {}).setdefault(field_key, f'/processing/{key}/{index}')
    for field in fields:
        refs=processing_refs.get(field['field_id'], {})
        field.update(refs)
    if has_api:
        operation_template=next(value for value in contract.template['structure']['api_specification']['operations']
                                if isinstance(value,dict))
        request_template=next(value for value in operation_template['request_parameters'] if isinstance(value,dict))
        response_template=next(value for value in operation_template['response_parameters'] if isinstance(value,dict))
        error_template=next(value for value in contract.template['structure']['api_specification']['error_codes']
                            if isinstance(value,dict))
        operation=contract.empty(operation_template)
        operation.update(operation_name=title,
                         data_formats=sorted({profile['format'].upper() for profile in api_profiles}),
                         request_parameters=[contract.empty(request_template)],
                         response_parameters=[])
        for field in fields:
            if field['source_category'] != 'api':
                continue
            response=contract.empty(response_template)
            response.update(param_name=field['name'],name_ko=field['name_ko'],path=field['path'],
                            data_type=field['data_type'],required=field['required'],
                            sample_value=field['sample_values'][0] if field['sample_values'] else None,
                            description=field['description'])
            operation['response_parameters'].append(response)
        api_spec['operations']=[operation]
        api_spec['error_codes']=[contract.empty(error_template)]
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
        reason='업로드 데이터의 null·빈 문자열 제외 비율. 모집단 대표성·정확성·필수 필드 충족 여부를 뜻하지 않음')
    model['usage']['status']='REVIEW_REQUIRED'
    observed_records=[profile['observed_records'] for profile in profiles if profile.get('observed_records') is not None]
    model['analysis'].update(scope='FULL',sample_size=sum(observed_records) if observed_records else None,population_size=None,
                             sampling_method='제공 파일 전수 조사',record_boundary_preserved=True,
                             limitations='제공 샘플의 전수 조사. 응답 선언 전체 건수는 모집단 관측 수가 아님. 외부 링크 대상 미열람.',analyzed_at=now,
                             sources=profiles,comparison=comparison)
    model['lineage'].update(source_datasets=[dict(name=p['name'],sha256=p['sha256'],byte_size=p['byte_size']) for p in profiles],
                            preprocessing_history='이 생성 경로는 원본을 수정하거나 보간하지 않음. 원본 생성 이전 가공 이력은 기관 확인 필요.')
    model['provenance'].update(generator_version='3.0',source_file_sha256=primary['sha256'],generated_utc=now)
    temporal=any(f['statistics'].get('temporal') for f in fields) or any(
        table.get('temporal') for profile in profiles for table in profile['tables'])
    if temporal:
        model['ai']['purpose']='관측된 시간·수치 필드로 예측 가능성을 검토. 목표 변수와 단위 확정 후 과거 구간 기준모델과 비교.'
        model['ai']['split_ratio']['strategy']='시간순 분리 및 개체별 분리 검토. 동일 개체·중복 시각과 파생/예측값이 학습·시험 양쪽에 유입되지 않도록 확인.'
    else:
        model['ai']['purpose']='관측 필드의 업무 의미·목표 변수·권리 확인 후 분석 임무를 선정하는 추론 초안.'
    numeric_fields=[field for field in fields
                    if any(kind_name in {'integer','number'} for kind_name in str(field.get('data_type','')).split(' | '))]
    model['ai']['recommended_features']=[
        {'field_id': field['field_id'], 'field_name': field['name'], 'name': field['name'],
         'role': None, 'importance': None,
         'reason': '관측된 수치형 필드이며 활용 입력 후보일 뿐 목표변수·업무 의미는 기관 확인 필요'}
        for field in numeric_fields
    ]
    model['ai']['target_candidates']=[
        {'field_id': field['field_id'], 'field_name': field['name'],
         'reason': '수치형 구조 후보이며 목표변수 지정 근거는 입력에서 확인되지 않음'}
        for field in numeric_fields
    ]
    model['ai']['time_series_characteristics']={
        'observed': bool(temporal),
        'evidence': '시간형 관측값의 간격·누락은 기관 업무 기준과 함께 확인 필요' if temporal
                    else '시간형 특성을 입력에서 확인하지 못함',
    }
    model['ai']['spatial_characteristics']=None
    model['ai']['bias']='수집 범위·기간·대상과 결측 처리에 따른 편향은 기관 확인 필요'
    model['ai']['representativeness']='제공된 입력 범위의 대표성은 모집단·수집 설계 확인 전 확정할 수 없음'
    model['ai']['quality_flag_usage']=('품질 플래그 후보의 코드 의미와 대상 필드를 확인한 뒤 분석 입력 또는 평가 지표에 사용'
                                       if model['processing'].get('quality_flags') else None)
    model['ai']['imputed_data_usage']=('결측 처리 규칙이 확인되기 전에는 보정값을 관측값과 혼용하지 않음'
                                       if model['processing'].get('missing_value_processing') else None)
    model['ai']['usage_risks']=[
        {'risk': '목표변수·파생 규칙·결측 처리 규칙이 확인되지 않은 상태에서 성능을 확정하지 않음'},
        {'risk': '품질 플래그와 보정값의 의미를 확인하지 않고 학습·평가에 혼용하지 않음'},
    ]
    model['ai']['large_data_optimization'].update(is_chunk_applied=False,sample_size=sum(observed_records) if observed_records else None,
                                                 parquet_recommended=True)
    return finalize(model, contract=contract)


# 리프 노드별 검토 항목을 생성하고 캐노니컬 모델을 완성함
def finalize(model, status_overrides=None, contract=None):
    """One typed review record per leaf/empty collection; no phantom pointers."""
    status_overrides = status_overrides or {}
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
            if path.startswith('/structure/distribution/') and not model['structure']['has_file_data'] and value is None:
                status='NOT_APPLICABLE'; reason='파일데이터 입력이 없어 파일 배포 명세는 비해당'
            if path.startswith('/structure/api_specification/') and not model['structure']['has_api_data'] and value is None:
                status='NOT_APPLICABLE'; reason='파일데이터 입력의 API 계약은 비해당'
            override=status_overrides.get(path)
            if override:
                status,source_type,override_reason=override
                reason=override_reason
            else:
                source_type='UNKNOWN' if status=='REVIEW_REQUIRED' else 'AI_INFERENCE' if status=='AUTO_INFERRED' else 'FILE_PROFILE'
            entry=dict(id=hashlib.sha256(path.encode()).hexdigest()[:16],bindingPath=path,label=path,
                       property=path,namespace='urn:synthetic-data:ai-ready:v2:',value=value,valueType=kind(value),
                       sourceType=source_type,
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
    validate(model, contract=contract)
    return model


# 캐노니컬 모델을 JSON Schema와 JSON 포인터 규칙으로 검증함
def validate(model, contract=None):
    if contract is None:
        contract = Contract()
    # Schema validation is the first gate: every renderer consumes only a
    # model that conforms to the canonical contract.
    contract.validate_schema(model)
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
