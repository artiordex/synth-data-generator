# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: layout.py
# 경로: packages/ocr/ocr/text/layout.py
# 목적: 텍스트 바운딩 박스 정렬, 읽기 순서 결정 및 레이아웃을 분석함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Geometry-aware OCR line assembly and spacing helpers.

OCR engines return detections in slightly different shapes.  Keeping line
clustering and gap handling in one small module prevents each backend from
inventing a different reading order or from inserting a space between every
detected box.
"""

from __future__ import annotations

from statistics import median
from typing import Iterable

from ..pipeline.models import BoundingBox, OCRWord


_NO_SPACE_BEFORE = frozenset(
    ".,;:!?%)]}〉》」』】。，、！？；：％）］｝〉》」』"
)
_NO_SPACE_AFTER = frozenset("([<{〈《「『【[")


# cluster words into lines 작업을 수행함
def cluster_words_into_lines(words: Iterable[OCRWord]) -> list[list[OCRWord]]:
    """Cluster boxes into visual lines using centers and adaptive tolerance.

    The old implementation compared every box with the first box in a line.
    A tall first box could therefore absorb an adjacent line, while a small
    box at the end of a line could become a new line.  We compare with the
    current line center and use both center distance and vertical overlap.
    """

    lines: list[list[OCRWord]] = []
    for word in sorted(words, key=lambda item: (item.bbox.y, item.bbox.x)):
        box = word.bbox
        candidates: list[tuple[float, int]] = []
        center = box.y + box.height / 2.0
        for index, line in enumerate(lines):
            heights = [item.bbox.height for item in line]
            line_center = median(
                item.bbox.y + item.bbox.height / 2.0 for item in line
            )
            tolerance = max(3.0, 0.42 * max(box.height, median(heights)))
            overlap = min(
                box.y + box.height,
                max(item.bbox.y + item.bbox.height for item in line),
            ) - max(box.y, min(item.bbox.y for item in line))
            overlap_ratio = overlap / max(1.0, min(box.height, median(heights)))
            if abs(center - line_center) <= tolerance or overlap_ratio >= 0.30:
                score = max(
                    overlap_ratio,
                    1.0 - abs(center - line_center) / max(tolerance, 1.0),
                )
                candidates.append((score, index))
        if candidates:
            lines[max(candidates)[1]].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda item: item.bbox.x) for line in lines]


# 병합 touching fragments 작업을 수행함
def merge_touching_fragments(lines: Iterable[Iterable[OCRWord]]) -> list[list[OCRWord]]:
    """Merge boxes that are clearly fragments of one glyph/word.

    Only near-touching boxes on the same visual line are merged.  Meaningful
    word gaps remain separate, which lets :func:`render_lines` recover them
    from geometry.  The function is deliberately conservative around normal
    word-sized gaps.
    """

    merged_lines: list[list[OCRWord]] = []
    for source_line in lines:
        line = sorted(source_line, key=lambda item: item.bbox.x)
        if not line:
            merged_lines.append([])
            continue
        result = [line[0]]
        for word in line[1:]:
            previous = result[-1]
            gap = word.bbox.x - (previous.bbox.x + previous.bbox.width)
            height = max(1, min(previous.bbox.height, word.bbox.height))
            punctuation_join = (
                word.text[:1] in _NO_SPACE_BEFORE
                or previous.text[-1:] in _NO_SPACE_AFTER
            )
            if gap <= max(2, round(height * 0.14)) or (punctuation_join and gap <= round(height * 0.35)):
                result[-1] = _merge_words(previous, word, gap)
            else:
                result.append(word)
        merged_lines.append(result)
    return merged_lines


# lines 데이터를 타깃 포맷으로 렌더링함
def render_lines(lines: Iterable[Iterable[OCRWord]]) -> str:
    """Render ordered OCR lines while deriving spaces from box gaps."""

    rendered: list[str] = []
    for source_line in lines:
        line = sorted(source_line, key=lambda item: item.bbox.x)
        if not line:
            rendered.append("")
            continue
        parts = [line[0].text]
        for previous, current in zip(line, line[1:]):
            gap = current.bbox.x - (previous.bbox.x + previous.bbox.width)
            height = max(1, min(previous.bbox.height, current.bbox.height))
            space_threshold = max(3, round(height * 0.22))
            needs_space = gap >= space_threshold
            if current.text[:1] in _NO_SPACE_BEFORE or previous.text[-1:] in _NO_SPACE_AFTER:
                needs_space = False
            parts.append((" " if needs_space else "") + current.text)
        rendered.append("".join(parts))
    return "\n".join(rendered)


# 병합 words 작업을 수행함
def _merge_words(left: OCRWord, right: OCRWord, gap: int) -> OCRWord:
    separator = "" if gap <= 0 or right.text[:1] in _NO_SPACE_BEFORE else ""
    text = f"{left.text}{separator}{right.text}"
    left_box, right_box = left.bbox, right.bbox
    x = min(left_box.x, right_box.x)
    y = min(left_box.y, right_box.y)
    right_edge = max(left_box.x + left_box.width, right_box.x + right_box.width)
    bottom = max(left_box.y + left_box.height, right_box.y + right_box.height)
    total_area = max(1, left_box.area + right_box.area)
    confidence = (
        left.confidence * left_box.area + right.confidence * right_box.area
    ) / total_area
    return OCRWord(
        text=text,
        confidence=confidence,
        bbox=BoundingBox(x, y, right_edge - x, bottom - y),
    )
