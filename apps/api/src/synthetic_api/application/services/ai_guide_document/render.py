# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: render.py
# 경로: apps/api/src/synthetic_api/application/services/ai_guide_document/render.py
# 목적: AI 친화 가이드 템플릿 파싱, 데이터 바인딩, 마크다운 및 DOCX 렌더링을 수행함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""Parse templates, bind once, render and reverse-extract both document formats."""
from __future__ import annotations

import copy
import html
import io
import json
import re
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from .binding import TOKEN, validate


# 텍스트 내 마크다운 링크 및 서식 문자를 일반 텍스트로 정규화함
def plain(text):
    text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text)
    return text.replace('**','').replace('`','').replace('\\|','|').replace('<br>', '\n')


# 마크다운 표 행의 셀 텍스트를 분할 추출함
def cells(line):
    return [plain(v.strip()) for v in re.split(r'(?<!\\)\|',line.strip().strip('|'))]


# 마크다운 텍스트를 구조화된 블록 목록으로 파싱함
def parse_md(text):
    blocks=[]
    lines=text.splitlines(); i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line or line=='---': i+=1; continue
        heading=re.match(r'^(#{1,3})\s+(.+)',line)
        if heading:
            blocks.append(dict(kind='heading',level=len(heading[1]),text=plain(heading[2])))
        elif line.startswith('|') and i+1<len(lines) and re.fullmatch(r'[\s|:\-]+',lines[i+1]):
            rows=[cells(line)]; i+=2
            while i<len(lines):
                current=lines[i].strip()
                if current.startswith('|'):
                    rows.append(cells(lines[i]));i+=1
                elif re.fullmatch(r'{{[#/].+}}',current): i+=1
                elif not current:
                    next_index=i+1
                    while next_index<len(lines) and not lines[next_index].strip(): next_index+=1
                    new_table=next_index+1<len(lines) and re.fullmatch(r'[\s|:\-]+',lines[next_index+1])
                    if next_index<len(lines) and lines[next_index].strip().startswith('|') and not new_table: i=next_index
                    else: break
                else: break
            blocks.append(dict(kind='table',rows=rows)); continue
        else:
            blocks.append(dict(kind='paragraph',text=plain(re.sub(r'^[>*]\s*','',line))))
        i+=1
    return blocks


# DOCX 문서 내 플레이스홀더 및 표 구조 인덱스를 생성함
def index_docx(path):
    doc=Document(path)
    placeholders=[]; tables=[]
    for i,p in enumerate(doc.paragraphs):
        placeholders.extend(dict(location=f'paragraph/{i}',key=m[1]) for m in TOKEN.finditer(p.text))
    for i,t in enumerate(doc.tables):
        previous=t._tbl.getprevious()
        title=''.join(previous.itertext()) if previous is not None else ''
        style=[]
        for r,row in enumerate(t.rows):
            for c,cell in enumerate(row.cells):
                placeholders.extend(dict(location=f'table/{i}/{r}/{c}',key=m[1]) for m in TOKEN.finditer(cell.text))
                shade=cell._tc.xpath('./w:tcPr/w:shd')
                style.append(dict(row=r,col=c,shade=shade[0].get(qn('w:fill')) if shade else None,
                                  alignment=[str(p.alignment) for p in cell.paragraphs],
                                  fonts=[run.font.name for p in cell.paragraphs for run in p.runs]))
        tables.append(dict(index=i,title=title,headers=[c.text for c in t.rows[0].cells],columns=len(t.columns),
                           variable_rows=[r for r,row in enumerate(t.rows) if any(TOKEN.search(c.text) for c in row.cells)],styles=style))
    return dict(placeholders=placeholders,tables=tables,
                sections=[dict(width=s.page_width.mm,height=s.page_height.mm) for s in doc.sections])


