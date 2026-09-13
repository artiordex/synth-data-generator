# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_high_accuracy.py
# 경로: packages/synthetic_engine/tests/test_ocr_high_accuracy.py
# 목적: 고정밀 OCR 인식 파이프라인 품질 지표를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

import cv2
import numpy as np
import re
import zipfile

from openpyxl import load_workbook

from synthetic_engine.exporters import ocr_table_reconstructor as reconstructor
from synthetic_engine.exporters.ocr_table_reconstructor import (
    GridCell,
    OCRPageResult,
    OCRFigureBlock,
    OCRTable,
    OCRTableCell,
    OCRTextBlock,
    OCRWord,
    assign_words_to_tables,
    convert_ocr_result_to_html,
    convert_ocr_result_to_markdown,
    convert_ocr_result_to_hwpx,
    convert_ocr_result_to_xlsx,
    detect_borderless_table_cells,
    detect_table_grid_cells,
    process_scanned_page,
    recognize_table_cells,
    resolve_span_conflicts,
    remove_table_lines_for_handwriting,
    snap_grid_boundaries,
)
from synthetic_engine.exporters.ocr_style_extractor import (
    detect_cell_border_styles,
    detect_text_alignment,
    extract_cell_background_color,
)
from synthetic_engine.exporters.ocr_fidelity import (
    bind_form_key_value_pairs,
    correct_public_form_header,
    normalize_form_value,
)
from synthetic_engine.exporters.handwriting_vlm import (
    detect_checkbox_state,
    detect_signature_or_seal,
    refine_handwritten_cell,
)


# iou 작업을 수행함
def _iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    ix0, iy0 = max(left[0], right[0]), max(left[1], right[1])
    ix1, iy1 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    return intersection / max(1, left_area + right_area - intersection)


# bordered 표(테이블) 격자 구조 detection iou 기능의 정상 동작 및 제약조건을 테스트함
def test_bordered_table_grid_detection_iou() -> None:
    image = np.full((260, 380), 255, dtype=np.uint8)
    for x in (40, 140, 240, 340):
        cv2.line(image, (x, 30), (x, 230), 0, 2)
    for y in (30, 95, 160, 230):
        cv2.line(image, (40, y), (340, y), 0, 2)

    tables = detect_table_grid_cells(image, min_table_area=4_000)

    assert len(tables) == 1
    assert tables[0].rows_count == 3
    assert tables[0].cols_count == 3
    assert _iou(tables[0].bbox, (40, 30, 341, 231)) >= 0.95


# borderless 표(테이블) projection 프로파일 기능의 정상 동작 및 제약조건을 테스트함
def test_borderless_table_projection_profile() -> None:
    image = np.full((240, 360), 255, dtype=np.uint8)
    words = [
        OCRWord(f"r{row}c{col}", (30 + col * 105, 25 + row * 60,
                                  88 + col * 105, 45 + row * 60), 0.99)
        for row in range(3)
        for col in range(3)
    ]

    cells = detect_borderless_table_cells(image, words)

    assert len(cells) == 9
    assert {(cell.row_start, cell.col_start) for cell in cells} == {
        (row, col) for row in range(3) for col in range(3)
    }
    assert all(not cell.is_border_detected for cell in cells)
    assert snap_grid_boundaries([10, 14], [15, 50], tolerance=5) == [13, 50]


# process 페이지 recovers mixed ruled and borderless 표 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_process_page_recovers_mixed_ruled_and_borderless_tables(monkeypatch) -> None:
    image = np.full((520, 520, 3), 255, dtype=np.uint8)
    for x in (30, 150, 270):
        cv2.line(image, (x, 30), (x, 190), (0, 0, 0), 2)
    for y in (30, 110, 190):
        cv2.line(image, (30, y), (270, y), (0, 0, 0), 2)
    words = [
        OCRWord("유괘선", (50, 58, 120, 82), 0.99),
        OCRWord("r0c0", (310, 250, 360, 270), 0.99),
        OCRWord("r0c1", (430, 250, 480, 270), 0.99),
        OCRWord("r1c0", (310, 330, 360, 350), 0.99),
        OCRWord("r1c1", (430, 330, 480, 350), 0.99),
    ]
    monkeypatch.setattr(
        "synthetic_engine.exporters.ocr_table_reconstructor._run_ocr_on_image",
        lambda _: words,
    )
    monkeypatch.setattr(
        "synthetic_engine.exporters.ocr_table_reconstructor.detect_image_figures",
        lambda *args, **kwargs: [],
    )

    page = process_scanned_page(image, 1)

    assert len(page.tables) == 2
    assert any(table.rows_count == 2 and table.cols_count == 2 for table in page.tables)
    assert _iou(page.tables[0].bbox, page.tables[1].bbox) == 0.0
    assert page.text_blocks == []
    for word in ("유괘선", "r0c0", "r0c1", "r1c0", "r1c1"):
        assert page.full_text.count(word) == 1
    borderless = next(table for table in page.tables if not all(cell.is_border_detected for cell in table.cells))
    assert borderless.to_grid() == [["r0c0", "r0c1"], ["r1c0", "r1c1"]]


