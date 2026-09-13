# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_hwpx_native_preservation.py
# 경로: packages/synthetic_engine/tests/test_hwpx_native_preservation.py
# 목적: HWPX 고유 서식 및 네이티브 구조 보존을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import posixpath
import zipfile

import pymupdf as fitz
import pytest
from hwpx.document import HwpxDocument
from lxml import etree

from synthetic_engine.exporters.preserve_document import replace_hwpx


# fixture document 작업을 수행함
def fixture_document(path):
    doc = HwpxDocument.new()
    doc.add_paragraph('Unchanged heading')
    table = doc.add_table(rows=2, cols=3)
    table.set_column_widths([8000, 16000, 24000])
    cell = table.merge_cells(0, 0, 0, 1)
    paragraph = cell.paragraphs[0]
    paragraph.add_run('before ABC', bold=True)
    paragraph.add_run('123 after', italic=True)
    pixels = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 12), False)
    pixels.clear_with(80)
    binary = doc.media.add_image(pixels.tobytes('png'), 'png')
    paragraph.add_picture(binary.item_id, width=2100, height=1700)
    table.cell(1, 2).paragraphs[0].add_run('other cell unchanged')
    table.cell(1, 2).paragraphs[0].add_picture(binary.item_id, width=1300, height=900)
    doc.save_to_path(path)


# structural xml 작업을 수행함
def structural_xml(data):
    root = etree.fromstring(data)
    for node in root.iter():
        if etree.QName(node).localname == 't':
            node.text = None
            for child in node:
                child.tail = None
    return etree.tostring(root, method='c14n')


# 이미지 graph 작업을 수행함
def image_graph(archive):
    root = etree.fromstring(archive.read('Contents/section0.xml'))
    references = []
    for node in root.iter():
        for key, value in node.attrib.items():
            if etree.QName(key).localname == 'binaryItemIDRef':
                cell = next(p for p in node.iterancestors() if etree.QName(p).localname == 'tc')
                address = next(p for p in cell if etree.QName(p).localname == 'cellAddr')
                references.append((tuple(sorted(address.attrib.items())), root.getroottree().getpath(node), value))
    manifest = etree.fromstring(archive.read('Contents/content.hpf'))
    items = {n.get('id'): n.get('href') for n in manifest.iter() if n.get('id') and n.get('href')}
    assert references
    for _, _, identifier in references:
        href = items[identifier]
        resolved = href if href in archive.namelist() else posixpath.normpath(posixpath.join('Contents', href))
        assert resolved in archive.namelist()
        assert archive.read(resolved)
    return references


# 한글 표준(HWPX) search replace save reload preserves 표(테이블) and 이미지 graph 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize('replacement', ['XYZ789', 'X', 'A substantially longer replacement'])
def test_hwpx_search_replace_save_reload_preserves_table_and_image_graph(tmp_path, replacement):
    source, output = tmp_path / 'source.hwpx', tmp_path / 'result.hwpx'
    fixture_document(source)
    original_bytes = source.read_bytes()
    HwpxDocument.open(source)
    replace_hwpx(source, output, [{'original': 'ABC123', 'replacement': replacement}])
    HwpxDocument.open(output)
    assert source.read_bytes() == original_bytes
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(output) as after:
        assert after.testzip() is None
        assert image_graph(before) == image_graph(after)
        assert len(image_graph(after)) == 2
        assert after.namelist() == [n for n in before.namelist() if not n.startswith('Preview/')]
        for name in after.namelist():
            if name == 'Contents/section0.xml':
                assert structural_xml(before.read(name)) == structural_xml(after.read(name))
                original_text = ''.join(etree.fromstring(before.read(name)).itertext())
                result_text = ''.join(etree.fromstring(after.read(name)).itertext())
                assert result_text == original_text.replace('ABC123', replacement)
            elif name == 'META-INF/container.xml':
                original = etree.fromstring(before.read(name))
                for node in list(original.iter()):
                    if node.get('full-path', '').startswith('Preview/'):
                        node.getparent().remove(node)
                assert etree.tostring(original, method='c14n') == etree.tostring(etree.fromstring(after.read(name)), method='c14n')
            else:
                assert after.read(name) == before.read(name), name


# 한글 표준(HWPX) missing search does not publish partial output 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_missing_search_does_not_publish_partial_output(tmp_path):
    source, output = tmp_path / 'source.hwpx', tmp_path / 'result.hwpx'
    fixture_document(source)
    output.write_bytes(b'existing result')
    with pytest.raises(ValueError, match='MISSING'):
        replace_hwpx(source, output, [{'original': 'ABC123', 'replacement': 'OK'}, {'original': 'MISSING', 'replacement': 'X'}])
    assert output.read_bytes() == b'existing result'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['result.hwpx', 'source.hwpx']


# 한글 표준(HWPX) control boundary and tail 텍스트 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_control_boundary_and_tail_text(tmp_path):
    source, output = tmp_path / 'source.hwpx', tmp_path / 'result.hwpx'
    xml = b'<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"><hp:p><hp:run><hp:t>ABC<hp:tab/>123 suffix</hp:t></hp:run></hp:p></hp:sec>'
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('Contents/section0.xml', xml)
    with pytest.raises(ValueError, match='ABC123'):
        replace_hwpx(source, output, [{'original': 'ABC123', 'replacement': 'X'}])
    replace_hwpx(source, output, [{'original': '123', 'replacement': '45678'}])
    with zipfile.ZipFile(output) as archive:
        root = etree.fromstring(archive.read('Contents/section0.xml'))
        assert root.find('.//{*}tab').tail == '45678 suffix'
        assert root.find('.//{*}t').text == 'ABC'


# 한글 표준(HWPX) processing does not resave native package 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_processing_does_not_resave_native_package(tmp_path, monkeypatch):
    from synthetic_engine.exporters import preserve_document as engine
    source = tmp_path / 'source.hwpx'
    fixture_document(source)
    work = tmp_path / 'work'
    work.mkdir()
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40, 60), 'ABC123')
        pdf.save(work / 'original.pdf')
    items = [{'original': 'ABC123', 'replacement': 'XYZ789'}]

    # only 데이터를 타깃 포맷으로 렌더링함
    def render_only(edited, pdf, output=None, replacements=None):
        assert output is None, 'Native SaveAs must not rewrite the final HWPX'
        HwpxDocument.open(edited)
        engine.replace_pdf(work / 'original.pdf', pdf, items)

    monkeypatch.setattr(engine, 'native_hancom', render_only)
    output, report = engine.process_document(source, work, items)
    assert report['layout'] == 'PASS'
    assert output.read_bytes() == (work / 'edited.hwpx').read_bytes()
    HwpxDocument.open(output)
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(output) as after:
        assert image_graph(before) == image_graph(after)
        assert structural_xml(before.read('Contents/section0.xml')) == structural_xml(after.read('Contents/section0.xml'))