# 가이드 범주별 마크다운 및 DOCX 템플릿 경로와 내용을 반환함
def template_source(contract, category):
    stem='AI친화_'+('파일데이터' if category=='file' else '오픈API')+'_가이드_템플릿'
    source=(contract.assets/(stem+'.md')).read_text(encoding='utf-8')
    # Versioned presentation corrections: preserve headings, remove unsupported claims.
    source=source.replace(' / {{structure.api_specification.operations.0.operation_id}}','')
    source=source.replace('(행안부 12대 네임스페이스)','(카탈로그 어휘 매핑)')
    source=source.replace(' (필수)',' (기관 적용성 확인)')
    source=source.replace('공공데이터 16대 표준 분류','주제분류체계')
    source=source.replace('필수 데이터 결측치 부재율','관측 셀 결측 부재율').replace('필수 응답 필드 결측 부재율','관측 리프 값 결측 부재율')
    source=source.replace('이상치(Outlier) 부재율','정답 대비 일치율').replace('이상치(Outlier) 및 비정상 응답 부재율','정답 대비 일치율')
    source=source.replace('`dcat`, `dct`, `vcard`, `xsd`, `api` W3C 표준 네임스페이스 연계','W3C 어휘와 프로젝트 확장 `api`를 구분; 국가 프로파일 적합성 미검증')
    source=source.replace('XSD 및 JSON Schema 표준 타입 준수','원천 관측 타입 (외부 스키마 적합성 미검증)')
    source=source.replace('{{#reviewRequired}}\n* [{{status}}] {{label}}: {{reason}} (조치: {{action}})\n{{/reviewRequired}}',
        'REVIEW_TABLE')
    source=source.replace('(본문 5.3절 참조)','응답 샘플 필드와 운영 API 계약을 구분합니다. 전체 관측 사전은 아래 상세 부록 참조.')
    source=source.replace('(본문 5.2절 참조)','기관 확인 필요: 실제 요청 계약 미확정.')
    source=source.replace('(본문 5.4, 5.5절 참조)','기관 확인 필요: 인증정보 없는 공식 요청·응답 예제 미확정.')
    source=source.replace('권고 데이터 분할 비율','미확정 분할 비율')
    source+='\n\n### 분석 범위 및 출처별 결과\n{{analysis.summary}}\n'
    return source,contract.assets/(stem+'.docx')


# 값을 문서 표기용 문자열로 포맷팅함
def display(value):
    if value is None: return '기관 확인 필요'
    if isinstance(value,bool): return 'true' if value else 'false'
    if isinstance(value,float): return format(value,'.10g')
    if isinstance(value,(dict,list)): return json.dumps(value,ensure_ascii=False,separators=(',',':'))
    return str(value)


# 텍스트 템플릿의 Mustache 플레이스홀더에 모델 데이터를 바인딩함
def bind_text(text,model,contract,contexts=()):
    # Balanced nested mustache sections, with paths resolved in their repeat scope.
    start=re.search(r'{{#([^{}]+)}}',text)
    while start:
        depth=1; end=None
        for token in re.finditer(r'{{([#/])([^{}]+)}}',text[start.end():]):
            depth+=1 if token[1]=='#' else -1
            if depth==0:
                end=(start.end()+token.start(),start.end()+token.end())
                if token[2]!=start[1]: raise ValueError('반복 마커 불일치')
                break
        if end is None: raise ValueError('닫히지 않은 반복')
        items,path=contract.resolve(model,start[1],contexts)
        if not isinstance(items,list): raise ValueError('반복 대상은 배열이어야 합니다')
        body=text[start.end():end[0]]
        replacement=''.join(bind_text(body,model,contract,contexts+((path,i,item),)) for i,item in enumerate(items))
        text=text[:start.start()]+replacement+text[end[1]:]
        start=re.search(r'{{#([^{}]+)}}',text)
    statuses={e['bindingPath']:e['status'] for e in model['canonicalItems']}
    # 정규식 매치 토큰을 모델의 실제 값 문자열로 치환함
    def substitute(match):
        value,path=contract.resolve(model,match[1],contexts)
        result='해당 없음' if value is None and statuses.get(path)=='NOT_APPLICABLE' else display(value)
        if statuses.get(path)=='AUTO_INFERRED': result+=' [AUTO_INFERRED]'
        return result.replace('|','\\|').replace('\r','').replace('\n','<br>')
    return TOKEN.sub(substitute,text)


