# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: common.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/common.py
# 목적: 문서 파서 공통 유틸리티 및 기본 베이스 파서를 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Shared bounded geometry checks and original image payload mapping."""
from dataclasses import replace
from io import BytesIO

from ..core.ir import ImageIR
from ..exceptions import DocumentConversionError


# 표(테이블) 크기 유효성 및 상태를 점검함
def check_table_size(rows, columns):
    if rows < 0 or columns < 0 or rows > 10000 or columns > 10000 or rows * columns > 1000000:
        raise DocumentConversionError('Table exceeds logical grid limits')


# 표(테이블) source refs 작업을 수행함
def table_source_refs(table, node, table_tag):
    """Keep nested table identity local while adding logical cell addresses."""
    table.depth = sum(parent.tag == table_tag for parent in node.iterancestors())
    table.source_ref = replace(table.source_ref, table_id=table.table_id)
    for row in table.rows:
        for cell in row:
            cell.source_ref = replace(cell.source_ref, table_id=table.table_id,
                                      row_index=cell.row_index, col_index=cell.col_index)


# 이미지 from bytes 작업을 수행함
def image_from_bytes(data, width_pt, height_pt, ref):
    """Inspect raster headers without transcoding or loading full pixel arrays."""
    from PIL import Image
    with Image.open(BytesIO(data)) as decoded:
        width, height = decoded.size
        fmt = decoded.format.lower()
        mime = Image.MIME.get(decoded.format, 'application/octet-stream')
    return ImageIR(data, mime, fmt, width_pt, height_pt,
                   original_width_px=width, original_height_px=height, source_ref=ref)
