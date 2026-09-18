# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: public_data_parsing.py
# 경로: apps/api/src/synthetic_api/application/services/public_data_parsing.py
# 목적: JSON·XML 레코드를 공통 응답 모델로 읽고 중첩 구조를 보존하여 직렬화함
# 작성자: 개발팀
# 작성일: 2026-09-17
# 수정일: 2026-09-17
# =============================================================================
"""Loss-aware structured dataset parsing; never guesses field types or ambiguous tables."""
from __future__ import annotations

import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

XSI = 'http://www.w3.org/2001/XMLSchema-instance'
JSON_TYPES = 'urn:synthetic-studio:json-types:v1'
TYPE = '{' + JSON_TYPES + '}type'
NIL = '{' + XSI + '}nil'
TAG = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]*\Z', re.ASCII)


# 접두사 표기와 무관하게 구조 제어 요소의 로컬 이름을 비교함
def _local(tag):
    return tag.rsplit('}', 1)[-1]


# 명시적 오류와 중복 키를 조용한 덮어쓰기 대신 반환함
def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'중복 JSON 키는 허용하지 않습니다: {key}')
        result[key] = value
    return result


# 비표준 JSON 숫자는 형식 간 보존이 불가능하므로 거부함
def _bad_number(value):
    raise ValueError(f'유효하지 않은 JSON 숫자입니다: {value}')


# 문자열 형태의 숫자·boolean을 근거 없이 타입 추론하지 않음
def _xml_value(element):
    children = list(element)
    text = element.text or ''
    kind = element.attrib.get(TYPE)
    attributes = {'@' + k: v for k, v in element.attrib.items() if k not in {TYPE, NIL}}
    if element.attrib.get(NIL) in {'true', '1'}:
        if children or text or attributes:
            raise ValueError('xsi:nil 요소에 값 또는 속성이 함께 존재합니다.')
        return None
    if children and (text.strip() or any((c.tail or '').strip() for c in children)):
        raise ValueError('혼합 텍스트 XML은 데이터 표로 안전하게 변환할 수 없습니다.')
    if kind == 'array':
        if attributes or text.strip() or any(_local(c.tag) != 'item' for c in children):
            raise ValueError('배열 타입 XML 구조가 올바르지 않습니다.')
        return [_xml_value(c) for c in children]
    if kind in {'integer', 'number', 'boolean'}:
        if children or attributes:
            raise ValueError('단일 값 XML 타입에 자식 요소 또는 속성이 존재합니다.')
        if kind == 'boolean':
            if text not in {'true', 'false'}:
                raise ValueError('boolean 타입 XML 값이 올바르지 않습니다.')
            return text == 'true'
        try:
            value = int(text) if kind == 'integer' else float(text)
        except ValueError as exc:
            raise ValueError('숫자 타입 XML 값이 올바르지 않습니다.') from exc
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('NaN/Infinity는 지원하지 않습니다.')
        return value
    if kind not in {None, 'object'}:
        raise ValueError('지원하지 않는 XML 변환 타입입니다.')
    if not children and not attributes and kind != 'object':
        return text
    result = dict(attributes)
    grouped = {}
    for child in children:
        # 기존 records/record/field 구조 및 XML 이름으로 표현할 수 없는 JSON 키를 보존함
        encoded = _local(child.tag) == 'field' and set(child.attrib) <= {'name', TYPE, NIL} and 'name' in child.attrib
        key = child.attrib['name'] if encoded else child.tag
        if encoded:
            clean = deepcopy(child)
            del clean.attrib['name']
            value = _xml_value(clean)
        else:
            value = _xml_value(child)
        grouped.setdefault(key, []).append(value)
    for key, values in grouped.items():
        if key in result:
            raise ValueError('XML 속성과 요소의 변환 키가 충돌합니다.')
        result[key] = values[0] if len(values) == 1 else values
    if text.strip() or (not children and attributes):
        if '#text' in result:
            raise ValueError('XML 텍스트의 변환 키가 충돌합니다.')
        result['#text'] = text
    return result


# 네임스페이스로 구분된 동일 로컬 키를 임의 병합하지 않음
def _named(mapping, name):
    keys = [k for k in mapping if _local(k) == name] if isinstance(mapping, dict) else []
    if len(keys) > 1:
        raise ValueError(f'네임스페이스가 다른 {name} 요소를 구분해야 합니다.')
    return mapping[keys[0]] if keys else None