# complex colspan rowspan conflict resolution 기능의 정상 동작 및 제약조건을 테스트함
def test_complex_colspan_rowspan_conflict_resolution() -> None:
    cells = [
        GridCell(row, row + 1, col, col + 1,
                 (col * 100, row * 50, (col + 1) * 100, (row + 1) * 50))
        for row in range(2)
        for col in range(3)
    ]
    words = [
        OCRWord("통합 제목", (10, 8, 290, 42), 0.99),
        OCRWord("세로 후보", (8, 5, 92, 95), 0.99),
    ]

    resolved = resolve_span_conflicts(cells, words)

    assert len(resolved) == 4
    header = next(cell for cell in resolved if cell.row_start == 0)
    assert (header.rowspan, header.colspan) == (1, 3)
    occupied = {
        (row, col)
        for cell in resolved
        for row in range(cell.row_start, cell.row_end)
        for col in range(cell.col_start, cell.col_end)
    }
    assert occupied == {(row, col) for row in range(2) for col in range(3)}


# 셀 background 색상 extraction 기능의 정상 동작 및 제약조건을 테스트함
def test_cell_background_color_extraction() -> None:
    image = np.full((100, 160, 3), (224, 216, 200), dtype=np.uint8)
    cv2.putText(image, "A", (65, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    color = extract_cell_background_color(image, (10, 10, 150, 90))

    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    assert all(abs(actual - expected) <= 5 for actual, expected in zip(rgb, (200, 216, 224)))
    cell = (0, 0, 200, 40)
    assert detect_text_alignment(cell, (8, 8, 70, 30)) == "left"
    assert detect_text_alignment(cell, (70, 8, 130, 30)) == "center"
    assert detect_text_alignment(cell, (130, 8, 192, 30)) == "right"


# 셀 테두리 스타일 서식 detection 기능의 정상 동작 및 제약조건을 테스트함
def test_cell_border_style_detection() -> None:
    image = np.full((140, 180), 255, dtype=np.uint8)
    cv2.line(image, (30, 30), (150, 30), 0, 2)
    cv2.line(image, (149, 30), (149, 110), 0, 1)
    cv2.line(image, (153, 30), (153, 110), 0, 1)
    for x in range(30, 150, 18):
        cv2.line(image, (x, 110), (min(x + 9, 150), 110), 0, 2)

    styles = detect_cell_border_styles(image, (30, 30, 150, 110))

    assert styles == {"top": "solid", "right": "double", "bottom": "dashed", "left": "none"}


# handwriting stroke separation 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_stroke_separation() -> None:
    image = np.full((180, 260), 255, dtype=np.uint8)
    cv2.line(image, (20, 60), (240, 60), 0, 2)
    cv2.line(image, (20, 120), (240, 120), 0, 2)
    cv2.line(image, (90, 20), (90, 160), 0, 2)
    cv2.line(image, (180, 20), (180, 160), 0, 2)
    handwriting = np.zeros_like(image)
    cv2.putText(handwriting, "27", (108, 105), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.4, 255, 2)
    image[handwriting > 0] = 0

    cleaned = remove_table_lines_for_handwriting(image, (15, 15, 245, 165), dpi=300)

    protected = handwriting > 0
    # Rule intersections are inherently shared pixels; score all other pen pixels.
    yy, xx = np.indices(image.shape)
    line_zone = (
        (np.abs(yy - 60) <= 2) | (np.abs(yy - 120) <= 2)
        | (np.abs(xx - 90) <= 2) | (np.abs(xx - 180) <= 2)
    )
    scored = protected & ~line_zone
    preservation = np.count_nonzero((cleaned < 128) & scored) / np.count_nonzero(scored)
    assert preservation >= 0.98
    assert np.mean(cleaned[60, 25:85] < 128) <= 0.03


# domain dictionary fuzzy correction 기능의 정상 동작 및 제약조건을 테스트함
def test_domain_dictionary_fuzzy_correction() -> None:
    variants = {
        "성 명": "성명", "생년월잎": "생년월일", "주민등록번오": "주민등록번호",
        "휴대전와번호": "휴대전화번호", "전자우펀": "전자우편", "도로명주쇼": "도로명주소",
        "우편번오": "우편번호", "담당부셔": "담당부서", "사업자등록번오": "사업자등록번호",
        "접수번오": "접수번호", "문서번오": "문서번호", "신청잎": "신청일",
        "처리내욤": "처리내용", "검토의건": "검토의견", "계좌번오": "계좌번호",
        "은 행 명": "은행명", "합 게": "합계", "연 락 처": "연락처",
        "공개여뷰": "공개여부", "사용목젹": "사용목적",
    }
    corrected = {candidate: correct_public_form_header(candidate) for candidate in variants}
    assert all(corrected[candidate] is not None for candidate in variants)
    assert {candidate: result[0] for candidate, result in corrected.items()} == variants


# regex date amount normalization 기능의 정상 동작 및 제약조건을 테스트함
def test_regex_date_amount_normalization() -> None:
    assert normalize_form_value("2026년 9월 9일") == "2026-09-09"
    assert normalize_form_value("2026. 09. 10") == "2026-09-10"
    assert normalize_form_value("1,23O,OOO원", "amount") == "1,230,000원"
    assert normalize_form_value("010 1234 5678") == "010-1234-5678"
    assert normalize_form_value("900101-1234567") == "900101-*******"
    assert normalize_form_value("[V]") == "■"
    assert normalize_form_value("[ ]") == "□"
    assert normalize_form_value("AB-OIS", "code") == "AB-015"


# form key value pair binding 기능의 정상 동작 및 제약조건을 테스트함
def test_form_key_value_pair_binding() -> None:
    cells = [
        {"row": 0, "col": 0, "text": "성 명"},
        {"row": 0, "col": 1, "text": "홍길동"},
        {"row": 1, "col": 0, "text": "생년월잎"},
        {"row": 1, "col": 1, "text": "1990년 1월 2일"},
        {"row": 2, "col": 0, "text": "접수번오: A-2026-17"},
        {"row": 3, "col": 0, "text": "검토의건"},
        {"row": 4, "col": 0, "text": "이상 없음"},
    ]

    pairs = bind_form_key_value_pairs(cells)

    assert [(pair.key, pair.value) for pair in pairs] == [
        ("성명", "홍길동"),
        ("생년월일", "1990-01-02"),
        ("접수번호", "A-2026-17"),
        ("검토의견", "이상 없음"),
    ]


# checkbox 이미지 작업을 수행함
def _checkbox_image(checked: bool) -> np.ndarray:
    image = np.full((80, 80, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (18, 18), (62, 62), (0, 0, 0), 3)
    if checked:
        cv2.line(image, (28, 40), (38, 52), (0, 0, 0), 4)
        cv2.line(image, (38, 52), (55, 28), (0, 0, 0), 4)
    return image


# checkbox state recognition 기능의 정상 동작 및 제약조건을 테스트함
def test_checkbox_state_recognition() -> None:
    assert detect_checkbox_state(_checkbox_image(False)) == (True, False)
    assert detect_checkbox_state(_checkbox_image(True)) == (True, True)


# signature and seal detection 기능의 정상 동작 및 제약조건을 테스트함
def test_signature_and_seal_detection() -> None:
    seal = np.full((80, 100, 3), 255, dtype=np.uint8)
    cv2.circle(seal, (50, 40), 22, (0, 0, 210), 5)
    signature = np.full((60, 140, 3), 255, dtype=np.uint8)
    points = np.array([[8, 40], [25, 20], [38, 43], [55, 12], [68, 42], [92, 18], [130, 38]])
    cv2.polylines(signature, [points.astype(np.int32)], False, (0, 0, 0), 3)
    assert detect_signature_or_seal(seal) == (True, "seal")
    assert detect_signature_or_seal(signature) == (True, "signature")


# handwriting vlm 폴백 deterministic 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_fallback_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("OCR_VLM_ENABLED", raising=False)
    result = refine_handwritten_cell(
        np.full((50, 120, 3), 255, dtype=np.uint8),
        {"ocr_confidence": 0.2, "ocr_text": "1O,5OO원", "expected_type": "amount"},
    )
    assert result.source == "heuristic_fallback"
    assert result.text == "10,500"
    repeated = refine_handwritten_cell(
        np.full((50, 120, 3), 255, dtype=np.uint8),
        {"ocr_confidence": 0.2, "ocr_text": "1O,5OO원", "expected_type": "amount"},
    )
    assert repeated == result


# special document symbols are not treated as garbage 기능의 정상 동작 및 제약조건을 테스트함
def test_special_document_symbols_are_not_treated_as_garbage() -> None:
    assert reconstructor._special_character_ratio("용량 5㎎/㎖, 면적 12㎡, 온도 25℃ ※ 확인") == 0.0


# 페이지 데이터를 외부 포맷으로 내보냄
def _export_page() -> OCRPageResult:
    # 셀 작업을 수행함
    def cell(row: int, col: int, text: str, bbox: tuple[int, int, int, int], **kwargs) -> OCRTableCell:
        return OCRTableCell(
            row=row,
            col=col,
            rowspan=kwargs.pop("rowspan", 1),
            colspan=kwargs.pop("colspan", 1),
            bbox=bbox,
            words=[OCRWord(text, (bbox[0] + 5, bbox[1] + 5, bbox[2] - 5, bbox[3] - 5), 0.99)],
            **kwargs,
        )

    table = OCRTable(
        bbox=(0, 0, 300, 100),
        rows_count=2,
        cols_count=3,
        cells=[
            cell(0, 0, "통합 제목", (0, 0, 300, 50), colspan=3,
                 bg_color_hex="#dbeafe", text_align="center",
                 border_styles={side: "solid" for side in ("top", "right", "bottom", "left")}),
            cell(1, 0, "성명\n(필수)", (0, 50, 100, 100)),
            cell(1, 1, "홍길동", (100, 50, 200, 100)),
            cell(1, 2, "선택", (200, 50, 300, 100), control_type="checkbox", control_state="checked"),
        ],
    )
    return OCRPageResult(page_num=1, width=300, height=100, tables=[table])


# HTML 웹 문서 preserves 셀 너비 목록 escapes review warning and 셀 figures 기능의 정상 동작 및 제약조건을 테스트함
def test_html_preserves_cell_widths_escapes_review_warning_and_cell_figures() -> None:
    figure_image = np.full((30, 40, 3), 255, dtype=np.uint8)
    cv2.circle(figure_image, (20, 15), 10, (0, 0, 220), -1)
    ok, encoded = cv2.imencode(".png", figure_image)
    assert ok
    figure = OCRFigureBlock(
        bbox=(120, 20, 160, 50),
        image_bytes=encoded.tobytes(),
        format="png",
        width=40,
        height=30,
    )
    table = OCRTable(
        bbox=(0, 0, 300, 90),
        rows_count=1,
        cols_count=3,
        cells=[
            OCRTableCell(
                row=0,
                col=0,
                rowspan=1,
                colspan=1,
                bbox=(0, 0, 100, 90),
                words=[OCRWord("<성명>", (5, 10, 65, 28), 0.99)],
            ),
            OCRTableCell(
                row=0,
                col=1,
                rowspan=1,
                colspan=1,
                bbox=(100, 0, 200, 90),
                figures=[figure],
            ),
            OCRTableCell(
                row=0,
                col=2,
                rowspan=1,
                colspan=1,
                bbox=(200, 0, 300, 90),
                words=[OCRWord("긴값" * 50, (205, 10, 295, 28), 0.99)],
            ),
        ],
    )
    page = OCRPageResult(
        page_num=1,
        width=300,
        height=90,
        tables=[table],
        figures=[figure],
        text_blocks=[OCRTextBlock("검토 <필요>\n2행", (0, 100, 100, 120))],
        mean_confidence=0.42,
        requires_review=True,
        warnings=["<저신뢰 & 확인>"],
    )

    html_output = convert_ocr_result_to_html([page])

    assert "&lt;성명&gt;" in html_output
    assert "&lt;저신뢰 &amp; 확인&gt;" in html_output
    assert "&lt;필요&gt;" in html_output
    assert "검토 &lt;필요&gt;<br>2행" in html_output
    assert "ocr-cell-figure" in html_output
    assert html_output.count(figure.base64_src) == 1
    assert '<div class="ocr-figure-container">' not in html_output
    widths = [
        float(value)
        for value in re.findall(r'<col style="width:([0-9.]+)%">', html_output)
    ]
    assert len(widths) == 3
    assert abs(sum(widths) - 100.0) < 0.001


# 한글 표준(HWPX) export visual and 셀 integrity 기능의 정상 동작 및 제약조건을 테스트함
def test_hwpx_export_visual_and_cell_integrity(tmp_path) -> None:
    output = tmp_path / "ocr.hwpx"
    page = _export_page()

    convert_ocr_result_to_hwpx([page], output)
    html_output = convert_ocr_result_to_html([page])

    assert output.is_file()
    with zipfile.ZipFile(output) as package:
        assert package.testzip() is None
        section = package.read("Contents/section0.xml").decode("utf-8")
        package_xml = "".join(
            package.read(name).decode("utf-8", errors="ignore")
            for name in package.namelist() if name.endswith(".xml")
        )
    assert "통합 제목" in section
    assert 'colSpan="3"' in section
    assert "lineBreak" in section
    assert 'horizontal="CENTER"' in package_xml
    assert section.count("<hp:tc") == len(page.tables[0].cells)
    assert "DBEAFE" in package_xml.upper()
    assert 'colspan="3"' in html_output
    assert "background-color:#dbeafe" in html_output
    from hwpx.document import HwpxDocument
    reopened = HwpxDocument.open(output)
    assert len(reopened.tables) == 1


# 엑셀(XLSX) export 스팬 목록 and fills 기능의 정상 동작 및 제약조건을 테스트함
def test_xlsx_export_spans_and_fills(tmp_path) -> None:
    output = tmp_path / "ocr.xlsx"

    convert_ocr_result_to_xlsx([_export_page()], output)
    workbook = load_workbook(output)
    sheet = workbook[workbook.sheetnames[0]]

    assert "A1:C1" in {str(cell_range) for cell_range in sheet.merged_cells.ranges}
    assert sheet["A1"].value == "통합 제목"
    assert sheet["A1"].fill.fgColor.rgb.endswith("DBEAFE")
    assert sheet["A1"].alignment.horizontal == "center"


# word 바운딩 박스 overlap binds when center falls outside 셀 기능의 정상 동작 및 제약조건을 테스트함
def test_word_bbox_overlap_binds_when_center_falls_outside_cell() -> None:
    left = OCRTableCell(0, 0, 1, 1, (0, 0, 100, 60), grid_confidence=0.9)
    table = OCRTable(
        bbox=(0, 0, 130, 60), cells=[left], rows_count=1, cols_count=1
    )
    # 44% of the word lies in the cell, but its center is just outside it.
    word = OCRWord("boundary", (80, 10, 125, 35), 0.98)

    _, outside = assign_words_to_tables([word], [table], min_overlap_ratio=0.35)

    assert left.words == [word]
    assert outside == []


# complex 표(테이블) uses canonical HTML 웹 문서 in 마크다운 기능의 정상 동작 및 제약조건을 테스트함
def test_complex_table_uses_canonical_html_in_markdown() -> None:
    page = _export_page()

    markdown = convert_ocr_result_to_markdown([page])

    assert '<table class="ocr-table"' in markdown
    assert 'colspan="3"' in markdown
    assert "<colgroup>" in markdown
    assert "| 통합 제목 |" not in markdown


# opt in 셀 OCR 인식 maps 자르기 바운딩 박스 back to 페이지 기능의 정상 동작 및 제약조건을 테스트함
def test_opt_in_cell_ocr_maps_crop_bbox_back_to_page(monkeypatch) -> None:
    monkeypatch.setenv("OCR_TABLE_CELL_RECOGNITION", "true")
    monkeypatch.setattr(
        reconstructor,
        "recognize_page_words",
        lambda *_args, **_kwargs: [OCRWord("정상 텍스트", (7, 8, 67, 28), 0.99)],
    )
    cell = OCRTableCell(
        0, 0, 1, 1, (20, 30, 120, 80),
        words=[OCRWord("��", (25, 40, 55, 60), 0.2)],
        grid_confidence=0.9,
        source="ruled_v2",
    )
    table = OCRTable(
        bbox=(20, 30, 120, 80),
        cells=[cell],
        rows_count=1,
        cols_count=1,
        grid_confidence=0.9,
        source="ruled_v2",
    )

    recognize_table_cells(np.full((140, 180, 3), 255, dtype=np.uint8), table, object())

    assert cell.text == "정상 텍스트"
    assert cell.words[0].bbox == (23, 34, 83, 54)


# v2 failure keeps legacy ruled detector 폴백 기능의 정상 동작 및 제약조건을 테스트함
def test_v2_failure_keeps_legacy_ruled_detector_fallback(monkeypatch) -> None:
    image = np.full((180, 260), 255, dtype=np.uint8)
    for x in (30, 110, 190):
        cv2.line(image, (x, 25), (x, 145), 0, 2)
    for y in (25, 85, 145):
        cv2.line(image, (30, y), (190, y), 0, 2)
    monkeypatch.setattr(reconstructor, "detect_ruled_table_grids_v2", lambda *args, **kwargs: [])

    tables = detect_table_grid_cells(image, min_table_area=2_000)

    assert len(tables) == 1
    assert tables[0].source == "ruled_legacy"
    assert tables[0].rows_count >= 2
    assert tables[0].cols_count >= 2
