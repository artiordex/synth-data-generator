"""Edit copies of Hancom-converted templates; never rebuild their style tables."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from html import escape
from pathlib import Path
import re
from zipfile import ZipFile

from lxml import etree as ET

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP}
TEMPLATE_NAMES = {
    "original_spec": "원본데이터 명세서.hwpx",
    "synthetic_spec": "합성데이터 명세서.hwpx",
    "review_report": "측정결과서.hwpx",
}


def tag(name):
    return f"{{{HP}}}{name}"


def text_of(element):
    return "".join(element.xpath(".//hp:t//text()", namespaces=NS))


def cell_at(table, row, column):
    """Address an anchor cell, rather than a physical index in a merged row."""
    for cell in table.findall("hp:tr/hp:tc", NS):
        addr = cell.find("hp:cellAddr", NS)
        if int(addr.get("rowAddr")) == row and int(addr.get("colAddr")) == column:
            return cell
    raise ValueError(f"템플릿 셀을 찾을 수 없습니다: 행 {row}, 열 {column}")


def set_paragraph(paragraph, text):
    """Retain the template paragraph and first text-run styles, clear old content."""
    runs = paragraph.findall("hp:run", NS)
    run_attrs = dict(runs[0].attrib) if runs else {"charPrIDRef": "0"}
    for child in list(paragraph):
        paragraph.remove(child)
    run = ET.SubElement(paragraph, tag("run"), run_attrs)
    node = ET.SubElement(run, tag("t"))
    # A text cell contains text only: no inherited drawing or stale line-layout cache.
    parts = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text)).split("\n")
    node.text = parts[0]
    for line in parts[1:]:
        ET.SubElement(node, tag("lineBreak")).tail = line


def set_cell(cell, text):
    sublist = cell.find("hp:subList", NS)
    paragraphs = sublist.findall("hp:p", NS)
    if not paragraphs:
        raise ValueError("본문 문단이 없는 템플릿 셀입니다.")
    set_paragraph(paragraphs[0], text)
    for p in paragraphs[1:]:
        sublist.remove(p)


def put(table, row, column, text):
    set_cell(cell_at(table, row, column), text)


def update_geometry(table):
    """Reindex anchor rows and reconcile the size of vertically merged cells."""
    rows = table.findall("hp:tr", NS)
    heights = []
    for index, row in enumerate(rows):
        row_heights = []
        for cell in row.findall("hp:tc", NS):
            cell.find("hp:cellAddr", NS).set("rowAddr", str(index))
            if int(cell.find("hp:cellSpan", NS).get("rowSpan")) == 1:
                row_heights.append(int(cell.find("hp:cellSz", NS).get("height")))
        heights.append(max(row_heights, default=1500))
    for index, row in enumerate(rows):
        for cell in row.findall("hp:tc", NS):
            span = int(cell.find("hp:cellSpan", NS).get("rowSpan"))
            cell.find("hp:cellSz", NS).set("height", str(sum(heights[index:index + span])))
    table.set("rowCnt", str(len(rows)))
    table.find("hp:sz", NS).set("height", str(sum(heights)))
    # Hancom ignores multi-page support for tables treated as a single character.
    # TABLE permits a vertically merged dataset cell to continue across pages.
    table.find("hp:pos", NS).set("treatAsChar", "0")
    table.set("textWrap", "TOP_AND_BOTTOM")
    table.set("pageBreak", "TABLE")
    table.set("noAdjust", "0")
    # Drop the enclosing paragraph's obsolete cached line layout, not its style.
    parent_p = table.getparent().getparent()
    for cache in parent_p.findall("hp:linesegarray", NS):
        parent_p.remove(cache)


def replace_rows(table, start, stop, values, prototype_index=None):
    """Replace a rectangular body region using a styled original row per column."""
    rows = table.findall("hp:tr", NS)
    prototype = deepcopy(rows[start if prototype_index is None else prototype_index])
    insertion = table.index(rows[start])
    for row in rows[start:stop]:
        table.remove(row)
    for offset, row_values in enumerate(values):
        row = deepcopy(prototype)
        cells = row.findall("hp:tc", NS)
        if len(row_values) != len(cells):
            raise ValueError("템플릿 본문 열 수와 입력 열 수가 다릅니다.")
        for cell, value in zip(cells, row_values):
            if int(cell.find("hp:cellSpan", NS).get("rowSpan")) != 1:
                raise ValueError("일반 행 복제에 세로 병합 셀이 포함되어 있습니다.")
            set_cell(cell, value)
        table.insert(insertion + offset, row)
    update_geometry(table)


def output_columns(context, synthetic=False):
    cols = context["columns"]
    if not synthetic:
        return cols
    by_name = {c["name"]: c for c in cols}
    return [
        {**by_name[name], "description": by_name[name]["synthetic_description"]}
        if name in by_name else {"name": name, "dtype": "생성 항목", "information_type": "분류 확인 필요",
                                "description": "처리 규칙에 의해 추가된 항목; 의미 확인 필요", "method": "규칙 생성", "note": "담당자 확인 필요"}
        for name in context["synthetic_columns"]
    ]


def bind_privacy_rows(table, context, columns):
    # Keep the original three header rows, including their 2-column/2-row merges.
    rows = table.findall("hp:tr", NS)
    first, later = deepcopy(rows[3]), deepcopy(rows[4])
    insertion = table.index(rows[3])
    for row in rows[3:]:
        table.remove(row)
    effective = columns or [{"name": "해당 항목 없음", "information_type": "-", "method": "-", "note": "빈 데이터"}]
    for index, col in enumerate(effective):
        row = deepcopy(first if index == 0 else later)
        for cell in row.findall("hp:tc", NS):
            col_addr = int(cell.find("hp:cellAddr", NS).get("colAddr"))
            if col_addr < 2:
                cell.find("hp:cellSpan", NS).set("rowSpan", str(len(effective)))
            values = {0: "1", 1: context["dataset_name"], 2: col["name"], 3: col["information_type"],
                      4: col["method"], 5: "자동 처리", 6: col["note"]}
            set_cell(cell, values[col_addr])
        table.insert(insertion + index, row)
    put(table, 0, 0, "개인정보 처리계획\n" + context["privacy_plan"])
    update_geometry(table)


def bind_privacy(root, table, context, columns):
    # Hancom clips a merged dataset cell taller than a page even with TABLE flow.
    # Keep each merged group bounded and repeat the original three header rows.
    paragraph = table.getparent().getparent()
    parent = paragraph.getparent()
    source = deepcopy(paragraph)
    insertion = parent.index(paragraph)
    max_id = max(int(t.get("id", "0")) for t in root.findall(".//hp:tbl", NS))
    max_z = max(int(t.get("zOrder", "0")) for t in root.findall(".//hp:tbl", NS))
    for group, offset in enumerate(range(0, max(1, len(columns)), 8)):
        p = paragraph if group == 0 else deepcopy(source)
        current = p.find(".//hp:tbl", NS)
        bind_privacy_rows(current, context, columns[offset:offset + 8])
        if group:
            current.set("id", str(max_id + group))
            current.set("zOrder", str(max_z + group))
            p.set("pageBreak", "1")
            parent.insert(insertion + group, p)


def bind_examples(root, table, names, values):
    """Clone the original example table in groups of its existing column count."""
    paragraph = table.getparent().getparent()
    parent = paragraph.getparent()
    base_columns = int(table.get("colCnt"))
    source = deepcopy(paragraph)
    table_width = int(table.find("hp:sz", NS).get("width"))
    insertion = parent.index(paragraph)
    max_id = max(int(t.get("id", "0")) for t in root.findall(".//hp:tbl", NS))
    max_z = max(int(t.get("zOrder", "0")) for t in root.findall(".//hp:tbl", NS))
    for group, offset in enumerate(range(0, max(1, len(names)), base_columns)):
        p = paragraph if group == 0 else deepcopy(source)
        current = p.find(".//hp:tbl", NS)
        group_names = names[offset:offset + base_columns] or ["항목 없음"]
        group_values = [r[offset:offset + base_columns] for r in values] if names else []
        source_rows = current.findall("hp:tr", NS)
        header, body = deepcopy(source_rows[0]), deepcopy(source_rows[1])
        row_insertion = current.index(source_rows[0])
        for row in source_rows:
            current.remove(row)
        for rindex, row_values in enumerate([group_names] + group_values):
            row = deepcopy(header if rindex == 0 else body)
            cells = row.findall("hp:tc", NS)
            for extra in cells[len(group_names):]:
                row.remove(extra)
            # Column labels change with the dataset: avoid inheriting very narrow
            # sample-specific columns, while retaining the original total width.
            selected_widths = [table_width // len(group_names)] * len(group_names)
            selected_widths[-1] += table_width - sum(selected_widths)
            for col, value in enumerate(row_values):
                cell = row.findall("hp:tc", NS)[col]
                cell.find("hp:cellAddr", NS).set("colAddr", str(col))
                cell.find("hp:cellSz", NS).set("width", str(selected_widths[col]))
                set_cell(cell, value)
            current.insert(row_insertion + rindex, row)
        current.set("colCnt", str(len(group_names)))
        if group:
            current.set("id", str(max_id + group))
            current.set("zOrder", str(max_z + group))
            parent.insert(insertion + group, p)
        update_geometry(current)


def validate_grid(root):
    for table in root.findall(".//hp:tbl", NS):
        rows, cols = int(table.get("rowCnt")), int(table.get("colCnt"))
        covered = set()
        if len(table.findall("hp:tr", NS)) != rows:
            raise ValueError("템플릿 표 행 수가 일치하지 않습니다.")
        for cell in table.findall("hp:tr/hp:tc", NS):
            addr, span = cell.find("hp:cellAddr", NS), cell.find("hp:cellSpan", NS)
            for r in range(int(addr.get("rowAddr")), int(addr.get("rowAddr")) + int(span.get("rowSpan"))):
                for c in range(int(addr.get("colAddr")), int(addr.get("colAddr")) + int(span.get("colSpan"))):
                    if r >= rows or c >= cols or (r, c) in covered:
                        raise ValueError("템플릿 병합 셀이 겹치거나 표 범위를 벗어납니다.")
                    covered.add((r, c))
        if len(covered) != rows * cols:
            raise ValueError("템플릿 표에 누락된 셀이 있습니다.")


def verify_template(tables, kind):
    count = {"original_spec": 6, "synthetic_spec": 4, "review_report": 4}[kind]
    if len(tables) != count:
        raise ValueError(f"지원하지 않는 템플릿 구조: {kind}, 표 {len(tables)}개")
    expected = [(1, 0, 0, "연번"), (2, 0, 3, "항목명")] if kind != "review_report" else [(2, 0, 0, "모형"), (3, 0, 0, "총평")]
    for t, r, c, label in expected:
        if text_of(cell_at(tables[t], r, c)).strip() != label:
            raise ValueError(f"템플릿 기준 셀 불일치: {label}")


def bind_section(root, context, kind):
    tables = root.findall(".//hp:tbl", NS)
    verify_template(tables, kind)
    c = context
    if kind == "review_report":
        # Formula drawings and the original measurement-method table remain intact.
        put(tables[2], 0, 1, c["model"])
        results = [r[:3] for r in c["measurements"]]
        results += [["유용성", f"JSD: {name}", value] for name, value in c["jsd_by_column"]]
        replace_rows(tables[2], 2, 4, results)
        summary = (f"※ 데이터명: {c['dataset_name']}\n※ 담당 부서: {c['department']} / 목적: {c['purpose']}\n"
                   f"※ 원본 {c['original_rows']:,}건 / 합성 {c['synthetic_rows']:,}건\n"
                   f"※ {c['model']} 모형\n※ {c['assessment']}\n"
                   "※ 구간화 원본 중복 비율은 재식별 확률과 다른 지표임.\n"
                   + "\n".join(f"{row[1]}: {row[2]}" for row in c["measurements"]) +
                   (f"\n※ 수치 노이즈 처리: {c['dp']}" if c["dp"].get("enabled") else "\n※ 수치 노이즈 처리: 미적용"))
        put(tables[3], 1, 0, summary)
        for paragraph in root.findall("hp:p", NS):
            if text_of(paragraph) == "4) 결과평가":
                paragraph.set("pageBreak", "1")
        return

    synthetic = kind == "synthetic_spec"
    columns = output_columns(c, synthetic)
    rows = c["synthetic_rows"] if synthetic else c["original_rows"]
    put(tables[0], 1, 1, c["dataset_name"])
    put(tables[0], 1, 2, c["department"])
    put(tables[0], 2, 1, "정형데이터")
    put(tables[0], 2, 2, "CSV / XLSX" if synthetic else Path(c["original_filename"]).suffix.upper().lstrip("."))
    put(tables[0], 3, 1, f"{rows:,}건")
    put(tables[0], 3, 2, f"{len(columns):,}개 항목")
    put(tables[0], 4, 1, f"{c['special_notes']}\n정보 개요: {c['overview']}\n활용 목적: {c['purpose']}")
    counts = Counter(col["information_type"] for col in columns)
    replace_rows(tables[1], 1, 3, [[i, group, n, "100%" if n == len(columns) else f"{n / max(1, len(columns)):.1%}", "자동 탐지 또는 담당자 입력 기준"] for i, (group, n) in enumerate(counts.items(), 1)])
    total_row = int(tables[1].get("rowCnt")) - 1
    put(tables[1], total_row, 2, len(columns))
    put(tables[1], total_row, 3, "100%" if columns else "0%")
    put(tables[1], total_row, 4, "전체 항목")
    replace_rows(tables[2], 1, 9, [[i, col["dtype"], col["information_type"], col["name"], col["description"]] for i, col in enumerate(columns, 1)])
    names = [col["name"] for col in columns]
    examples = c["synthetic_examples"] if synthetic else c["original_examples"]
    for paragraph in root.findall("hp:p", NS):
        if text_of(paragraph) in {"3) 원본데이터 예시", "3) 합성데이터 예시"}:
            # Start the variable-width example block together with its heading.
            paragraph.set("pageBreak", "1")
        if text_of(paragraph).startswith("4) 항목별 개인정보 처리 계획"):
            paragraph.set("pageBreak", "1")
        if text_of(paragraph).startswith("※") and "행 중" in text_of(paragraph):
            set_paragraph(paragraph, f"※{rows:,}행 중 {len(examples)}행 / " + ("식별값 비공개" if synthetic else "원본값 비공개"))
    bind_examples(root, tables[3], names, examples)
    if not synthetic:
        bind_privacy(root, tables[5], c, columns)


def write_template(context, kind, template_dir, output_path):
    source = Path(template_dir) / TEMPLATE_NAMES[kind]
    if not source.exists():
        raise FileNotFoundError(f"원본 서식 템플릿이 필요합니다: {source}. scripts/convert_review_templates.ps1로 원본 HWP를 변환하세요.")
    source_bytes = source.read_bytes()
    with ZipFile(source) as archive:
        parts = {info.filename: archive.read(info) for info in archive.infolist()}
        infos = archive.infolist()
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    root = ET.fromstring(parts["Contents/section0.xml"], parser)
    bind_section(root, context, kind)
    validate_grid(root)
    parts["Contents/section0.xml"] = ET.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)
    parts["Preview/PrvText.txt"] = "\n".join(root.xpath(".//hp:t/text()", namespaces=NS)).encode("utf-8")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".hwpx.tmp")
    try:
        with ZipFile(temporary, "w") as archive:
            for info in infos:
                # Do not show the original sample's screenshot as the output preview.
                if info.filename == "Preview/PrvImage.png":
                    continue
                archive.writestr(info, parts[info.filename])
        with ZipFile(temporary) as archive:
            assert archive.read("Contents/header.xml") == parts["Contents/header.xml"]
            validate_grid(ET.fromstring(archive.read("Contents/section0.xml"), parser))
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    output_path.with_suffix(".html").write_text(html_preview(root), encoding="utf-8")
    return {"template": source.name, "sha256": sha256(source_bytes).hexdigest()}


def html_preview(root):
    """Content-only preview, including the template's merged table structure."""
    parts = ['<!doctype html><html lang="ko"><meta charset="utf-8"><title>심의자료 내용 확인</title><style>body{font:14px/1.6 sans-serif;max-width:1000px;margin:32px auto}table{border-collapse:collapse;width:100%;margin:12px 0}td{border:1px solid #555;padding:6px;white-space:pre-wrap;overflow-wrap:anywhere}</style><body><p>내용 확인본 · 실제 한글 서식은 HWPX 파일을 확인하세요.</p>']
    for p in root.findall("hp:p", NS):
        table = p.find("hp:run/hp:tbl", NS)
        if table is None:
            parts.append(f"<p>{escape(text_of(p))}</p>")
        else:
            parts.append("<table>")
            for row in table.findall("hp:tr", NS):
                parts.append("<tr>")
                for cell in row.findall("hp:tc", NS):
                    span = cell.find("hp:cellSpan", NS)
                    parts.append(f'<td rowspan="{span.get("rowSpan")}" colspan="{span.get("colSpan")}">{escape(text_of(cell))}</td>')
                parts.append("</tr>")
            parts.append("</table>")
    return "".join(parts) + "</body></html>"
