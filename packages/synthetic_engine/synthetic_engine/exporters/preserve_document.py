"""Direct editing and fail-closed layout verification for selected text targets."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import zlib
from collections import Counter

import numpy as np
import pymupdf as fitz
from lxml import etree

from ..privacy.document_replacements import validate_replacements


def native_hancom(source, pdf, output=None, replacements=None):
    if os.name != 'nt':
        raise ValueError('한글 원본 서식 검증에는 Windows 한글 렌더링 작업자가 필요합니다.')
    spec = pdf.with_suffix('.request.json')
    spec.write_text(json.dumps({'source': str(source), 'pdf': str(pdf),
                               'output': str(output) if output else None,
                               'replacements': replacements or []}, ensure_ascii=False), encoding='utf-8')
    try:
        result = subprocess.run([sys.executable, '-m', 'synthetic_engine.exporters.native_hancom', str(spec)],
                                capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not pdf.is_file():
            raise ValueError('한글 자동화/페이지 렌더링 실패. 설치 및 문서 접근 허용 상태를 확인하세요.')
    except subprocess.TimeoutExpired:
        raise ValueError('한글 문서 접근 또는 렌더링 시간 초과. 검증 전 다운로드는 차단됩니다.') from None
    finally:
        spec.unlink(missing_ok=True)


def render_pages(pdf, directory, prefix):
    with fitz.open(pdf) as document:
        if document.page_count > 100:
            raise ValueError('원본 서식 검증은 최대 100페이지까지 지원합니다.')
        for number, page in enumerate(document):
            page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(directory / f'{prefix}-{number}.png')
        return document.page_count


def locate_targets(document, items):
    located, counts = {}, {item['original']: 0 for item in items}
    for number, page in enumerate(document):
        if page.rotation:
            raise ValueError('회전된 페이지는 현재 정밀 치환 검증을 지원하지 않습니다.')
        hits = []
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                if tuple(line['dir']) != (1.0, 0.0):
                    raise ValueError('회전된 텍스트가 포함되어 있습니다.')
                chars = [(char, span) for span in line['spans'] for char in span['chars']]
                text = ''.join(char['c'] for char, _ in chars)
                for item in items:
                    old = item['original']
                    start = 0
                    while (start := text.find(old, start)) >= 0:
                        selected = chars[start:start + len(old)]
                        rect = fitz.Rect(selected[0][0]['bbox'])
                        for char, _ in selected[1:]: rect |= fitz.Rect(char['bbox'])
                        style = selected[0][1]
                        if any(span['font'] != style['font'] or span['size'] != style['size'] for _, span in selected):
                            raise ValueError('여러 글꼴에 걸친 개인정보는 자동 치환할 수 없습니다.')
                        hits.append({'rect': rect, 'origin': selected[0][0]['origin'], 'style': style, 'item': item})
                        counts[old] += 1
                        start += len(old)
        located[number] = hits
    if any(count == 0 for count in counts.values()):
        raise ValueError('지정한 개인정보의 좌표를 찾지 못했습니다. 줄바꿈·스캔·이미지 여부를 확인하세요.')
    return located


_FALLBACK_KOREAN_BUFFER = None


def get_korean_fallback_buffer():
    global _FALLBACK_KOREAN_BUFFER
    if _FALLBACK_KOREAN_BUFFER is None:
        try:
            _FALLBACK_KOREAN_BUFFER = fitz.Font('korean').buffer
        except Exception:
            malgun = Path('C:/Windows/Fonts/malgun.ttf')
            if malgun.exists():
                _FALLBACK_KOREAN_BUFFER = malgun.read_bytes()
    return _FALLBACK_KOREAN_BUFFER


def replace_pdf(source, output, items):
    with fitz.open(source) as document:
        if document.is_encrypted or document.embfile_count() or document.get_sigflags() > 0:
            raise ValueError('암호화·첨부파일·서명 PDF는 자동 처리하지 않습니다.')
        positions = locate_targets(document, items)
        fallback_buffer = get_korean_fallback_buffer()
        fallback_font = fitz.Font(fontbuffer=fallback_buffer) if fallback_buffer else None

        for number, hits in positions.items():
            page = document[number]
            if list(page.annots() or []) or list(page.widgets() or []):
                raise ValueError('주석·입력 양식 PDF는 잔존 정보 검증을 지원하지 않습니다.')
            fonts = {}
            for hit in hits:
                rect, style = hit['rect'], hit['style']
                if any(rect.intersects(image['bbox']) for image in page.get_image_info()):
                    raise ValueError('개인정보 영역이 이미지와 겹칩니다. 이미지 내 개인정보 검증이 필요합니다.')
                font_name = style['font']
                if font_name not in fonts:
                    candidates = [
                        font for font in page.get_fonts(full=True)
                        if font[3].split('+')[-1] == font_name.split('+')[-1]
                        or font[4].split('+')[-1] == font_name.split('+')[-1]
                        or font_name.lower() in font[3].lower()
                        or font[3].lower() in font_name.lower()
                    ]
                    xref = candidates[0][0] if candidates else None
                    buffer = None
                    if xref:
                        _, _, _, buffer = document.extract_font(xref)
                    if buffer:
                        font = fitz.Font(fontbuffer=buffer)
                        alias = f'privacyfont{len(fonts)}'
                    else:
                        font = fitz.Font(fontname=font_name)
                        alias = font_name
                    fonts[font_name] = (font, alias, buffer)
                font, alias, buffer = fonts[font_name]
                new = hit['item']['replacement']

                # 글리프 지원 검사 및 대체 글꼴 자동 전환
                use_font = font
                use_alias = alias
                use_buffer = buffer
                standard_14 = {
                    'helvetica', 'helvetica-bold', 'helvetica-oblique', 'helvetica-boldoblique',
                    'times-roman', 'times-bold', 'times-italic', 'times-bolditalic',
                    'courier', 'courier-bold', 'courier-oblique', 'courier-boldoblique',
                    'symbol', 'zapfdingbats'
                }
                needs_fallback = (
                    (buffer is None and font_name.lower() not in standard_14)
                    or any(not font.has_glyph(ord(char)) for char in new)
                )
                if needs_fallback:
                    if fallback_font and all(fallback_font.has_glyph(ord(char)) for char in new):
                        use_font = fallback_font
                        use_alias = 'privacy_fallback_ko'
                        use_buffer = fallback_buffer
                    else:
                        missing = [c for c in new if not (fallback_font and fallback_font.has_glyph(ord(c)))]
                        if missing:
                            raise ValueError(f"대체 문자에 포함된 '{missing[0]}'의 글꼴 글리프를 지원하지 않습니다. 대체값을 표준 문자(*, ○, 한글 등)로 변경하세요.")
                        raise ValueError('대체 문자의 글리프를 지원하는 글꼴을 찾을 수 없습니다. 대체값을 변경하세요.')

                # 폭 초과 방지: 글자 폭이 원본 영역보다 넓은 경우 자동 크기 조절
                fontsize = style['size']
                text_w = use_font.text_length(new, fontsize=fontsize)
                if text_w > rect.width:
                    scale = (rect.width - 0.2) / max(text_w, 1.0)
                    fontsize = round(max(fontsize * scale, 4.0), 2)

                hit['font'] = use_alias
                hit['fontbuffer'] = use_buffer
                hit['fontsize'] = fontsize
                page.add_redact_annot(rect, fill=None, cross_out=False)

            if hits:
                page.apply_redactions(images=0, graphics=0, text=0)
                registered = set()
                for hit in hits:
                    falias = hit['font']
                    if falias not in registered and hit.get('fontbuffer'):
                        page.insert_font(fontname=falias, fontbuffer=hit['fontbuffer'])
                        registered.add(falias)
                for hit in hits:
                    color = hit['style']['color']
                    page.insert_text(hit['origin'], hit['item']['replacement'], fontname=hit['font'],
                                     fontsize=hit['fontsize'], color=tuple(((color >> shift) & 255) / 255 for shift in (16, 8, 0)))
        document.save(output, garbage=4, deflate=True, clean=True)


def replace_hwpx(source, output, items):
    ns = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    counts = {item['original']: 0 for item in items}
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(output, 'w') as zout:
        if any('signature' in name.lower() for name in zin.namelist()):
            raise ValueError('전자서명 문서는 자동 편집하지 않습니다.')
        for entry in zin.infolist():
            data = zin.read(entry.filename)
            if entry.filename.startswith('Contents/') and entry.filename.endswith('.xml'):
                root = etree.fromstring(data, parser)
                for paragraph in root.iter(f'{{{ns}}}p'):
                    nodes = [node for node in paragraph.iter(f'{{{ns}}}t')
                             if next((p for p in node.iterancestors() if p.tag == f'{{{ns}}}p'), None) is paragraph]
                    original = ''.join(node.text or '' for node in nodes)
                    changed = original
                    for item in items:
                        counts[item['original']] += original.count(item['original'])
                        changed = changed.replace(item['original'], item['replacement'])
                    if original != changed:
                        offset = 0
                        for node in nodes:
                            length = len(node.text or '')
                            node.text = changed[offset:offset + length]
                            offset += length
                data = etree.tostring(root, encoding='utf-8', xml_declaration=True)
            # Stale cached previews can retain original personal data. Native saving
            # regenerates them after the edit; they must not be shipped untouched.
            if entry.filename.startswith('Preview/'):
                continue
            zout.writestr(entry, data)
    if any(count == 0 for count in counts.values()):
        raise ValueError('한글 텍스트 런에서 지정한 개인정보를 찾지 못했습니다.')


def verify_pdf_pair(original_pdf, processed_pdf, items):
    with fitz.open(original_pdf) as before, fitz.open(processed_pdf) as after:
        if len(before) != len(after): raise ValueError('페이지 수가 변경되었습니다.')
        locations = locate_targets(before, items)
        total_changed = 0
        for index in range(len(before)):
            a, b = before[index], after[index]
            if a.rect != b.rect: raise ValueError('페이지 크기가 변경되었습니다.')
            raw_a, raw_b = a.get_pixmap(alpha=False), b.get_pixmap(alpha=False)
            pixels_a = np.frombuffer(raw_a.samples, dtype=np.uint8).reshape(raw_a.height, raw_a.width, raw_a.n)
            pixels_b = np.frombuffer(raw_b.samples, dtype=np.uint8).reshape(raw_b.height, raw_b.width, raw_b.n)
            diff = np.any(pixels_a != pixels_b, axis=2)
            for hit in locations[index]:
                rect = hit['rect'] + (-1, -1, 1, 1)
                diff[max(0, int(rect.y0)):min(raw_a.height, int(rect.y1 + 1)),
                     max(0, int(rect.x0)):min(raw_a.width, int(rect.x1 + 1))] = False
            if diff.any(): raise ValueError('개인정보 영역 밖의 시각적 차이가 발생했습니다. 결과를 제공하지 않습니다.')
            def untouched_chars(page):
                chars = Counter()
                boxes = [hit['rect'] for hit in locations[index]]
                for block in page.get_text('rawdict')['blocks']:
                    for line in block.get('lines', []):
                        for span in line['spans']:
                            for char in span['chars']:
                                if not any(fitz.Rect(char['bbox']).intersects(box) for box in boxes):
                                    chars[(char['c'], *[round(v, 2) for v in char['origin']])] += 1
                return chars
            if untouched_chars(a) != untouched_chars(b):
                raise ValueError('개인정보 이외의 텍스트 또는 텍스트 좌표가 변경되었습니다.')
            text = b.get_text()
            if any(item['original'] in text for item in items):
                raise ValueError('처리된 페이지에 원본 개인정보가 남아 있습니다.')
            total_changed += len(locations[index])
        for item in items:
            if sum(page.get_text().count(item['replacement']) for page in after) < sum(
                    1 for hits in locations.values() for hit in hits if hit['item'] == item):
                raise ValueError('대체 텍스트가 누락되었거나 글꼴 인코딩이 손상되었습니다.')
        for xref in range(1, after.xref_length()):
            content = after.xref_object(xref).encode('utf-8') + (after.xref_stream(xref) if after.xref_is_stream(xref) else b'')
            for item in items:
                old = item['original']
                encodings = (old.encode(), old.encode('utf-16-le'), old.encode('utf-16-be'))
                if any(encoded in content or encoded.hex().encode() in content.lower() for encoded in encodings):
                    raise ValueError('PDF 내부 객체에 원본 개인정보가 남아 있습니다.')
        return {'page_count': len(after), 'changed_regions': total_changed,
                'layout': 'PASS', 'selected_text_residual': 'PASS',
                'scope': '선택한 텍스트와 검사 가능한 객체 기준. 이미지·OCR·미탐지 개인정보는 별도 검토가 필요합니다.'}


def verify_native_residual(output, items):
    def check(data):
        for item in items:
            if any(item['original'].encode(encoding) in data for encoding in ('utf-8', 'utf-16-le', 'utf-16-be')):
                raise ValueError('한글 내부 데이터에 원본 개인정보가 남아 있습니다.')
    if output.suffix.lower() == '.hwpx':
        with zipfile.ZipFile(output) as archive:
            for entry in archive.infolist():
                data = archive.read(entry)
                check(data)
                if entry.filename.endswith('.xml'):
                    root = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
                    check(''.join(root.itertext()).encode('utf-8'))
    else:
        import olefile
        with olefile.OleFileIO(output) as ole:
            for entry in ole.listdir():
                data = ole.openstream(entry).read()
                check(data)
                if entry[0] in {'BodyText', 'DocInfo'}:
                    try:
                        check(zlib.decompress(data, -15))
                    except zlib.error:
                        pass


def process_document(source, directory, items):
    validate_replacements(items)
    output = directory / ('processed' + source.suffix.lower())
    original_pdf, processed_pdf = directory / 'original.pdf', directory / 'processed.pdf'
    if source.suffix.lower() == '.pdf':
        replace_pdf(source, output, items)
    elif source.suffix.lower() == '.hwpx':
        edited = directory / 'edited.hwpx'
        replace_hwpx(source, edited, items)
        native_hancom(edited, processed_pdf, output=output)
    elif source.suffix.lower() == '.hwp':
        native_hancom(source, processed_pdf, output=output, replacements=items)
    else:
        raise ValueError('원본 편집은 PDF, HWP, HWPX에서 지원합니다.')
    report = verify_pdf_pair(original_pdf, processed_pdf, items)
    if source.suffix.lower() != '.pdf':
        verify_native_residual(output, items)
        from ..profiling.pseudonym_input import read_pseudonym_input
        text = '\n'.join(read_pseudonym_input(output)['문서_내용'].astype(str))
        if any(item['original'] in text for item in items):
            raise ValueError('한글 원본 데이터에 개인정보가 남아 있습니다.')
    return output, report
# =============================================================================
# 파일명: preserve_document.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/preserve_document.py
# 목적: 문서 원본 서식을 유지한 치환과 잔여 개인정보 검증을 처리함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