# 캐노니컬 모델을 바탕으로 가이드 문서 블록 구조 모델을 구축함
def document_model(model,contract):
    validate(model)
    source,path=template_source(contract,model['structure']['data_category'])
    source=source.replace('{{analysis.summary}}','아래 표는 각 원본 파일의 전수 조사 결과입니다. 두 표현을 합산한 레코드 수가 아닙니다.')
    blocks=parse_md(bind_text(source,model,contract))
    groups={}
    for entry in model['reviewRequired']:
        parent,leaf=entry['bindingPath'].rsplit('/',1)
        groups.setdefault(parent,[]).append(leaf)
    for i,b in enumerate(blocks):
        if b.get('text')=='REVIEW_TABLE':
            blocks[i]=dict(kind='table',rows=[['검토 경로','미확정 항목','상태']]+[[k,', '.join(v),'REVIEW_REQUIRED: 기관 확인 필요'] for k,v in groups.items()])
    blocks.insert(1,dict(kind='paragraph',text=model['dataset']['title']))
    blocks.insert(2,dict(kind='paragraph',text=model['document']['review_notice']))
    headings=[b['text'] for b in blocks if b['kind']=='heading' and b['level']==2]
    blocks.insert(3,dict(kind='paragraph',text='목차 (페이지 번호 없음)\n'+'\n'.join(headings)))
    # 헤더와 행 데이터를 바탕으로 표 블록을 문서에 추가함
    def table(headers,rows): blocks.append(dict(kind='table',rows=[headers]+[[display(x) for x in row] for row in rows]))
    profiles=model['analysis']['sources']
    table(['출처','바이트','조사 범위','실제 레코드','응답 선언값'],
          [[p['name'],p['byte_size'],p['scope'],p['observed_records'],p['declared_counts']] for p in profiles])
    for p in profiles:
        if p['tables']:
            table(['시트/표','실제 데이터 행','컬럼 수','제외한 빈 행'],
                  [[t['name'],t['row_count'],len(t['columns']),t.get('blank_rows',0)] for t in p['tables']])
            for t in p['tables']:
                ts=t.get('temporal')
                if ts:
                    blocks.append(dict(kind='heading',level=3,text='시간·개체 후보 분석: '+t['name']))
                    table(['항목','결과'],[[k,v] for k,v in ts.items() if k not in {'groups','gaps'}])
                    table(['개체 후보','시작','종료','중복 시각','최빈 간격(초)','누락 후보 구간 수'],
                          [[g['key'],g['start'],g['end'],g['duplicate_timestamps'],g['modal_interval_seconds'],len(g['gaps'])] for g in ts['groups']])
                    blocks.append(dict(kind='paragraph',text='전체 누락 후보 구간의 시작·종료·간격은 동일 Canonical Metadata의 analysis.sources[].tables[].temporal.groups[].gaps에 보존됩니다. 정렬된 고유 시각의 최빈 간격 초과를 기준으로 하며 실제 업무 누락 판정은 기관 확인 필요.'))
    comparison=model['analysis'].get('comparison')
    if comparison:
        table(['비교 항목','결과'],[[k,v] for k,v in comparison.items()])
    blocks.append(dict(kind='heading',level=3,text='전체 관측 필드·구조 경로 및 통계'))
    table(['출처 / 물리 경로','관측 타입','출현','null','빈 문자열','누락'],
          [[f['source']+'\n'+f['path'],f['data_type'],f['statistics'].get('occurrences'),f['statistics'].get('null_count'),
            f['statistics'].get('empty_count'),f['statistics'].get('missing_count')] for f in model['fields']])
    numeric=[f for f in model['fields'] if f['statistics'].get('numeric_count')]
    if numeric:
        table(['컬럼','유효 수치','결측 수','최소','최대','평균'],
              [[f['name']]+[f['statistics'].get(k) for k in ('numeric_count','numeric_missing_count','min_value','max_value','mean')] for f in numeric])
    table(['필드','0','false','빈 배열','수식','캐시 없는 수식'],
          [[f['name']]+[f['statistics'].get(k,0) for k in ('zero_count','false_count','empty_array_count','formula_count','uncached_formula_count')] for f in model['fields']])
    for f in model['fields']:
        temporal=f['statistics'].get('temporal')
        if temporal:
            blocks.append(dict(kind='heading',level=3,text='시간 분석: '+f['name']))
            table(['항목','관측 결과'],[[k,v] for k,v in temporal.items() if k!='gaps'])
            table(['시작','종료','간격(초)'],[[g['start'],g['end'],g['seconds']] for g in temporal['gaps']])
    blocks.append(dict(kind='paragraph',text='상태: 직접 관측 수치는 AUTO_CONFIRMED. 논리명·업무 의미·단위·필수성은 기관 확인 필요(REVIEW_REQUIRED). 외부 링크는 존재만 관측했으며 대상 파일·모델 성능은 분석하지 않았습니다.'))
    blocks.append(dict(kind='paragraph',text='Parquet 전환은 권고 초안(AUTO_INFERRED)입니다. 원본 보존, 날짜·개체별 누수 방지 검토 후 파티션과 타입을 결정하세요. 이 분석에서 보간·모델 학습은 수행하지 않았습니다.'))
    original_index=index_docx(path)
    normalized=contract.assets.parents[1]/'apps/api/src/synthetic_api/data/ai_guide'/path.name
    if not normalized.exists():
        raise ValueError('정규화 DOCX 템플릿이 없습니다. prepare-templates 명령을 실행하세요.')
    return blocks,normalized,dict(md_headings=[b for b in parse_md(source) if b['kind']=='heading'],
                            md_placeholders=[m[1] for m in TOKEN.finditer(source)],original_docx=original_index,
                            docx=index_docx(normalized),normalization='기존 사례 본문 제거; MD 구조와 기존 DOCX 서식 재사용')


