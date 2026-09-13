# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_hwpx_parser.py
# 경로: packages/synthetic_engine/tests/document_conversion/test_hwpx_parser.py
# 목적: HWPX 파서의 세부 XML 단락 추출 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from zipfile import ZipFile
import pytest
from synthetic_engine.document_conversion.parsers.hwpx_parser import HwpxParser, HP, HH, HS
from synthetic_engine.document_conversion.parsers.package import DocumentPackage
from synthetic_engine.document_conversion.core.ir import TableIR, ParagraphIR, TabIR


# package 작업을 수행함
def package(path, body):
    with ZipFile(path, 'w') as archive:
        archive.writestr('Contents/header.xml', f'<h:head xmlns:h="{HH}"><h:charPr id="0" height="1200"><h:bold/></h:charPr></h:head>')
        archive.writestr('Contents/section0.xml', f'<s:sec xmlns:s="{HS}" xmlns:p="{HP}">{body}</s:sec>')
    return path


# 한글 표준(HWPX) 텍스트 controls and 스타일 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_text_controls_and_styles(tmp_path):
    source = package(tmp_path/'text.hwpx', '<p:p><p:run charPrIDRef="0"><p:t> A\u00a0\u3000①食藥處<p:tab/>B<p:lineBreak/>C </p:t></p:run></p:p>')
    document = HwpxParser().parse(source)
    paragraph = document.sections[0].elements[0]
    assert paragraph.inlines[0].text == ' A\u00a0\u3000①食藥處'
    assert paragraph.inlines[0].bold and paragraph.inlines[0].size_pt == 12
    assert isinstance(paragraph.inlines[1], TabIR)
    assert paragraph.inlines[-1].text == 'C '
    assert paragraph.source_ref.xml_path.startswith('Contents/section0.xml:')


# 한글 표준(HWPX) nested 표 목록 and 병합 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_nested_tables_and_merge(tmp_path):
    inner = '<p:p><p:run><p:t>inside</p:t></p:run></p:p>'
    for _ in range(4):
        inner = '<p:tbl rowCnt="1"><p:tr><p:tc><p:cellAddr rowAddr="0" colAddr="0"/><p:cellSpan rowSpan="1" colSpan="2"/><p:subList>'+inner+'</p:subList></p:tc></p:tr></p:tbl>'
    document = HwpxParser().parse(package(tmp_path/'table.hwpx', inner))
    tables = [b for b in document.iter_blocks() if isinstance(b, TableIR)]
    assert len(tables) == 4
    assert all(t.rows[0][0].col_span == 2 for t in tables)
    assert sum(isinstance(b, ParagraphIR) for b in document.iter_blocks()) == 1


# package 파일 경로 and dtd rejected 기능의 정상 동작 및 제약조건을 테스트함
def test_package_path_and_dtd_rejected(tmp_path):
    path = tmp_path/'bad.zip'
    with ZipFile(path, 'w') as archive:
        archive.writestr('../escape', 'x')
    with pytest.raises(ValueError, match='Unsafe'):
        DocumentPackage(path)
    with ZipFile(path, 'w') as archive:
        archive.writestr('doc.xml', '<!DOCTYPE x [<!ENTITY e "bad">]><x>&e;</x>')
    with DocumentPackage(path) as archive:
        with pytest.raises(ValueError, match='entities'):
            archive.xml('doc.xml')
