# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: ai_guide_template.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_template.py
# 목적: HWPX 서식 템플릿에 분석 메타데이터를 바인딩하고 가이드 문서를 렌더링함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Bind analyzed data to the user's HWPX sample without carrying sample facts forward."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field

from synthetic_api.application.services.ai_guide_analysis import dumps
from synthetic_api.application.services.ai_guide_document.hwpx_parser import HwpxParser
from synthetic_engine.document_conversion.parsers.package import DocumentPackage

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
OPF = 'http://www.idpf.org/2007/opf/'
ODF = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
TEMPLATE = Path(__file__).resolve().parents[2] / 'data' / 'ai_guide_template.hwpx'
TEMPLATE_ID = 'kdhc-ai-ready-sample-v1'
REVIEW = '기관 확인 필요 [REVIEW_REQUIRED]'

# Explicit input fields: values from a sample never become defaults for a new dataset.
METADATA_FIELDS = {
    'publisher': ('제공기관', 'dct:publisher'),
    'description': ('데이터 설명', 'dct:description'),
    'department': ('운영부서', 'dct:creator'),
    'legal_basis': ('관련법령 및 근거', 'dct:references'),
    'landing_page': ('공개 페이지', 'dcat:landingPage'),
    'contact': ('담당부서·연락처', 'dcat:contactPoint'),
    'license': ('라이선스 및 이용조건', 'dct:license'),
    'rights': ('저작권·외부 데이터 권리', 'dct:rights'),
    'update_frequency': ('갱신주기', 'dct:accrualPeriodicity'),
    'version': ('배포 버전', 'owl:versionInfo'),
    'issued': ('최초 공개일', 'dct:issued'),
    'modified': ('원천 수정일', 'dct:modified'),
    'temporal': ('시간 범위 및 시간대', 'dct:temporal'),
    'spatial': ('공간·대상 범위', 'dct:spatial'),
    'source_datasets': ('원천·연계 데이터셋', 'dct:relation'),
    'transformation': ('결합키·파생식·가공 이력', '내부 계보 항목'),
    'imputation': ('결측 보정 방법·플래그 의미', '내부 계보 항목'),
    'training_split': ('AI 목적·학습/검증 분리·정보 누출 방지', '내부 AI 활용 항목'),
    'limitations': ('대표성·편향·개인정보·이용 한계', '내부 검토 항목'),
    'service_name': ('API 서비스명', 'dct:title'),
    'endpoint': ('API URL', 'dcat:endpointURL'),
    'interface_type': ('인터페이스 표준', 'dcat:endpointDescription'),
    'http_method': ('HTTP method', '내부 API 계약'),
    'http_methods': ('HTTP methods', '내부 API 계약'),
    'mime_types': ('교환 데이터 형식', 'dcat:mediaType'),
    'character_encoding': ('문자 인코딩', '내부 API 계약'),
    'https': ('HTTPS 사용 여부', '내부 API 계약'),
    'access_rights': ('서비스 접근 권한', 'dct:accessRights'),
    'service_start': ('서비스 시작일', 'dct:issued'),
    'last_modified': ('서비스 최종 수정일', 'dct:modified'),
    'auth_type': ('인증 유형', '내부 API 계약'),
    'authentication': ('인증 방식 (실제 키 입력 금지)', '내부 API 계약'),
    'auth_type_desc': ('인증 적용 설명', '내부 API 계약'),
    'request_parameters': ('요청 파라미터·필수·기본값', '내부 API 계약'),
    'pagination': ('페이지네이션·호출 제한', '내부 API 계약'),
    'error_codes': ('오류 코드·재시도', '내부 API 계약'),
    'response_path': ('업무 레코드 경로', '내부 API 계약'),
    'specification_url': ('API 명세 URL', 'dcat:endpointDescription'),
    'api_version': ('API 버전', 'owl:versionInfo'),
    'rate_limit': ('호출 제한', '내부 API 계약'),
    'sample_request': ('요청 메시지 샘플', '내부 API 계약'),
    'sample_response_xml': ('XML 응답 샘플', '내부 API 계약'),
    'sample_response_json': ('JSON 응답 샘플', '내부 API 계약'),
}
API_FIELD_ORDER = [
    'service_name', 'endpoint', 'specification_url', 'api_version', 'service_start',
    'last_modified', 'interface_type', 'http_method', 'http_methods', 'mime_types',
    'character_encoding', 'https', 'access_rights', 'auth_type', 'authentication', 'auth_type_desc',
    'request_parameters', 'pagination', 'rate_limit', 'response_path', 'error_codes',
    'sample_request', 'sample_response_xml', 'sample_response_json',
]
API_KEYS = set(API_FIELD_ORDER)


