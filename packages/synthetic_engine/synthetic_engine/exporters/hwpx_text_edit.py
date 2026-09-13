# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: hwpx_text_edit.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/hwpx_text_edit.py
# 목적: HWPX 내부 문단 텍스트 및 속성 직접 치환 수정을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Edit original HWPX text slots without rebuilding controls or table geometry."""
from lxml import etree

NS = 'http://www.hancom.co.kr/hwpml/2011/paragraph'


# preview references 요소를 제거함
def remove_preview_references(data):
    root = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
    changed = False
    for node in list(root.iter()):
        if any(key.rsplit('}', 1)[-1] in ('full-path', 'href', 'Target')
               and value.replace('\\', '/').lstrip('./').startswith('Preview/')
               for key, value in node.attrib.items()):
            if node.getparent() is not None:
                node.getparent().remove(node)
                changed = True
    return etree.tostring(root, encoding='utf-8', xml_declaration=True) if changed else data


# section 내용을 편집함
def edit_section(data, items, counts):
    root = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
    changed = False
    for paragraph in root.iter(f'{{{NS}}}p'):
        segments = [[]]
        for node in paragraph.iter(f'{{{NS}}}t'):
            if next((p for p in node.iterancestors() if p.tag == f'{{{NS}}}p'), None) is not paragraph:
                segments.append([])
                continue
            if node.text:
                segments[-1].append((node, 'text', node.text))
            for child in node:
                # Controls are search boundaries, not removable whitespace.
                segments.append([])
                if child.tail:
                    segments[-1].append((child, 'tail', child.tail))
        for slots in segments:
            original = ''.join(value for _, _, value in slots)
            matches = []
            for item in items:
                old = item['original']
                if not old:
                    raise ValueError('검색어가 비어 있습니다.')
                start = 0
                while (start := original.find(old, start)) >= 0:
                    matches.append((start, start + len(old), item['replacement'], old))
                    start += len(old)
            matches.sort()
            if any(a[1] > b[0] for a, b in zip(matches, matches[1:])):
                raise ValueError('검색어 치환 구간이 중복됩니다.')
            for start, end, replacement, old in reversed(matches):
                affected, offset = [], 0
                for node, attr, text in slots:
                    left, right = max(start, offset), min(end, offset + len(text))
                    if left < right:
                        affected.append((node, attr, left - offset, right - offset))
                    offset += len(text)
                cursor = 0
                for index, (node, attr, left, right) in enumerate(affected):
                    current = getattr(node, attr) or ''
                    amount = len(replacement) - cursor if index == len(affected) - 1 else min(right - left, len(replacement) - cursor)
                    setattr(node, attr, current[:left] + replacement[cursor:cursor + amount] + current[right:])
                    cursor += amount
                counts[old] += 1
                changed = True
    if not changed:
        return data
    return etree.tostring(root, encoding='utf-8', xml_declaration=data.lstrip().startswith(b'<?xml'))