# 구조화된 문서 블록 목록을 마크다운 문서로 변환함
def markdown(blocks):
    lines=[]
    for b in blocks:
        if b['kind']=='table':
            for i,row in enumerate(b['rows']):
                lines.append('| '+' | '.join(v.replace('&','&amp;').replace('|','&#124;').replace('\n','<br>') for v in row)+' |')
                if i==0: lines.append('| '+' | '.join('---' for _ in row)+' |')
        else:
            lines.append(('#'*b['level']+' ' if b['kind']=='heading' else '')+b['text'])
        lines.append('')
    return '\n'.join(lines)


# DOCX 워드 표 셀의 배경색, 테두리 및 폰트 스타일을 적용함
def cell_style(cell,header=False):
    pr=cell._tc.get_or_add_tcPr()
    for old in list(pr.findall(qn('w:shd'))): pr.remove(old)
    shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'E8EEF5' if header else 'FFFFFF'); pr.append(shade)
    borders=OxmlElement('w:tcBorders')
    for edge in ('top','left','bottom','right'):
        e=OxmlElement('w:'+edge); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
    pr.append(borders)
    for p in cell.paragraphs:
        p.alignment=0
        p.paragraph_format.space_after=Pt(4); p.paragraph_format.space_before=Pt(4)
        p.paragraph_format.keep_with_next=False
        for run in p.runs:
            run.font.name='맑은 고딕'; run.font.size=Pt(8); run.bold=header
            run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'맑은 고딕')


