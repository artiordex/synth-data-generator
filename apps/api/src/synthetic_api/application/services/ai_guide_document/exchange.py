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
    tree=etree.parse(str(contract.assets/'AI친화_메타데이터_템플릿.xml'))
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
    schema=etree.XMLSchema(etree.parse(str(contract.assets/'AI친화_메타데이터_스키마.xsd')))
    schema.assertValid(tree)
    return etree.tostring(tree,encoding='utf-8',xml_declaration=True,pretty_print=True)


# 캐노니컬 모델을 표준 JSON-LD 그래프 구조로 직렬화함
def jsonld_output(model,contract):
    template=json.loads((contract.assets/'AI친화_메타데이터_템플릿.jsonld').read_text(encoding='utf-8'))
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
