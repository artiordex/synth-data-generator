"""Direct editing and fail-closed layout verification for selected text targets."""
import json
import os
import re
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
from ..privacy.text_format_rules import RULE_VERSION


# native hancom 작업을 수행함
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


# 페이지 목록 데이터를 타깃 포맷으로 렌더링함
def render_pages(pdf, directory, prefix):
    with fitz.open(pdf) as document:
        if document.page_count > 100:
            raise ValueError('원본 서식 검증은 최대 100페이지까지 지원합니다.')
        for number, page in enumerate(document):
            page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(directory / f'{prefix}-{number}.png')
        return document.page_count


# targets 위치를 탐색하여 반환함
def locate_targets(document, items):
    if not items:
        return {number: [] for number in range(len(document))}
    located, counts = {}, {item['original']: 0 for item in items}
    for number, page in enumerate(document):
        hits = []
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                chars = [(char, span) for span in line['spans'] for char in span['chars']]
                text = ''.join(char['c'] for char, _ in chars)
                for item in items:
                    old = item['original']
                    start = 0
                    while (start := text.find(old, start)) >= 0:
                        if tuple(line['dir']) != (1.0, 0.0):
                            raise ValueError(f'검색어 {old!r}의 텍스트 자체가 회전되어 정밀 치환을 지원하지 않습니다.')
                        selected = chars[start:start + len(old)]
                        rect = fitz.Rect(selected[0][0]['bbox'])
                        for char, _ in selected[1:]: rect |= fitz.Rect(char['bbox'])
                        style = selected[0][1]
                        runs = []
                        for offset, (char, span) in enumerate(selected):
                            key = (span['font'], span['size'], span['color'])
                            if not runs or runs[-1]['key'] != key:
                                runs.append({'key': key, 'rect': fitz.Rect(char['bbox']),
                                             'origin': char['origin'], 'style': span, 'item': item,
                                             'replacement': '', 'first_run': not runs})
                            runs[-1]['rect'] |= fitz.Rect(char['bbox'])
                            runs[-1]['replacement'] += item['replacement'][offset]
                        hits.extend(runs)
                        counts[old] += 1
                        start += len(old)
        for hit in hits:
            # PyMuPDF editing uses unrotated coordinates; pixmaps use page rotation.
            hit['display_rect'] = hit['rect'] * page.rotation_matrix
        located[number] = hits
    missing = [term for term, count in counts.items() if count == 0]
    if missing:
        raise ValueError(f'좌표를 찾지 못한 검색어: {missing!r}. 줄바꿈·스캔·이미지 여부를 확인하세요.')
    return located


_FALLBACK_KOREAN_BUFFER = None


# korean 폴백 buffer 정보를 조회하여 반환함
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


# replace PDF 문서 작업을 수행함
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
                new = hit['replacement']

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
                    page.insert_text(hit['origin'], hit['replacement'], fontname=hit['font'],
                                     fontsize=hit['fontsize'], color=tuple(((color >> shift) & 255) / 255 for shift in (16, 8, 0)))
        document.save(output, garbage=4, deflate=True, clean=True)


# replace 한글 표준(HWPX) 작업을 수행함
def replace_hwpx(source, output, items):
    from .hwpx_text_edit import edit_section, remove_preview_references
    import tempfile
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('원본과 결과 파일 경로는 달라야 합니다.')
    counts = {item['original']: 0 for item in items}
    staged = None
    try:
        with zipfile.ZipFile(source) as zin:
            if len(zin.namelist()) != len(set(zin.namelist())):
                raise ValueError('HWPX 패키지에 중복된 파일 항목이 있습니다.')
            if any('signature' in name.lower() for name in zin.namelist()):
                raise ValueError('전자서명 문서는 자동 편집하지 않습니다.')
            with tempfile.NamedTemporaryFile(dir=output.parent, suffix='.hwpx', delete=False) as temp:
                staged = Path(temp.name)
            with zipfile.ZipFile(staged, 'w') as zout:
                zout.comment = zin.comment
                for entry in zin.infolist():
                    data = zin.read(entry.filename)
                    if entry.filename.startswith('Contents/') and entry.filename.endswith('.xml'):
                        data = edit_section(data, items, counts)
                    if entry.filename == 'META-INF/container.xml' or entry.filename.endswith(('.hpf', '.rels')):
                        data = remove_preview_references(data)
                    # Cached previews may contain the original PII.
                    if entry.filename.startswith('Preview/'):
                        continue
                    zout.writestr(entry, data)
            missing = [term for term, count in counts.items() if count == 0]
            if missing:
                raise ValueError(f'한글 텍스트 런에서 찾지 못한 검색어: {missing!r}')
            if 'Contents/content.hpf' in zin.namelist():
                from hwpx.document import HwpxDocument
                # Validate package references before publishing the staged result.
                HwpxDocument.open(staged)
        staged.replace(output)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