class FieldAnnotation(BaseModel):
    model_config = ConfigDict(extra='forbid', str_max_length=2000)
    label: str = ''
    description: str = ''
    unit: str = ''
    codes: str = ''


class TemplateGuideRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    canonical_metadata: dict = Field(...)
    metadata: dict[str, str] = Field(default_factory=dict)
    field_annotations: dict[str, FieldAnnotation] = Field(default_factory=dict)


# 단일 값 또는 객체를 텍스트 문자열로 변환함
def _value_text(value):
    return value if isinstance(value, str) else dumps(value)


# 템플릿 가이드 요청으로부터 계약 사양 및 메타데이터를 구성함
def build_contract(req: TemplateGuideRequest) -> dict:
    model = deepcopy(req.canonical_metadata)
    if model.get('schema_version') != '2.0' or model.get('data_category') not in {'api', 'file'}:
        raise ValueError('AI가이드 v2 분석 결과가 필요합니다. 데이터를 다시 분석하세요.')
    for key in ('format', 'root_type', 'sha256'):
        if not isinstance(model.get(key), str) or not model[key]:
            raise ValueError(f'분석 결과 {key}가 누락되었습니다.')
    if type(model.get('byte_size')) is not int or model['byte_size'] < 0:
        raise ValueError('분석 바이트 수가 잘못되었습니다.')
    for key in ('tables', 'record_sets', 'quality_metrics', 'warnings'):
        if not isinstance(model.get(key), list):
            raise ValueError(f'분석 결과 {key}가 잘못되었습니다.')
    fields = model.get('fields')
    if not isinstance(fields, list) or len(fields) > 5000:
        raise ValueError('fields는 5,000개 이하의 구조 경로 목록이어야 합니다.')
    paths = []
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get('path'), str):
            raise ValueError('필드 경로가 누락되었습니다.')
        if not isinstance(field.get('types'), list) or not all(isinstance(t, str) for t in field['types']):
            raise ValueError('필드 타입이 잘못되었습니다.')
        for key in ('occurrences', 'null_count', 'empty_count'):
            if type(field.get(key)) is not int or field[key] < 0:
                raise ValueError(f'필드 {key}는 0 이상의 정수여야 합니다.')
        if field['null_count'] + field['empty_count'] > field['occurrences']:
            raise ValueError('결측 수가 관측 수보다 많습니다.')
        paths.append(field['path'])
    if len(paths) != len(set(paths)):
        raise ValueError('중복된 필드 경로입니다.')
    if set(req.metadata) - METADATA_FIELDS.keys():
        raise ValueError('지원하지 않는 기관 메타데이터 키입니다.')
    if set(req.field_annotations) - set(paths):
        raise ValueError('분석 결과에 없는 경로에 필드 설명이 지정되었습니다.')
    if any(len(value) > 4000 for value in req.metadata.values()):
        raise ValueError('기관 메타데이터는 항목당 4,000자 이하로 작성하세요.')
    if len(dumps(req.model_dump()).encode('utf-8')) > 8 * 1024 * 1024:
        raise ValueError('템플릿 입력 메타데이터는 8 MiB 이하로 제한합니다.')
    metadata = {}
    for key, (label, prop) in METADATA_FIELDS.items():
        if key in API_KEYS and model['data_category'] != 'api':
            continue
        value = req.metadata.get(key, '').strip()
        metadata[key] = {'label': label, 'property': prop, 'value': value or None,
                         'status': 'USER_PROVIDED' if value else 'REVIEW_REQUIRED',
                         'source': 'USER' if value else 'UNKNOWN'}
    dictionary = []
    for field in fields:
        if set(field['types']) <= {'object', 'array'}:
            continue
        annotation = req.field_annotations.get(field['path'], FieldAnnotation())
        dictionary.append({**field, 'annotation': annotation.model_dump()})
    pending = [value['label'] for value in metadata.values() if value['status'] == 'REVIEW_REQUIRED']
    for field in dictionary:
        if not field['annotation']['description']:
            pending.append(field['path'] + ': 설명/업무 의미 확인')
        if not field['annotation']['unit'] and set(field['types']) & {'integer', 'number'}:
            pending.append(field['path'] + ': 단위 확인 (무차원인 경우 명시)')
    pending += [metric['category'] + ': 품질 검증' for metric in model.get('quality_metrics', [])
                if metric.get('status') == 'REVIEW_REQUIRED']
    return {'contract_version': '1.0', 'template_id': TEMPLATE_ID,
            'title': str(model.get('title') or 'AI 친화 데이터 가이드'),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'document_status': 'REVIEW_REQUIRED' if pending else 'USER_REVIEW_PENDING',
            'analysis': model, 'metadata': metadata, 'dictionary': dictionary,
            'review_required': pending,
            'provenance_note': '분석 결과는 제출된 v2 메타데이터 기준이며 기관 입력은 USER_PROVIDED입니다. 서명 또는 기관 승인 인증이 아닙니다.'}


