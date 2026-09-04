import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd
from hwpx import HwpxDocument

from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.exporters.review_documents import build_review_context, build_review_documents
from synthetic_engine.exporters.template_binding import TEMPLATE_NAMES


def test_full_variable_forms(tmp_path):
    raw = pd.DataFrame({"email": ["secret@example.com", None], **{f"항목{i}": [i, i + 1] for i in range(27)}})
    syn = raw.drop(columns="email").head(1).copy()
    plan = ColumnPlan([], list(syn.columns), ["email"], {"email": {"action": "drop"}}, {})
    outputs = build_review_documents(raw=raw, synthetic=syn, plan=plan,
        original_filename="입력.csv", model_type="statistical", metrics={},
        output_review_dir=tmp_path, department_name="검토팀", project_purpose="통계 분석",
        metadata={"dataset_name": "새 데이터 & 검토", "privacy_plan": "보유 30일 후 파기"})
    assert len(outputs) == 3
    texts = {}
    for key, path in outputs.items():
        assert path.suffix == ".hwpx"
        doc = HwpxDocument.open(path)
        assert doc.validate().ok
        with ZipFile(path) as z:
            root = ET.fromstring(z.read("Contents/section0.xml"))
            texts[key] = " ".join(root.itertext())
            source_path = Path(__file__).resolve().parents[3] / "storage/templates" / TEMPLATE_NAMES[key]
            with ZipFile(source_path) as source:
                # These hold every font, paragraph style, border, margin and asset.
                for part in source.namelist():
                    if part not in {"Contents/section0.xml", "Preview/PrvText.txt", "Preview/PrvImage.png"}:
                        assert z.read(part) == source.read(part)
                ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
                original = ET.fromstring(source.read("Contents/section0.xml"))
                assert ET.tostring(root.find(".//hp:secPr", ns)) == ET.tostring(original.find(".//hp:secPr", ns))
                if key == "review_report":
                    assert ET.tostring(root.findall(".//hp:tbl", ns)[1]) == ET.tostring(original.findall(".//hp:tbl", ns)[1])
                else:
                    original_header = original.findall(".//hp:tbl", ns)[2].find("hp:tr", ns)
                    assert ET.tostring(root.findall(".//hp:tbl", ns)[2].find("hp:tr", ns)) == ET.tostring(original_header)
                if key == "original_spec":
                    tables = root.findall(".//hp:tbl", ns)
                    assert len(tables) == 12  # four example and four privacy tables
                    for privacy, count in zip(tables[-4:], [8, 8, 8, 4]):
                        assert privacy.get("rowCnt") == str(count + 3)
                        anchors = privacy.findall("hp:tr", ns)[3].findall("hp:tc", ns)[:2]
                        assert all(cell.find("hp:cellSpan", ns).get("rowSpan") == str(count) for cell in anchors)
                    details = tables[2]
                    assert details.find("hp:pos", ns).get("treatAsChar") == "0"
                    assert details.get("pageBreak") == "TABLE"
        assert "secret@example.com" not in texts[key]
        assert "37,298" not in texts[key]
        assert path.with_suffix(".html").exists()
    for field in ("데이터명", "데이터 유형", "데이터 규모", "특이사항", "정보 개요", "정보 상세", "원본데이터 예시", "개인정보 처리 계획", "항목26", "보유 30일 후 파기", "검토팀"):
        assert field in texts["original_spec"]
    assert "1건" in texts["synthetic_spec"] and "27개 항목" in texts["synthetic_spec"]
    assert "미측정" in texts["review_report"]
    assert "보완 후 검토" in texts["review_report"]
    data = json.loads((tmp_path / "심의자료_입력내용.json").read_text(encoding="utf-8"))
    assert len(data["columns"]) == 28


def test_failed_metric_is_not_zero_and_no_automatic_approval():
    frame = pd.DataFrame({"value": [1]})
    plan = ColumnPlan([], ["value"], [], {}, {})
    metrics = {"safety": {"single_out_rate_binned": 0.0, "anonymeter": {
        "evaluated_with_anonymeter": True, "singling_out_risk": 0,
        "singling_out": {"status": "ERROR"},
    }}, "utility": {"jsd_mean": float("nan")}, "assessment": {"score": 100}}
    c = build_review_context(frame, frame, plan, "data.csv", "statistical", metrics)
    assert c["measurements"][0][2] == "0.0000"
    assert c["measurements"][1][2] == "미측정"
    assert c["measurements"][2][2] == "미측정"
    assert "100" not in c["assessment"]


def test_empty_data_has_no_old_samples(tmp_path):
    frame = pd.DataFrame(columns=["빈 항목"])
    files = build_review_documents(raw=frame, synthetic=frame, plan=ColumnPlan([], [], [], {}, {}),
        original_filename="empty.csv", model_type="statistical", metrics={}, output_review_dir=tmp_path)
    assert len(files) == 3


def test_missing_template_fails_instead_of_rebuilding(tmp_path):
    import pytest
    frame = pd.DataFrame({"값": [1]})
    with pytest.raises(FileNotFoundError, match="템플릿"):
        build_review_documents(raw=frame, synthetic=frame, plan=ColumnPlan([], ["값"], [], {}, {}),
            original_filename="data.csv", model_type="statistical", metrics={},
            template_dir=tmp_path / "missing", output_review_dir=tmp_path / "output")