# PDF 문서 pair 정합성 및 무결성을 검증함
def verify_pdf_pair(original_pdf, processed_pdf, items):
    with fitz.open(original_pdf) as before, fitz.open(processed_pdf) as after:
        if len(before) != len(after): raise ValueError('페이지 수가 변경되었습니다.')
        locations = locate_targets(before, items)
        total_changed = 0
        for index in range(len(before)):
            a, b = before[index], after[index]
            if a.rect != b.rect or a.rotation != b.rotation: raise ValueError('페이지 크기 또는 회전이 변경되었습니다.')
            raw_a, raw_b = a.get_pixmap(alpha=False), b.get_pixmap(alpha=False)
            pixels_a = np.frombuffer(raw_a.samples, dtype=np.uint8).reshape(raw_a.height, raw_a.width, raw_a.n)
            pixels_b = np.frombuffer(raw_b.samples, dtype=np.uint8).reshape(raw_b.height, raw_b.width, raw_b.n)
            diff = np.any(pixels_a != pixels_b, axis=2)
            for hit in locations[index]:
                rect = hit['display_rect'] + (-1, -1, 1, 1)
                diff[max(0, int(rect.y0)):min(raw_a.height, int(rect.y1 + 1)),
                     max(0, int(rect.x0)):min(raw_a.width, int(rect.x1 + 1))] = False
            if diff.any(): raise ValueError('개인정보 영역 밖의 시각적 차이가 발생했습니다. 결과를 제공하지 않습니다.')
            # untouched chars 작업을 수행함
            def untouched_chars(page):
                chars = Counter()
                boxes = [hit['rect'] for hit in locations[index]]
                for block in page.get_text('rawdict')['blocks']:
                    for line in block.get('lines', []):
                        for span in line['spans']:
                            for char in span['chars']:
                                # Extraction may infer spaces after text streams are split.
                                # Sub-point rounding at adjacent glyph edges is not overlap.
                                if char.get('synthetic', False):
                                    continue
                                if not any((fitz.Rect(char['bbox']) & box).width > 0.01
                                           and (fitz.Rect(char['bbox']) & box).height > 0.01
                                           for box in boxes):
                                    chars[(char['c'], *[round(v, 2) for v in char['origin']])] += 1
                return chars
            if untouched_chars(a) != untouched_chars(b):
                raise ValueError('개인정보 이외의 텍스트 또는 텍스트 좌표가 변경되었습니다.')
            text = b.get_text()
            if any(item['original'] in text for item in items):
                raise ValueError('처리된 페이지에 원본 개인정보가 남아 있습니다.')
            total_changed += sum(hit['first_run'] for hit in locations[index])
        for item in items:
            # A styled run boundary may be extracted as a line break or space.
            if sum(re.sub(r'\s+', '', page.get_text()).count(re.sub(r'\s+', '', item['replacement'])) for page in after) < sum(
                    1 for hits in locations.values() for hit in hits if hit['item'] == item and hit['first_run']):
                raise ValueError('대체 텍스트가 누락되었거나 글꼴 인코딩이 손상되었습니다.')
        for xref in range(1, after.xref_length()):
            content = after.xref_object(xref).encode('utf-8') + (after.xref_stream(xref) if after.xref_is_stream(xref) else b'')
            for item in items:
                old = item['original']
                encodings = (old.encode(), old.encode('utf-16-le'), old.encode('utf-16-be'))
                if any(encoded in content or encoded.hex().encode() in content.lower() for encoded in encodings):
                    raise ValueError('PDF 내부 객체에 원본 개인정보가 남아 있습니다.')
        return {'page_count': len(after), 'changed_regions': total_changed,
                'text_rule_version': RULE_VERSION,
                'layout': 'PASS', 'selected_text_residual': 'PASS',
                'similarity_percent': 100.0 if not items else None,
                'scope': '선택한 텍스트와 검사 가능한 객체 기준. 이미지·OCR·미탐지 개인정보는 별도 검토가 필요합니다.'}


# native residual 정합성 및 무결성을 검증함
def verify_native_residual(output, items):
    # check 작업을 수행함
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


# document 데이터를 처리함
def process_document(source, directory, items):
    validate_replacements(items)
    output = directory / ('processed' + source.suffix.lower())
    original_pdf, processed_pdf = directory / 'original.pdf', directory / 'processed.pdf'
    if not items:
        # A document without selected PII must remain byte-for-byte native.
        import shutil
        shutil.copyfile(source, output)
        shutil.copyfile(original_pdf, processed_pdf)
    elif source.suffix.lower() == '.pdf':
        replace_pdf(source, output, items)
    elif source.suffix.lower() == '.hwpx':
        edited = directory / 'edited.hwpx'
        replace_hwpx(source, edited, items)
        native_hancom(edited, processed_pdf)
        import shutil
        shutil.copyfile(edited, output)
    elif source.suffix.lower() == '.hwp':
        native_hancom(source, processed_pdf, output=output, replacements=items)
    else:
        raise ValueError('원본 편집은 PDF, HWP, HWPX에서 지원합니다.')
    if not items and source.suffix.lower() != '.pdf':
        report = {'page_count': 0, 'changed_regions': 0, 'layout': 'PASS',
                  'selected_text_residual': 'PASS', 'similarity_percent': 100.0,
                  'scope': '개인정보 후보 없음. 원본 네이티브 파일을 변경 없이 복제했습니다.'}
    else:
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