# 문서 블록 목록을 기반으로 스타일이 보존된 DOCX 바이너리를 렌더링함
def docx_bytes(blocks,template):
    doc=Document(template)
    prototypes={tuple(c.text for c in t.rows[0].cells):copy.deepcopy(t._tbl) for t in doc.tables}
    # The retained asset contains case-specific body data. Reuse its page/style package,
    # but replace the content topology with the parsed MD presentation profile.
    for element in list(doc._element.body):
        if element.tag!=qn('w:sectPr'): doc._element.body.remove(element)
    for section in doc.sections:
        section.page_width=Mm(210); section.page_height=Mm(297)
        section.left_margin=section.right_margin=Mm(20)
        section.top_margin=section.bottom_margin=Mm(20)
        for part in (section.header,section.footer,section.first_page_header,section.first_page_footer):
            for p in part.paragraphs:
                # Retain paragraph formatting, remove case-specific header/footer text.
                p.clear()
    normal=doc.styles['Normal']; normal.font.name='맑은 고딕'; normal.font.size=Pt(10)
    normal.paragraph_format.alignment=0
    normal.paragraph_format.line_spacing=1.15
    normal.paragraph_format.space_after=Pt(6)
    for level in (1,2,3):
        style=doc.styles['Heading '+str(level)]
        if style.element.pPr is not None:
            for numbering in list(style.element.pPr.findall(qn('w:numPr'))): style.element.pPr.remove(numbering)
    for b in blocks:
        if b['kind']=='table':
            rows=b['rows']
            prototype=prototypes.get(tuple(rows[0]))
            if prototype is not None:
                from docx.table import Table
                element=copy.deepcopy(prototype);doc._element.body.insert(len(doc._element.body)-1,element)
                table=Table(element,doc._body)
                body_style=copy.deepcopy(table.rows[1]._tr) if len(table.rows)>1 else None
                for row in list(table.rows)[1:]: table._tbl.remove(row._tr)
            else:
                table=doc.add_table(rows=1,cols=len(rows[0]));body_style=None
            table.autofit=False
            width=170/len(rows[0])
            for col in table.columns: col.width=Mm(width)
            for c,text in zip(table.rows[0].cells,rows[0]): c.text=text; c.width=Mm(width); cell_style(c,True)
            repeat=OxmlElement('w:tblHeader'); table.rows[0]._tr.get_or_add_trPr().append(repeat)
            for values in rows[1:]:
                row=table.add_row()
                keep=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(keep)
                for i,(cell,text) in enumerate(zip(row.cells,values)):
                    # Copy all cell properties from the parsed prototype; header shade is overridden.
                    cell._tc.remove(cell._tc.tcPr)
                    prototype_cell=body_style.findall(qn('w:tc'))[i] if body_style is not None else table.rows[0].cells[i]._tc
                    cell._tc.insert(0,copy.deepcopy(prototype_cell.find(qn('w:tcPr'))))
                    cell.text=text; cell_style(cell)
            doc.add_paragraph('')
        elif b['kind']=='heading':
            p=doc.add_paragraph(b['text'],style='Heading '+str(b['level']))
            p.paragraph_format.keep_with_next=True
            for run in p.runs:
                run.font.name='맑은 고딕';run.font.color.rgb=RGBColor.from_string('17365D')
                run.font.size=Pt({1:22,2:15,3:12}[b['level']])
        else:
            p=doc.add_paragraph(b['text'])
    stream=io.BytesIO();doc.save(stream);return stream.getvalue()


# 생성된 마크다운과 DOCX 문서 내용의 무결성 및 라운드트립 일치성을 검증함
def verify_outputs(blocks,md,docx):
    expected_tables=[b['rows'] for b in blocks if b['kind']=='table']
    expected_headings=[b['text'] for b in blocks if b['kind']=='heading']
    extracted=parse_md(md)
    md_tables=[[[html.unescape(v) for v in row] for row in b['rows']] for b in extracted if b['kind']=='table']
    doc=Document(io.BytesIO(docx))
    doc_tables=[[[c.text for c in row.cells] for row in table.rows] for table in doc.tables]
    doc_headings=[p.text for p in doc.paragraphs if p.style.name.startswith('Heading ')]
    md_headings=[b['text'] for b in extracted if b['kind']=='heading']
    if expected_tables != md_tables or expected_tables != doc_tables: raise ValueError('MD/DOCX 표 역추출 불일치')
    if expected_headings != md_headings or expected_headings != doc_headings: raise ValueError('목차/제목 역추출 불일치')
    if TOKEN.search(md): raise ValueError('미치환 플레이스홀더')
    return dict(tables=len(expected_tables),headings=len(expected_headings),field_values='PASS',reverse_extraction='PASS')


# 원본 서식 자산으로부터 정규화된 가이드 DOCX 템플릿을 사전 생성함
def prepare_templates(contract):
    """Explicit asset build, never a mutation during an API request."""
    folder=contract.assets.parents[1]/'apps/api/src/synthetic_api/data/ai_guide'
    folder.mkdir(parents=True,exist_ok=True)
    for category in ('file','api'):
        source,original=template_source(contract,category)
        (folder/original.name).write_bytes(docx_bytes(parse_md(source),original))