# 알려진 공공데이터 items/item 변형을 단일한 레코드 목록으로 정규화함
def _items(value, xml=False):
    if isinstance(value, dict):
        item = _named(value, 'item')
        if item is not None and len(value) == 1:
            value = item if isinstance(item, list) else [item]
        elif xml:
            raise ValueError('items 컨테이너에 item 외의 요소가 있습니다.')
    elif xml and value == '':
        value = []
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError('데이터 목록은 객체 레코드의 배열이어야 합니다.')
    return value


# JSON Pointer 형식으로 선택한 데이터 경로를 조회함
def _pointer(value, path):
    if path in {'', '$'}:
        return value
    if not path.startswith('/'):
        raise ValueError('record_path는 /data/items 같은 JSON Pointer 경로여야 합니다.')
    for token in path[1:].split('/'):
        key = token.replace('~1', '/').replace('~0', '~')
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f'데이터 경로를 찾을 수 없습니다: {path}')
        value = value[key]
    return value


# 한 데이터 목록을 찾되 여러 후보가 있으면 경로 지정을 요구함
def _find_records(value, path=''):
    if isinstance(value, list):
        if all(isinstance(row, dict) for row in value):
            return [(path, value)]
        return []
    if not isinstance(value, dict):
        return []
    # 코드·이름 등 단일 레코드의 속성과 함께 있는 내부 객체 배열을 표로 오인하지 않음
    known_containers = {'items', 'item', 'rows', 'row', 'records', 'record', 'data', 'results', 'result', 'response'}
    scalar_fields = any(not isinstance(c, (list, dict)) for c in value.values())
    has_container = any(_local(k) in known_containers and isinstance(c, (list, dict)) for k, c in value.items())
    if scalar_fields and not has_container:
        return []
    candidates = []
    for key, child in value.items():
        escaped = key.replace('~', '~0').replace('/', '~1')
        # 객체 배열의 내부 배열은 별도 테이블 후보로 탐색하지 않음
        if isinstance(child, (list, dict)):
            candidates.extend(_find_records(child, path + '/' + escaped))
    return candidates


# 파서 이후에도 중첩 깊이·비유한 숫자를 검증하여 직렬화 단계의 손실을 방지함
def _validate_tree(value):
    pending = [(value, 0)]
    count = 0
    while pending:
        child, depth = pending.pop()
        count += 1
        if depth > 128 or count > 2_000_000:
            raise ValueError('데이터 중첩 깊이 또는 요소 수가 허용 한도를 초과했습니다.')
        if isinstance(child, float) and not math.isfinite(child):
            raise ValueError('NaN/Infinity는 지원하지 않습니다.')
        if isinstance(child, dict):
            pending.extend((v, depth + 1) for v in child.values())
        elif isinstance(child, list):
            pending.extend((v, depth + 1) for v in child)


# 선택한 목록 밖의 원본 메타데이터를 다운로드 가능한 보조 문서에 남김
def _outside_records(value, path):
    if path in {'', '$'}:
        return None
    result = deepcopy(value)
    parent_path, _, leaf = path.rpartition('/')
    parent = _pointer(result, parent_path)
    del parent[leaf.replace('~1', '/').replace('~0', '~')]
    return result


