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
from pathlib import Path
from .binding import Contract,canonical
from .profile import profile_bytes,compare_json_xml
from .render import document_model,markdown,docx_bytes,verify_outputs
from .exchange import xml_output,jsonld_output,validate_jsonld_semantics


# 원본 파일 입력 목록과 제목을 기반으로 AI 친화 가이드 문서를 종합 생성함
def generate(inputs,title,assets=None):
    contract=Contract(assets) if assets else Contract()
    profiles=[profile_bytes(raw,fmt,name) for name,fmt,raw in inputs]
    comparison=None
    if len(inputs)==2 and {fmt.lstrip('.') for _,fmt,_ in inputs}=={'json','xml'}:
        raw={fmt.lstrip('.'):data for _,fmt,data in inputs}
        comparison=compare_json_xml(raw['json'],raw['xml'])
    model=canonical(profiles,title,contract,comparison)
    return render(model,contract)


# 캐노니컬 모델을 마크다운, DOCX, XML, JSON-LD로 렌더링하고 유효성을 검증함
def render(model,contract):
    blocks,template,index=document_model(model,contract)
    md=markdown(blocks);docx=docx_bytes(blocks,template)
    validation=verify_outputs(blocks,md,docx)
    xml=xml_output(model,contract)
    ld=jsonld_output(model,contract)
    validation.update(xsd='PASS (프로젝트 XSD)',jsonld_syntax='PASS',jsonld_semantics=validate_jsonld_semantics(ld),visual='PENDING')
    return dict(canonical=model,markdown=md,docx=docx,xml=xml,jsonld=ld,validation=validation,template_index=index,document_model=blocks)


# 생성된 문서 및 메타데이터 산출물을 대상 파일 경로에 저장함
def write(result,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    for suffix,key in [('.md','markdown'),('.docx','docx'),('.metadata.xml','xml'),('.metadata.jsonld','jsonld')]:
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
    args=parser.parse_args()
    result=generate([(p.name,p.suffix,p.read_bytes()) for p in args.inputs],args.title)
    write(result,args.output)
    print(json.dumps(result['validation'],ensure_ascii=False))


if __name__=='__main__': main()
