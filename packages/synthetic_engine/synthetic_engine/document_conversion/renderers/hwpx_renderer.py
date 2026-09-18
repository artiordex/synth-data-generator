# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: hwpx_renderer.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/renderers/hwpx_renderer.py
# 목적: IR 트리를 공공 표준 HWPX 한글 문서로 렌더링함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Use python-hwpx package construction for IR text and nested merged tables."""
from ..core.enums import ImagePlacement
from ..core.ir import ConversionWarning, ImageIR, ParagraphIR, TableIR
from ..core.capabilities import TargetCapabilities
from ..geometry.table_geometry import build_virtual_grid
from .text import inline_text


class HwpxRenderer:
    capabilities = TargetCapabilities(supports_nested_tables=True, supports_rowspan=True, supports_colspan=True)

    # render 작업을 수행함
    def render(self, document, output_path):
        """
            @description 문서 중간 표현을 대상 포맷으로 렌더링함
            @param {document} - 메서드 입력값임
            @param {output_path} - 메서드 입력값임
        """
        from hwpx.document import HwpxDocument
        output = HwpxDocument.new()

        # 이미지 항목을 목록에 추가함
        def add_image(container, image: ImageIR) -> None:
            """
                @description 이미지 리소스를 렌더링 대상 목록에 추가함
                @param {container} - 메서드 입력값임
                @param {image} - 메서드 입력값임
                @returns {None} - 메서드 실행 결과를 반환함
            """
            if image.placement != ImagePlacement.INLINE or image.opacity != 1 or image.rotation_deg != 0:
                document.warnings.append(ConversionWarning(
                    'HWPX_UNMAPPED_CONTENT',
                    'HWPX renderer cannot fully map image placement, opacity or rotation.',
                    source_ref=image.source_ref,
                    feature='image-placement-or-transform',
                ))
            try:
                paragraph = container.add_paragraph("", include_run=False)
            except TypeError:
                paragraph = container.add_paragraph("")
            binary = output.media.add_image(image.image_bytes, (image.format or 'png').lower())
            paragraph.add_picture(
                binary.item_id,
                width=max(1, round(image.width_pt * 100)),
                height=max(1, round(image.height_pt * 100)),
            )

        tasks = [(block, output) for section in reversed(document.sections) for block in reversed(section.elements)]
        while tasks:
            block, container = tasks.pop()
            if isinstance(block, ParagraphIR):
                container.add_paragraph(inline_text(block.inlines))
            elif isinstance(block, TableIR):
                grid = build_virtual_grid(block)
                if not grid or not grid[0]:
                    continue
                table = container.add_table(rows=len(grid), cols=len(grid[0]))
                if block.column_widths_pt:
                    table.set_column_widths([round(width * 100) for width in block.column_widths_pt])
                children = []
                for row in block.rows:
                    for cell in row:
                        if cell.row_span > 1 or cell.col_span > 1:
                            table.merge_cells(cell.row_index, cell.col_index,
                                              cell.row_index+cell.row_span-1, cell.col_index+cell.col_span-1)
                        target = table.cell(cell.row_index, cell.col_index)
                        children.extend((child, target) for child in cell.content)
                tasks.extend(reversed(children))
            elif isinstance(block, ImageIR):
                add_image(container, block)
                if block.caption is not None:
                    tasks.append((block.caption, container))
            else:
                container.add_paragraph('Unsupported source object')
        output.save_to_path(output_path)
        return output_path