def read_structured_source(raw, filename, record_path=None):
    """JSON/XML 입력에서 레코드와 원본 응답 페이지 메타데이터를 읽음

    Args:
        raw: 업로드 바이트, 최대 100 MiB
        filename: JSON 또는 XML 파일명
        record_path: 모호한 구조의 레코드 선택 경로, JSON Pointer 형식
    Returns:
        headers, rows, items, envelope, record_path 및 source_metadata
    Raises:
        ValueError: 중복 키, 모호한 목록, 혼합 XML 또는 크기 한도 초과
    """
    if len(raw) > 100 * 1024 * 1024:
        raise ValueError('입력 파일 한도는 100 MiB입니다.')
    xml = Path(filename).suffix.lower() == '.xml'
    try:
        if xml:
            # UTF-16/32의 NUL 바이트 우회를 포함하여 DTD·엔터티 정의를 차단함
            normalized = raw.replace(b'\x00', b'').upper()
            if b'<!DOCTYPE' in normalized or b'<!ENTITY' in normalized:
                raise ValueError('DTD 또는 외부 엔터티가 포함된 XML은 지원하지 않습니다.')
            root = ET.fromstring(raw)
            stack = [(root, 0)]
            count = 0
            while stack:
                node, depth = stack.pop()
                count += 1
                if count > 1_000_000 or depth > 128:
                    raise ValueError('XML 노드 수 또는 중첩 깊이가 허용 범위를 초과했습니다.')
                stack.extend((c, depth + 1) for c in node)
            value = {_local(root.tag): _xml_value(root)}
        else:
            value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object, parse_constant=_bad_number)
        _validate_tree(value)
        response = _named(value, 'response')
        direct_response = False
        if response is None:
            candidate = next(iter(value.values())) if xml else value
            candidate_body = _named(candidate, 'body')
            if isinstance(candidate_body, dict) and any(_local(k) == 'items' for k in candidate_body):
                response = candidate
                direct_response = True
        body = _named(response, 'body')
        header = _named(response, 'header')
        envelope = None
        if isinstance(body, dict) and any(_local(k) == 'items' for k in body):
            if xml and header == '':
                header = {}
            if header is not None and not isinstance(header, dict):
                raise ValueError('응답 header는 객체 또는 null이어야 합니다.')
            records = _items(_named(body, 'items'), xml)
            envelope = deepcopy(value) if not xml and not direct_response else {'response': deepcopy(response)}
            if not xml and not direct_response:
                envelope.pop(next(k for k in value if _local(k) == 'response'))
            normalized_body = dict(body)
            normalized_body.pop(next(k for k in body if _local(k) == 'items'))
            normalized_body['items'] = records
            # 페이지 제어 값만 구조의 정수 타입으로 읽고 업무 필드는 문자열로 유지함
            for key in ('totalCount', 'pageNo', 'numOfRows'):
                original_key = next((k for k in normalized_body if _local(k) == key), None)
                if original_key is not None:
                    number = normalized_body.pop(original_key)
                    if xml:
                        if isinstance(number, str) and re.fullmatch(r'\d+', number):
                            number = int(number)
                    if type(number) is not int or number < 0:
                        raise ValueError(f'{key}는 음이 아닌 정수여야 합니다.')
                    normalized_body[key] = number
            normalized_body = {
                **{k: normalized_body[k] for k in ('totalCount', 'pageNo', 'numOfRows') if k in normalized_body},
                **{k: v for k, v in normalized_body.items() if k not in {'totalCount', 'pageNo', 'numOfRows', 'items'}},
                'items': records,
            }
            envelope['response'] = dict(response)
            for name in ('header', 'body'):
                original_key = next((k for k in response if _local(k) == name), None)
                if original_key is not None:
                    envelope['response'].pop(original_key)
            envelope['response'].update(header=header, body=normalized_body)
            selected = '/response/body/items'
            if record_path not in {None, selected}:
                raise ValueError('공공데이터 응답의 record_path는 /response/body/items입니다.')
        else:
            if record_path is not None:
                chosen = _pointer(value, record_path)
                records = chosen if isinstance(chosen, list) else [chosen]
                selected = record_path
            else:
                candidates = _find_records(value)
                if len(candidates) > 1:
                    paths = ', '.join(p for p, _ in candidates[:10])
                    raise ValueError(f'데이터 목록이 여러 개입니다. record_path를 지정하세요: {paths}')
                if candidates:
                    selected, records = candidates[0]
                else:
                    chosen = next(iter(value.values())) if xml else value
                    selected = '/' + next(iter(value)) if xml else ''
                    # 단일 레코드 컨테이너만 펼치고 업무 필드의 중첩 구조는 유지함
                    while xml and isinstance(chosen, dict) and len(chosen) == 1 and _local(next(iter(chosen))) in {'items', 'rows', 'records', 'item', 'row', 'record'} and isinstance(next(iter(chosen.values())), dict):
                        key, chosen = next(iter(chosen.items()))
                        selected += '/' + key.replace('~', '~0').replace('/', '~1')
                    records = [] if xml and chosen == '' and _local(root.tag) in {'items', 'rows', 'records'} else [chosen]
            if any(not isinstance(row, dict) for row in records):
                raise ValueError('선택한 경로는 객체 또는 객체 레코드의 배열이어야 합니다.')
        headers = list(dict.fromkeys(k for row in records for k in row))
        if len(records) * max(1, len(headers)) > 2_000_000:
            raise ValueError('한 번에 변환할 수 있는 셀 수는 2,000,000개입니다.')
        return dict(headers=headers, rows=[[row.get(k) for k in headers] for row in records],
                    items=records, envelope=envelope, sheets=[], sheet_name=None, record_path=selected,
                    source_metadata=_outside_records(value, selected) if envelope is None else None)
    except RecursionError as exc:
        raise ValueError('입력 데이터의 중첩 깊이가 너무 큽니다.') from exc


