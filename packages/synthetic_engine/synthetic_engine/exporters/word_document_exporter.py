"""Word document rendering routines used by the export facade.

The block parser remains in :mod:`document_exporter` for now because it is
also used by the legacy in-place export path.  This module owns the three
format renderers so the facade does not contain format-specific loops.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Dict, List

from .errors import DocumentExportError
from .document_exporter import _markdown_escape_cell, _word_blocks


def convert_word_to_markdown(input_path: Path) -> str:
    """Convert a Word document's logical blocks to Markdown."""
    md: List[str] = []
    for block in _word_blocks(Path(input_path)):
        if block["type"] == "heading":
            md.append("#" * int(block.get("level", 1)) + " " + block["text"])
        elif block["type"] in {"list", "list_item"}:
            marker = "1." if block.get("ordered") else "-"
            prefix = "  " * int(block.get("level", 0))
            for line in block["text"].splitlines():
                if line.strip():
                    md.append(f"{prefix}{marker} {line.strip()}")
        elif block["type"] == "table":
            rows = block["rows"]
            width = max(sum(int(c.get("colspan", 1)) for c in row if not c.get("skip")) for row in rows)
            matrix: List[List[str]] = []
            for row in rows:
                out_row: List[str] = []
                for cell in row:
                    if cell.get("skip"):
                        out_row.extend([""] * int(cell.get("colspan", 1)))
                    else:
                        out_row.append(_markdown_escape_cell(cell.get("text", "")))
                        out_row.extend([""] * (int(cell.get("colspan", 1)) - 1))
                matrix.append(out_row + [""] * (width - len(out_row)))
            if matrix:
                md.append("| " + " | ".join(matrix[0]) + " |")
                md.append("| " + " | ".join(["---"] * width) + " |")
                for row in matrix[1:]:
                    md.append("| " + " | ".join(row) + " |")
        else:
            md.append(block["text"])
        md.append("")
    return "\n".join(md).strip()


def convert_word_to_html(input_path: Path) -> str:
    """Convert a Word document's logical blocks to an HTML fragment."""
    html_parts: List[str] = []
    open_lists: List[bool] = []

    def close_lists(to_level: int = 0) -> None:
        while len(open_lists) > to_level:
            ordered = open_lists.pop()
            html_parts.append("</ol>" if ordered else "</ul>")

    for block in _word_blocks(Path(input_path)):
        if block["type"] == "heading":
            close_lists()
            level = int(block.get("level", 1))
            html_parts.append(f"<h{level}>{block.get('html') or escape(block['text'])}</h{level}>")
        elif block["type"] in {"list", "list_item"}:
            level = int(block.get("level", 0))
            ordered = bool(block.get("ordered"))
            while len(open_lists) > level + 1:
                close_lists(len(open_lists) - 1)
            while len(open_lists) < level + 1:
                open_lists.append(ordered)
                html_parts.append("<ol>" if ordered else "<ul>")
            if open_lists[-1] != ordered:
                close_lists(level)
                open_lists.append(ordered)
                html_parts.append("<ol>" if ordered else "<ul>")
            for line in block["html"].splitlines():
                if line.strip():
                    html_parts.append(f"<li>{line.strip()}</li>")
        elif block["type"] == "table":
            close_lists()
            rows_html: List[str] = []
            for row_index, row in enumerate(block["rows"]):
                cell_tag = "th" if row_index == 0 else "td"
                cells_html = []
                for cell in row:
                    if cell.get("skip"):
                        continue
                    colspan = int(cell.get("colspan", 1))
                    attr = f' colspan="{colspan}"' if colspan > 1 else ""
                    value = cell.get("html") or escape(cell.get("text", "")).replace("\n", "<br/>")
                    cells_html.append(f"<{cell_tag}{attr}>{value}</{cell_tag}>")
                rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
            html_parts.append("<table>" + "".join(rows_html) + "</table>")
        else:
            close_lists()
            html_parts.append(f"<p>{block.get('html') or escape(block['text']).replace(chr(10), '<br/>')}</p>")
    close_lists()
    return "\n".join(html_parts)


def convert_word_to_hwpx(input_path: Path, output_path: Path) -> Path:
    """Convert a Word document's logical blocks to HWPX."""
    from hwpx.document import HwpxDocument

    doc = HwpxDocument.new()
    for block in _word_blocks(Path(input_path)):
        if block["type"] == "heading":
            try:
                doc.add_heading(block["text"], level=int(block.get("level", 1)))
            except Exception:
                doc.add_paragraph(block["text"])
        elif block["type"] in {"list", "list_item"}:
            marker = "1." if block.get("ordered") else "-"
            prefix = "  " * int(block.get("level", 0))
            for line in block["text"].splitlines():
                if line.strip():
                    doc.add_paragraph(f"{prefix}{marker} {line.strip()}")
        elif block["type"] == "table":
            rows = block["rows"]
            width = max(sum(int(c.get("colspan", 1)) for c in row if not c.get("skip")) for row in rows)
            table = doc.add_table(rows=len(rows), cols=width)
            try:
                table.set_column_widths([max(4000, int(42000 / max(width, 1)))] * width)
            except Exception:
                pass
            for row_index, row in enumerate(rows):
                col = 0
                for cell in row:
                    span = int(cell.get("colspan", 1))
                    if cell.get("skip"):
                        col += span
                        continue
                    try:
                        table.set_cell_text(row_index, col, cell.get("text", ""))
                        if row_index == 0:
                            table.set_cell_shading(row_index, col, "#EEF3F8")
                        if span > 1:
                            table.merge_cells(row_index, col, row_index, min(width - 1, col + span - 1))
                    except Exception:
                        pass
                    col += span
        else:
            doc.add_paragraph(block["text"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(output_path)
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise DocumentExportError(f"HWPX conversion produced no output: {output_path.name}")
    return output_path


__all__ = ["convert_word_to_markdown", "convert_word_to_html", "convert_word_to_hwpx"]
