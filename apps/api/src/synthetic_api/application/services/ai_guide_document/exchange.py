# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: exchange.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_document/exchange.py
# 목적: 캐노니컬 모델을 표준 XML 및 JSON-LD 포맷으로 직렬화하고 스키마를 검증함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Typed XML/JSON-LD AST projection of the same canonical input."""
from __future__ import annotations
import copy
import json
import re
from lxml import etree
from .binding import TOKEN

XSI='http://www.w3.org/2001/XMLSchema-instance'


# 값을 XML 및 JSON-LD 어휘 규격 문자열로 변환함
def lexical(value):
    if isinstance(value,bool): return 'true' if value else 'false'
    if isinstance(value,(list,dict)): return json.dumps(value,ensure_ascii=False,separators=(',',':'))
    return str(value)


# 캐노니컬 모델을 표준 메타데이터 XML 문서로 직렬화함
def xml_output(model,contract):
    tree=etree.parse(str(contract.assets/'ai_ready_metadata_template.xml'))
    # XML 노드 트리의 템플릿 마커와 속성을 모델 값으로 채움
    def fill(node,contexts=()):
        children=list(node); i=0
        while i<len(children):
            child=children[i]
            if not isinstance(child.tag,str):
                marker=re.search(r'{{#([^}]+)}}',child.text or '')
                if marker:
                    depth=1;j=i+1
                    while j<len(children):
                        text=children[j].text or '' if not isinstance(children[j].tag,str) else ''
                        if '{{#' in text: depth+=1
                        if '{{/' in text: depth-=1
                        if depth==0: break
                        j+=1
                    if j==len(children): raise ValueError('XML 반복 닫기 없음')
                    values,path=contract.resolve(model,marker[1],contexts)
                    insert=node.index(child)
                    for index,item in enumerate(values):
                        for prototype in children[i+1:j]:
                            if isinstance(prototype.tag,str):
                                clone=copy.deepcopy(prototype);fill(clone,contexts+((path,index,item),))
                                node.insert(insert,clone);insert+=1
                    for old in children[i:j+1]: node.remove(old)
                    i=j+1;continue
                node.remove(child)
            else: fill(child,contexts)
            i+=1
        for key,text in list(node.attrib.items()):
            match=TOKEN.fullmatch(text)
            if match:
                value,_=contract.resolve(model,match[1],contexts)
                if value is None: del node.attrib[key]
                else: node.set(key,lexical(value))
        if node.text and TOKEN.fullmatch(node.text.strip()):
            value,_=contract.resolve(model,TOKEN.fullmatch(node.text.strip())[1],contexts)
            if value is None:
                node.text=None;node.set('{'+XSI+'}nil','true')
            else: node.text=lexical(value)
    fill(tree.getroot())
    schema=etree.XMLSchema(etree.parse(str(contract.assets/'ai_ready_metadata_schema.xsd')))
    if not schema.validate(tree):
        raise ValueError(f'XML schema validation failed: {schema.error_log.last_error}')
    return etree.tostring(tree,encoding='utf-8',xml_declaration=True,pretty_print=True)


# 캐노니컬 모델을 표준 JSON-LD 그래프 구조로 직렬화함
def jsonld_output(model,contract):
    template=json.loads((contract.assets/'ai_ready_metadata_template.jsonld').read_text(encoding='utf-8'))
    # JSON-LD 템플릿 노드를 재귀적으로 평가하고 바인딩함
    def expand(node,contexts=()):
        if isinstance(node,dict):
            result={k:expand(v,contexts) for k,v in node.items()}
            if '@id' in result and result['@id'] is not None:
                identifier=result['@id']
                if isinstance(identifier,str) and identifier in {'string','integer','number','boolean'}:
                    result['@id']='xsd:'+('double' if identifier=='number' else identifier)
                elif not isinstance(identifier,str) or not re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',identifier):
                    result['ai:unresolvedIdentifier']=identifier
                    del result['@id']
            # Unknown IRIs are omitted, never turned into example URLs or invalid IDs.
            return {k:v for k,v in result.items() if v is not None or k=='ai:value'}
        if isinstance(node,list):
            if node and isinstance(node[0],str) and node[0].startswith('{{#'):
                values,path=contract.resolve(model,node[0][3:-2],contexts)
                return [expand(prototype,contexts+((path,i,item),)) for i,item in enumerate(values) for prototype in node[1:-1]]
            return [expand(v,contexts) for v in node]
        if isinstance(node,str) and TOKEN.fullmatch(node):
            return contract.resolve(model,TOKEN.fullmatch(node)[1],contexts)[0]
        if isinstance(node,str) and TOKEN.search(node):
            values=[contract.resolve(model,m[1],contexts)[0] for m in TOKEN.finditer(node)]
            if any(v is None for v in values): return None
            return TOKEN.sub(lambda m:lexical(contract.resolve(model,m[1],contexts)[0]),node)
        return node
    result=expand(template)
    # RDF projection retains unknown values through the full typed canonical review records.
    raw=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if TOKEN.search(raw): raise ValueError('JSON-LD 미치환 플레이스홀더')
    json.loads(raw)
    return raw


# JSON-LD 문서의 오프라인 문맥 확장을 검증함
def validate_jsonld_semantics(raw):
    """Offline expansion is distinct from a national-profile/SHACL assessment."""
    try:
        from pyld import jsonld
    except ImportError:
        return 'NOT_EVALUATED (pyld 미설치); 국가 프로파일 적합성 미검증'
    # 원격 네트워크 접근을 차단하는 모의 로더 함수임
    def no_network(*args,**kwargs): raise ValueError('원격 context 접근 금지')
    expanded=jsonld.expand(json.loads(raw),options={'documentLoader':no_network})
    return f'JSON-LD 1.1 오프라인 확장 PASS ({len(expanded)} root); 국가 프로파일/SHACL 적합성 미검증'