# XML 노드 하위의 모든 텍스트 요소를 결합하여 반환함
def _text(node):
    return '\n'.join(item.text or '' for item in node.iter(f'{{{HP}}}t'))


# XML 문단 또는 셀 노드의 텍스트를 대상 내용으로 치환함
def _replace_text(node, text):
    texts = list(node.iter(f'{{{HP}}}t'))
    if not texts:
        raise ValueError('템플릿 텍스트 셀을 찾을 수 없습니다.')
    texts[0].text = str(text)
    for item in texts[1:]:
        item.text = ''
    # Original cached line geometry belongs to the sample text.
    for item in list(node.iter(f'{{{HP}}}linesegarray')):
        item.getparent().remove(item)


# 요청 계약에 따라 HWPX 템플릿을 완성된 가이드 문서 바이너리로 렌더링함
def render_template(req: TemplateGuideRequest) -> bytes:
    contract = build_contract(req)
    model = contract['analysis']
    with DocumentPackage(TEMPLATE) as package:
        source = package.xml('Contents/section0.xml')
        parts = {name: package.read(name) for name in package.names}
    paragraphs = list(source)
    if len(paragraphs) != 96 or '작성 기준' not in _text(paragraphs[2]) or '컬럼명' not in _text(paragraphs[35]):
        raise ValueError('샘플 템플릿 구조가 변경되었습니다. 템플릿 매핑 검토가 필요합니다.')
    root = deepcopy(source)
    for child in list(root):
        root.remove(child)
    visible_blocks = []

    # 단락 프로토타입을 복제하여 텍스트를 설정하고 문서 트리에 추가함
    def paragraph(text, prototype=4):
        node = deepcopy(paragraphs[prototype])
        _replace_text(node, text)
        root.append(node)
        visible_blocks.append(str(text))

    # 소제목 서식 단락을 생성하여 문서 트리에 추가함
    def heading(text):
        paragraph('□ ' + text, 2)

    # 표 프로토타입을 복제하여 데이터 그리드 표를 생성하고 문서에 추가함
    def table(headers, rows, prototype=14):
        # Short table chunks repeat headers and avoid a single oversized inline table.
        rows = rows or [['해당 없음'] + [''] * (len(headers) - 1)]
        for start in range(0, len(rows), 12):
            wrapper = deepcopy(paragraphs[prototype])
            tbl = next(wrapper.iter(f'{{{HP}}}tbl'))
            original_rows = list(tbl.findall(f'{{{HP}}}tr'))
            head_row, body_row = original_rows[0], original_rows[1]
            for item in original_rows:
                tbl.remove(item)
            content = [headers] + rows[start:start + 12]
            total_height = 0
            for row_index, values in enumerate(content):
                tr = deepcopy(head_row if row_index == 0 else body_row)
                cells = tr.findall(f'{{{HP}}}tc')
                if len(values) != len(cells):
                    raise ValueError('템플릿 표 열 수와 데이터가 일치하지 않습니다.')
                height = 1800
                for col, (cell, value) in enumerate(zip(cells, values)):
                    _replace_text(cell, value)
                    cell.set('header', '1' if row_index == 0 else '0')
                    cell.find(f'{{{HP}}}cellAddr').set('rowAddr', str(row_index))
                    cell.find(f'{{{HP}}}cellAddr').set('colAddr', str(col))
                    width = int(cell.find(f'{{{HP}}}cellSz').get('width'))
                    # Conservative height estimate; Hancom performs final layout when opened.
                    char_capacity = max(4, (width - 1020) // 550)
                    lines = sum(max(1, (len(line) + char_capacity - 1) // char_capacity)
                                for line in str(value).split('\n'))
                    height = max(height, lines * 1400 + 600)
                for cell in cells:
                    cell.find(f'{{{HP}}}cellSz').set('height', str(height))
                total_height += height
                tbl.append(tr)
                visible_blocks.extend(str(value) for value in values)
            tbl.set('rowCnt', str(len(content)))
            tbl.set('repeatHeader', '1')
            tbl.set('pageBreak', 'CELL')
            tbl.find(f'{{{HP}}}pos').set('treatAsChar', '0')
            tbl.find(f'{{{HP}}}sz').set('height', str(total_height))
            for item in list(wrapper.iter(f'{{{HP}}}linesegarray')):
                item.getparent().remove(item)
            root.append(wrapper)

    # 메타데이터 사전에서 키에 해당하는 값을 조회하거나 기본값을 반환함
    def val(key):
        return contract['metadata'][key]['value'] or REVIEW

    title = contract['title']
    category = 'API' if model['data_category'] == 'api' else '파일데이터'
    paragraph(f'AI친화·고가치 데이터셋 가이드\n{title}\n({category} / 기관 검토용)', 0)
    heading('작성 기준 및 적용 방향')
    paragraph('사용자 제공 샘플 HWPX의 용지·글꼴·문단·표 서식을 사용하고 모든 데이터 내용은 이번 분석 결과로 바인딩했습니다.')
    paragraph('문서 상태: ' + contract['document_status'] + ' / 기관 미확인 항목이 있는 문서는 승인 완료본이 아닙니다.')
    paragraph(contract['provenance_note'])
    heading('데이터셋 개요')
    scopes = model.get('tables') or model.get('record_sets') or []
    size = '; '.join(f"{item.get('name', item.get('path', '$'))}: {item.get('row_count', item.get('count', 0)):,}건" for item in scopes) or '단일 루트 / 레코드셋 미지정'
    table(['구분', '내용', '구분', '내용'], [
        ['데이터명', title, '제공기관', val('publisher')],
        ['규모/레코드셋', size, '전체 데이터사전', f"{len(contract['dictionary'])}개 관측 값 경로"],
        ['시간 범위', val('temporal'), '대상 범위', val('spatial')],
        ['유형/형식', category + ' / ' + model['format'], '루트 타입', model['root_type']],
        ['데이터 설명', val('description'), '결합 데이터', val('source_datasets')],
    ], prototype=10)

    groups = [
        ('데이터 관리 메타데이터', ['publisher', 'description', 'department', 'legal_basis', 'landing_page', 'contact', 'update_frequency', 'temporal', 'spatial']),
        ('데이터 계보 메타데이터', ['version', 'issued', 'modified', 'source_datasets', 'transformation', 'imputation']),
        ('데이터 이용 메타데이터', ['license', 'rights']),
    ]
    for label, keys in groups:
        heading(label)
        table(['항목명', '속성', '상태', '작성 내용'], [[contract['metadata'][key]['label'], contract['metadata'][key]['property'], contract['metadata'][key]['status'], val(key)] for key in keys])

    heading('데이터 품질 메타데이터 및 검증 근거')
    rows = []
    for metric in model.get('quality_metrics', []):
        measured = metric.get('status') == 'MEASURED'
        if measured and metric.get('category') == 'COMPLETENESS':
            result = f"관측값 {metric.get('observed')} / null·빈값 {metric.get('missing')} / 점수 {metric.get('score')}"
        elif measured:
            result = dumps({key: value for key, value in metric.items() if key not in {'category', 'status', 'scope'}})
        else:
            result = REVIEW
        rows.append([metric.get('category', ''), metric.get('scope', '업무 기준·정답·기준일 필요'), metric.get('status', 'REVIEW_REQUIRED'), result])
    table(['품질지표', '측정 범위/근거', '상태', '결과'], rows, 38)
    paragraph('입력값 채움률은 업로드 데이터에서 null·빈 문자열이 아닌 관측값의 비율이며 정확성이나 대표성을 의미하지 않습니다. 중복·보정 플래그·기간·업무 규칙은 실제 검사를 실행한 경우에만 확정할 수 있습니다.')
    for warning in model.get('warnings', []):
        paragraph(warning)

    heading('전체 필드 데이터사전')
    paragraph('대표 필드가 아닌 전체 관측 값 경로입니다. 원천 자료형과 업무상 의미 타입·단위는 구분합니다. *는 배열 관측 경로이며 실행 가능한 JSON Pointer가 아닙니다.')
    rows = []
    for field in contract['dictionary']:
        annotation = field['annotation']
        rows.append([annotation['label'] or field['path'], field['path'],
                     ' | '.join(field['types']) + '\n단위: ' + (annotation['unit'] or REVIEW),
                     (annotation['description'] or REVIEW) + '\n코드: ' + (annotation['codes'] or '미정/해당 여부 확인')])
    table(['필드명/표시명', '원천 구조 경로', '관측 타입·단위', '설명·코드'], rows, 35)
    heading('필드별 관측 통계')
    table(['구조 경로', '관측/누락', 'null/빈 문자열', '관측 예시 (최대 160자)'], [
        [f['path'], f"{f['occurrences']} / {f.get('missing_count', '미측정')}",
         f"{f['null_count']} / {f['empty_count']}", _value_text(f.get('examples', []))[:160]]
        for f in contract['dictionary']], 35)

    heading('세부 데이터셋 구조 및 파싱 계약')
    paragraph('원천 경로·배열·컨테이너·namespace 정보는 HWPX 내부 AIReady/metadata.json에 함께 저장됩니다.')
    table(['구조 경로', '타입', '관측 횟수', '구분'], [[f['path'], ' | '.join(f['types']), str(f['occurrences']), '컨테이너' if set(f['types']) <= {'object', 'array'} else '값'] for f in model['fields']], 35)
    paragraph('JSON-LD는 @context·@graph·@id·@type·@value·@list 구조를 보존하고 원격 context 의미 검증은 별도로 수행합니다.')
    paragraph('XML은 {URI}local QName, 속성, 반복 요소, 혼합 텍스트, xsi:nil을 구분하며 공식 XSD 적합성을 자동 보증하지 않습니다.')
    if model.get('namespace_bindings'):
        table(['접두사', 'Namespace URI', '범위', '검토'], [[item['prefix'], item['uri'], '관측 namespace', 'QName 기준 구분'] for item in model['namespace_bindings']])
    if model['data_category'] == 'api':
        heading('1.1 공공데이터 오픈API 조회 서비스')
        heading('가. API 서비스 개요')
        table(['항목명', '속성', '구분', '작성 내용'], [
            [contract['metadata'][key]['label'], contract['metadata'][key]['property'],
             contract['metadata'][key]['status'], val(key)]
            for key in API_FIELD_ORDER
        ])
        heading('나. 응답 필드 및 샘플데이터')
        response_rows = []
        for field in contract['dictionary']:
            annotation = field['annotation']
            sample = _value_text(field.get('examples', []))[:160]
            response_rows.append([
                annotation['label'] or field['path'], field['path'],
                ' | '.join(field['types']) + '\n단위: ' + (annotation['unit'] or REVIEW),
                sample + '\n' + (annotation['description'] or REVIEW),
            ])
        table(['항목명(영문/표시명)', '응답 경로', '관측 타입·단위', '샘플데이터·항목설명'], response_rows)
        heading('다. 요청·응답·오류 계약')
        table(['항목명', '속성', '상태', '작성 내용'], [
            [contract['metadata'][key]['label'], contract['metadata'][key]['property'],
             contract['metadata'][key]['status'], val(key)]
            for key in ('request_parameters', 'pagination', 'rate_limit', 'response_path', 'error_codes',
                        'sample_request', 'sample_response_xml', 'sample_response_json')
        ])
        paragraph('응답 데이터만으로 서비스 URL·인증·요청 필수값을 확정하지 않습니다. 실제 비밀키·토큰·개인정보는 샘플에서 제거하고 기관 계약 확인 상태를 유지합니다.')
    else:
        heading('파일 적재·변환 지침')
        paragraph('CSV/TSV는 구분자·인용 개행·UTF-8 처리를 확인하고 XLSX는 시트와 헤더를 유지합니다. 수식을 임의 계산하거나 null·빈값을 0으로 대체하지 않습니다.')

    heading('데이터셋 활용도 및 한계')
    table(['항목명', '속성', '상태', '작성 내용'], [[contract['metadata'][key]['label'], contract['metadata'][key]['property'], contract['metadata'][key]['status'], val(key)] for key in ['training_split', 'limitations']])
    heading('기관 확인 및 발간 전 점검')
    table(['번호', '확인 대상', '상태', '처리 기준'], [[str(i + 1), item, 'REVIEW_REQUIRED', '근거 자료 확인 후 재생성'] for i, item in enumerate(contract['review_required'])])
    paragraph('기관 입력은 USER_PROVIDED로 기록하며 자동 승인하지 않습니다. 최종 발간 전 담당자 검토와 한컴 페이지 배치 확인이 필요합니다.')
    heading('문서·원본 식별 및 재현 정보')
    contract['template_sha256'] = hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    contract['binding_sha256'] = _contract_hash(contract)
    table(['항목', '값', '출처', '비고'], [
        ['원본 해시', model['sha256'], '분석 결과', 'XLSX 원본 바이트 / 텍스트 제출 UTF-8 바이트'],
        ['분석 바이트', str(model['byte_size']), '분석 결과', '원본 파일 인코딩과 구분'],
        ['생성 시각', contract['created_at'], '시스템 UTC', '원천 공개/수정일과 구분'],
        ['템플릿 ID', TEMPLATE_ID, '시스템', '사용자 샘플 기반'],
        ['템플릿 SHA-256', contract['template_sha256'], '시스템', '서식 버전 추적'],
        ['메타데이터 SHA-256', contract['binding_sha256'], '시스템', '본문과 내부 계약의 양방향 일치 확인'],
    ])
    heading('참고 기준')
    paragraph('사용자 제공: 한국지역난방공사_AI친화_고가치_데이터셋_샘플가이드.hwpx (서식 출처)')
    paragraph('공공데이터의 인공지능 친화적 관리 가이드라인 v1.1 / AI 데이터 품질관리·구축 가이드. 규격 준수 인증을 의미하지 않습니다.')
    paragraph('<끝>')

    # Give generated control and paragraph instances unique IDs; retain shared style IDs.
    for index, node in enumerate(root.iter(), 1):
        if node.tag in {f'{{{HP}}}p', f'{{{HP}}}tbl'}:
            node.set('id', str(index))
    contract['visible_text_sha256'] = hashlib.sha256(_text(root).encode()).hexdigest()
    parts['Contents/section0.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    parts['AIReady/metadata.json'] = dumps(contract).encode('utf-8')
    parts['Preview/PrvText.txt'] = '\n'.join(visible_blocks).encode('utf-8')
    # A stale thumbnail could otherwise still display sample facts.
    parts.pop('Preview/PrvImage.png', None)
    hpf = etree.fromstring(parts['Contents/content.hpf'])
    for node in hpf.findall(f'.//{{{OPF}}}metadata/*'):
        local = etree.QName(node).localname
        if local == 'title': node.text = title
        elif node.get('name') in {'creator', 'subject', 'description', 'keyword'}: node.text = ''
        elif node.get('name') in {'CreatedDate', 'ModifiedDate', 'date'}: node.text = contract['created_at']
    manifest = hpf.find(f'{{{OPF}}}manifest')
    etree.SubElement(manifest, f'{{{OPF}}}item', id='aiReadyMetadata', href='AIReady/metadata.json', **{'media-type': 'application/json'})
    parts['Contents/content.hpf'] = etree.tostring(hpf, xml_declaration=True, encoding='UTF-8')
    manifest = etree.fromstring(parts['META-INF/manifest.xml'])
    etree.SubElement(manifest, f'{{{ODF}}}file-entry', **{f'{{{ODF}}}full-path': 'AIReady/metadata.json', f'{{{ODF}}}media-type': 'application/json'})
    parts['META-INF/manifest.xml'] = etree.tostring(manifest, xml_declaration=True, encoding='UTF-8')
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('mimetype', parts.pop('mimetype'), compress_type=ZIP_STORED)
        for name, content in parts.items():
            archive.writestr(name, content)
    result = output.getvalue()
    # Same independent parser as the guide tab; parsing also checks table grid integrity.
    parsed = parse_generated_template(result)
    if parsed['analysis']['sha256'] != model['sha256']:
        raise ValueError('HWPX 재파싱 원본 해시가 일치하지 않습니다.')
    return result


# 계약 객체에서 해시 필드를 제외한 핵심 데이터의 SHA-256 해시를 계산함
def _contract_hash(contract):
    core = {key: value for key, value in contract.items() if key not in {'binding_sha256', 'visible_text_sha256'}}
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


# 생성된 HWPX 가이드 바이너리를 파싱하고 무결성을 검증함
def parse_generated_template(data: bytes) -> dict:
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('HWPX는 32 MiB 이하여야 합니다.')
    with TemporaryDirectory() as directory:
        path = Path(directory) / 'guide.hwpx'
        path.write_bytes(data)
        document = HwpxParser().parse(path)
        if not document.sections:
            raise ValueError('HWPX 본문이 없습니다.')
        with DocumentPackage(path) as package:
            if 'AIReady/metadata.json' not in package.names:
                raise ValueError('AI가이드 생성 메타데이터가 없습니다. 샘플 원본이 아닌 생성된 HWPX를 선택하세요.')
            contract = json.loads(package.read('AIReady/metadata.json'))
            if contract.get('contract_version') != '1.0' or contract.get('template_id') != TEMPLATE_ID:
                raise ValueError('지원하지 않는 템플릿 계약 버전입니다.')
            visible_text = _text(package.xml('Contents/section0.xml'))
            binding_hash = _contract_hash(contract)
            if binding_hash != contract.get('binding_sha256') or binding_hash not in visible_text:
                raise ValueError('HWPX 본문과 내부 메타데이터가 불일치합니다. 메타데이터가 변경되었습니다.')
            text_hash = hashlib.sha256(visible_text.encode()).hexdigest()
            if text_hash != contract.get('visible_text_sha256'):
                raise ValueError('HWPX 본문과 내부 메타데이터가 불일치합니다. 기관 입력을 반영하여 다시 생성하세요.')
            return contract
