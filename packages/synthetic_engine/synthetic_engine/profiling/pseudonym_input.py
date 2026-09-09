"""
파일명: pseudonym_input.py
경로: packages/synthetic_engine/synthetic_engine/profiling/pseudonym_input.py
목적: 표 문서와 정형 파일을 가명화 입력 데이터프레임으로 변환함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd

from .analyzer import read_table

DOCUMENT_EXTENSIONS = {'.pdf', '.hwp', '.hwpx', '.docx', '.md'}


def read_pseudonym_input(path: Path) -> pd.DataFrame:
    """가명화 대상 파일을 읽어 데이터프레임으로 반환함"""
    suffix = path.suffix.lower()
    if suffix not in DOCUMENT_EXTENSIONS:
        return read_table(path)
    lines = []
    if suffix == '.pdf':
        import pdfplumber
        with pdfplumber.open(path) as document:
            for page in document.pages:
                lines.extend((page.extract_text() or '').splitlines())
    elif suffix == '.md':
        lines = path.read_text(encoding='utf-8-sig').splitlines()
    elif suffix in {'.docx', '.hwpx'}:
        namespace = ('http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                     if suffix == '.docx' else 'http://www.hancom.co.kr/hwpml/2011/paragraph')
        def paragraph_text(node):
            """문서 XML 노드에서 중첩된 텍스트를 추출함"""
            # Nested table paragraphs are visited separately, not duplicated.
            parts = []
            for child in node:
                if child.tag == f'{{{namespace}}}p':
                    continue
                if child.tag == f'{{{namespace}}}t':
                    parts.append(child.text or '')
                else:
                    parts.append(paragraph_text(child))
            return ''.join(parts)
        with zipfile.ZipFile(path) as archive:
            if suffix == '.docx':
                names = ['word/document.xml']
                names += sorted(n for n in archive.namelist() if re.fullmatch(r'word/(header\d+|footer\d+|footnotes|endnotes)\.xml', n))
            else:
                names = sorted((n for n in archive.namelist() if re.fullmatch(r'Contents/section\d+\.xml', n)),
                               key=lambda n: int(re.search(r'section(\d+)', n).group(1)))
            for name in names:
                root = ET.fromstring(archive.read(name))
                lines.extend(paragraph_text(p) for p in root.iter(f'{{{namespace}}}p'))
    else:
        return read_table(path)
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        raise ValueError('추출 가능한 텍스트가 없습니다. 스캔·이미지 문서는 OCR 처리가 필요합니다.')
    return pd.DataFrame({'문단번호': range(1, len(lines) + 1), '문서_내용': lines})