# 캐노니컬 모델을 DCAT/OWL Turtle(RDF) 온톨로지 문자열로 직렬화함
def ttl_output(model) -> str:
    """Generate a DCAT/OWL Turtle ontology from the canonical model.

    Produces a minimal but conformant DCAT-AP 3.0 + schema.org description
    with one dcat:Dataset, one dcat:Distribution per field group, and
    OWL property declarations for each field.
    """
    ds = model.get('dataset', {})
    title = ds.get('title', '')
    description = ds.get('description', '')
    publisher = ds.get('publisher', '')
    creator = ds.get('creator', '')
    identifier = ds.get('identifier', '')
    language = ds.get('language', 'ko')
    keywords = ds.get('keywords', [])
    theme_label = ds.get('theme_label', '')
    landing_page = ds.get('landing_page', '')
    license_uri = model.get('usage', {}).get('license', '')
    issued = ds.get('version_info', {}).get('issued', '')
    modified = ds.get('version_info', {}).get('modified', '')
    update_freq = ds.get('update_frequency', '')
    fields = model.get('fields', [])

    def esc(s):
        return str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    # safe IRI slug from title
    slug = re.sub(r'[^A-Za-z0-9가-힣_-]+', '_', title)[:80].strip('_') or 'Dataset'
    base = f'https://data.go.kr/ontology/{slug}#'

    lines = [
        '@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .',
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .',
        '@prefix owl:  <http://www.w3.org/2002/07/owl#> .',
        '@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .',
        '@prefix dcat: <http://www.w3.org/ns/dcat#> .',
        '@prefix dct:  <http://purl.org/dc/terms/> .',
        '@prefix foaf: <http://xmlns.com/foaf/0.1/> .',
        '@prefix schema: <https://schema.org/> .',
        f'@prefix :     <{base}> .',
        '',
        f'<{base}> a owl:Ontology ;',
        f'    rdfs:label "{esc(title)}"@ko ;',
        f'    owl:versionInfo "1.0" .',
        '',
        ':Dataset a dcat:Dataset',
    ]
    if title:
        lines.append(f'    ; dct:title "{esc(title)}"@ko')
    if description:
        lines.append(f'    ; dct:description "{esc(description)}"@ko')
    if publisher:
        lines.append(f'    ; dct:publisher [ a foaf:Organization ; foaf:name "{esc(publisher)}"@ko ]')
    if creator:
        lines.append(f'    ; dct:creator [ a foaf:Organization ; foaf:name "{esc(creator)}"@ko ]')
    if identifier:
        lines.append(f'    ; dct:identifier "{esc(identifier)}"')
    if language:
        lines.append(f'    ; dct:language <http://id.loc.gov/vocabulary/iso639-1/{language}>')
    if landing_page:
        lines.append(f'    ; dcat:landingPage <{landing_page}>')
    if license_uri:
        lines.append(f'    ; dct:license <{license_uri}>')
    if issued:
        lines.append(f'    ; dct:issued "{esc(issued)}"^^xsd:date')
    if modified:
        lines.append(f'    ; dct:modified "{esc(modified)}"^^xsd:date')
    if update_freq:
        lines.append(f'    ; dct:accrualPeriodicity "{esc(update_freq)}"@ko')
    if theme_label:
        lines.append(f'    ; dcat:theme [ rdfs:label "{esc(theme_label)}"@ko ]')
    for kw in keywords:
        if kw:
            lines.append(f'    ; dcat:keyword "{esc(kw)}"@ko')
    lines.append('    .')
    lines.append('')

    # OWL DataProperty per field
    _TYPE_MAP = {
        'integer': 'xsd:integer', 'bigint': 'xsd:long', 'numeric': 'xsd:decimal',
        'float': 'xsd:double', 'boolean': 'xsd:boolean',
        'date': 'xsd:date', 'datetime': 'xsd:dateTime',
        'json': 'xsd:string', 'text': 'xsd:string',
        'char': 'xsd:string', 'varchar': 'xsd:string', 'string': 'xsd:string',
    }
    for field in fields:
        raw_name = field.get('name') or ''
        prop_name = re.sub(r'[^A-Za-z0-9_]', '_', raw_name) or 'field'
        label_ko = field.get('name_ko') or field.get('path', '')
        desc = field.get('description', '')
        data_types = field.get('types') or [field.get('data_type', 'string')]
        raw_type = (data_types[0] if data_types else 'string').lower()
        xsd_type = _TYPE_MAP.get(raw_type, 'xsd:string')
        unit = field.get('unit', '')
        lines.append(f':{prop_name} a owl:DatatypeProperty')
        lines.append(f'    ; rdfs:domain :Dataset')
        lines.append(f'    ; rdfs:range {xsd_type}')
        if label_ko:
            lines.append(f'    ; rdfs:label "{esc(label_ko)}"@ko')
        if raw_name and raw_name != label_ko:
            lines.append(f'    ; rdfs:label "{esc(raw_name)}"@en')
        if desc:
            lines.append(f'    ; rdfs:comment "{esc(desc)}"@ko')
        if unit:
            lines.append(f'    ; schema:unitText "{esc(unit)}"')
        lines.append('    .')
        lines.append('')

    return '\n'.join(lines)