# XML 제어문자를 제거하여 값을 조작하지 않고 입력 오류를 반환함
def _safe_text(value):
    if any(not (ord(c) in (9, 10, 13) or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise ValueError('XML 1.0에서 허용하지 않는 제어문자가 원천 값에 포함되어 있습니다.')
    return value


# XML 이름으로 표현할 수 없는 JSON 키는 name 속성을 갖는 field로 보존함
def _child(parent, key):
    if TAG.fullmatch(key):
        return ET.SubElement(parent, key)
    return ET.SubElement(parent, 'field', {'name': _safe_text(key)})


# 명시적 타입 표시로 null·빈 객체·빈 배열과 문자열 숫자를 구분함
def _write_value(element, value):
    if value is None:
        element.set(NIL, 'true')
    elif isinstance(value, dict):
        if not value:
            element.set(TYPE, 'object')
        for key, child in value.items():
            _write_value(_child(element, key), child)
    elif isinstance(value, list):
        element.set(TYPE, 'array')
        for child in value:
            _write_value(ET.SubElement(element, 'item'), child)
    elif isinstance(value, bool):
        element.set(TYPE, 'boolean')
        element.text = 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('NaN/Infinity는 지원하지 않습니다.')
        element.set(TYPE, 'integer' if isinstance(value, int) else 'number')
        element.text = str(value)
    elif isinstance(value, str):
        element.text = _safe_text(value)
    else:
        raise ValueError('지원하지 않는 JSON 타입입니다.')


def public_xml(payload):
    """공통 응답 모델을 CCTV의 items/item XML 구조로 직렬화함

    Args:
        payload: response.header/body/items 공통 모델
    Returns:
        UTF-8 XML 바이트, 중첩 값과 원래 JSON 타입 보존
    Raises:
        ValueError: 잘못된 키·타입 또는 XML 금지 문자
    """
    root = ET.Element('response')
    response = payload['response']
    response_keys = [k for k in ('header', 'body') if k in response] + [k for k in response if k not in {'header', 'body'}]
    for key in response_keys:
        value = response[key]
        if key != 'body':
            _write_value(_child(root, key), value)
            continue
        body = ET.SubElement(root, 'body')
        body_keys = [k for k in ('totalCount', 'pageNo', 'numOfRows') if k in value] + [k for k in value if k not in {'totalCount', 'pageNo', 'numOfRows', 'items'}] + ['items']
        for name in body_keys:
            data = value[name]
            child = _child(body, name)
            if name == 'items':
                for row in data:
                    item = ET.SubElement(child, 'item')
                    _write_value(item, row)
            elif name in {'totalCount', 'pageNo', 'numOfRows'} and type(data) is int:
                child.text = str(data)
            else:
                _write_value(child, data)
    # 공공데이터 응답의 중첩 트리를 사람이 확인할 수 있도록 들여쓴 XML로 출력함.
    # ET.indent는 요소 사이에만 공백을 추가하므로 leaf 요소의 실제 값은 변경하지 않음.
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def table_rows(source):
    """중첩 셀을 JSON 텍스트로 인코딩하여 2차원 표에 보존함

    Args:
        source: 구조화 입력 파서의 결과
    Returns:
        컬럼 순서대로 나열한 표의 행
    """
    return [[json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (dict, list))
             else 'true' if v is True else 'false' if v is False else v
             for v in row] for row in source['rows']]


def write_public_csv(source, path):
    """타입 추론 없이 값과 열 순서를 유지하여 표준 CSV를 저장함

    Args:
        source: 구조화 입력 파서의 결과
        path: 출력 파일 경로
    Returns:
        None
    """
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(source['headers'])
        writer.writerows(table_rows(source))
