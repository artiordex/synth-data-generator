import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd
import pytest
from hwpx.document import HwpxDocument

from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.exporters.package_exporter import (
    make_submission_package_dirs,
    numbered_submission_filename,
    synthetic_data_filename,
)
from synthetic_engine.exporters.review_documents import build_review_context, build_review_documents
from synthetic_engine.exporters.template_binding import TEMPLATE_NAMES
from synthetic_engine.profiling.analyzer import classify_information_type


@pytest.mark.parametrize("count", [0, 3, 5, 1000])
def test_synthetic_preview_uses_generated_values_and_count(tmp_path, monkeypatch, count):
    monkeypatch.setenv("OPENAI_COLUMN_DESCRIPTION_ENABLED", "false")
    raw = pd.DataFrame({"이메일": ["original@example.invalid"] * 794})
    synthetic = pd.DataFrame({"이메일": [f"generated{i}@example.invalid" for i in range(count)]})
    files = build_review_documents(raw=raw, synthetic=synthetic,
        plan=ColumnPlan([], [], ["이메일"], {"이메일": {"action": "faker"}}, {}),
        original_filename="preview.csv", model_type="ctgan", metrics={}, output_review_dir=tmp_path)
    with ZipFile(files["synthetic_spec"]) as archive:
        root = ET.fromstring(archive.read("Contents/section0.xml"))
    text = "".join(root.itertext())
    assert f"※{count:,}행 중 {min(count, 5)}행" in text
    assert "식별값 비공개" not in text
    assert "original@example.invalid" not in text
    for i in range(min(count, 5)):
        assert f"generated{i}@example.invalid" in text
    assert "generated5@example.invalid" not in text
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    assert root.findall(".//hp:tbl", ns)[3].get("rowCnt") == str(min(count, 5) + 1)


@pytest.mark.parametrize("count,expected", [(11, [6, 5]), (12, [6, 6]), (17, [6, 6, 5])])
def test_original_example_layout_and_fixed_plan(tmp_path, monkeypatch, count, expected):
    monkeypatch.setenv("OPENAI_COLUMN_DESCRIPTION_ENABLED", "false")
    frame = pd.DataFrame({f"항목{i}": [f"첫값{i}", f"둘째값{i}"] for i in range(count)})
    files = build_review_documents(raw=frame, synthetic=pd.concat([frame] * 1250, ignore_index=True),
        plan=ColumnPlan(list(frame.columns), [], [], {}, {}),
        original_filename="layout.csv", model_type="statistical", metrics={}, output_review_dir=tmp_path)
    with ZipFile(files["original_spec"]) as archive:
        root = ET.fromstring(archive.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    tables = root.findall(".//hp:tbl", ns)
    examples = tables[3:3 + len(expected)]
    assert [int(t.get("colCnt")) for t in examples] == expected
    for table in examples:
        assert table.get("rowCnt") == "2"
        widths = [int(c.find("hp:cellSz", ns).get("width")) for c in table.findall("hp:tr", ns)[0]]
        assert max(widths) - min(widths) <= 1
    text = "".join(root.itertext())
    assert "※2행 중 1행" in text
    assert "첫값0" in text and "둘째값0" not in text
    paragraphs = root.findall("hp:p", ns)
    heading = next(p for p in paragraphs if "".join(p.itertext()) == "3) 원본데이터 예시")
    assert heading.get("pageBreak") == "0"
    index = paragraphs.index(heading)
    assert not "".join(paragraphs[index - 1].itertext()).strip()
    assert paragraphs[index - 2].find(".//hp:tbl", ns) is tables[2]
    for table in tables[4 + len(expected):]:
        rows = table.findall("hp:tr", ns)
        assert "".join(rows[0].itertext()) == "개인정보 처리계획"
        notes = []
        for row in rows[3:]:
            for cell in row:
                col = cell.find("hp:cellAddr", ns).get("colAddr")
                if col == "4":
                    assert "".join(cell.itertext()) == "그대로 사용"
                elif col == "5":
                    assert "".join(cell.itertext()) == "유지"
                elif col == "6":
                    notes.append(cell)
        assert len(notes) == 1
        assert notes[0].find("hp:cellSpan", ns).get("rowSpan") == str(len(rows) - 3)
        assert "".join(notes[0].itertext()) == "원본데이터 증강생성 (2행 → 2,500행)"
    from lxml import html
    preview = html.parse(str(files["original_spec"].with_suffix(".html")))
    privacy = preview.xpath("//table[tr[1]/td[text()='개인정보 처리계획']]")
    assert len(privacy) == 1
    body_rows = privacy[0].xpath("./tr")[3:]
    assert len(body_rows) == count
    for index in (0, 1, 6):
        assert body_rows[0].xpath("./td")[index].get("rowspan") == str(count)
    assert len(privacy[0].xpath(".//td[text()='layout']")) == 1


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
                    for element in ("equation", "pic"):
                        assert [ET.tostring(e) for e in root.findall(f".//hp:{element}", ns)] == [
                            ET.tostring(e) for e in original.findall(f".//hp:{element}", ns)]
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
        assert ("secret@example.com" in texts[key]) == (key == "original_spec")
        assert "37,298" not in texts[key]
        assert path.with_suffix(".html").exists()
    for field in ("데이터명", "데이터 유형", "데이터 규모", "특이사항", "정보 개요", "정보 상세", "원본데이터 예시", "개인정보 처리 계획", "항목26", "검토팀"):
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


@pytest.mark.parametrize("safety,utility,expected", [
    (0, 0.02, ["0.00", "0.02"]),
    (0.001, 0.9, ["<0.01", "0.90"]),
    (None, float("nan"), ["미측정", "미측정"]),
])
def test_report_contains_only_two_measured_results(tmp_path, safety, utility, expected):
    frame = pd.DataFrame({"성별": ["남", "여"]})
    files = build_review_documents(raw=frame, synthetic=frame,
        plan=ColumnPlan(["성별"], [], [], {}, {}),
        original_filename="9. 진로정보 수요_세종.csv", model_type="ctgan",
        metrics={"safety": {"single_out_rate_binned": safety},
                 "utility": {"jsd_mean": utility, "jsd_by_column": {"성별": 0.3}}},
        output_review_dir=tmp_path)
    with ZipFile(files["review_report"]) as archive:
        root = ET.fromstring(archive.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    tables = root.findall(".//hp:tbl", ns)
    rows = tables[2].findall("hp:tr", ns)
    assert len(rows) == 4
    assert ["".join(row.findall("hp:tc", ns)[2].itertext()) for row in rows[2:]] == expected
    assert "CTGAN" in "".join(rows[0].itertext())
    summary = "".join(tables[3].itertext())
    assert "데이터명: 진로정보 수요_세종" in summary
    assert "개인식별 위험성이 없는" not in summary
    assert "JSD: 성별" not in "".join(root.itertext())


def test_descriptions_are_generated_once_and_shared(tmp_path, monkeypatch):
    from synthetic_engine.exporters import review_documents
    calls = []

    def polish(**kwargs):
        calls.append(kwargs["column_name"])
        return "진로정보 수요 응답정보"

    monkeypatch.setattr(review_documents, "polish_column_description", polish)
    frame = pd.DataFrame({"성별": ["남", "여"], "문항A": ["필요함", "보통"]})
    files = build_review_documents(raw=frame, synthetic=frame,
        plan=ColumnPlan(list(frame.columns), [], [], {}, {}),
        original_filename="수요.csv", model_type="statistical", metrics={}, output_review_dir=tmp_path)
    assert calls == ["문항A"]
    descriptions = []
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    for kind in ("original_spec", "synthetic_spec"):
        with ZipFile(files[kind]) as archive:
            root = ET.fromstring(archive.read("Contents/section0.xml"))
        rows = root.findall(".//hp:tbl", ns)[2].findall("hp:tr", ns)[1:]
        descriptions.append(["".join(r.findall("hp:tc", ns)[4].itertext()) for r in rows])
        assert "항목별 실제 처리방법은 아래 표 참조" not in "".join(root.itertext())
    assert descriptions[0] == descriptions[1] == ["개인의 성별", "진로정보 수요 응답정보"]


@pytest.mark.parametrize("text", ["가" * 31, "기본 설명은 조사연도이다", "조사연도입니다"])
def test_verbose_gpt_descriptions_are_rejected(text):
    from synthetic_engine.exporters.openai_text import clean_response
    assert clean_response(text) == ""


def test_information_area_is_limited_to_quasi_identifier_or_general():
    frame = pd.DataFrame({
        "지역": ["세종", "충남"],
        "성별": ["남", "여"],
        "고등학교 유형": ["일반고", "특성화고"],
        "참여경험_진로와 직업 수업": ["예", "아니오"],
        "만족도_진로와 직업 수업": ["만족", "보통"],
        "조사연도": [2020, 2020],
        "이메일": ["a@example.com", "b@example.com"],
    })
    context = build_review_context(
        frame,
        frame.drop(columns=["이메일"]),
        ColumnPlan(
            ["지역", "성별", "고등학교 유형", "참여경험_진로와 직업 수업", "만족도_진로와 직업 수업"],
            ["조사연도"],
            ["이메일"],
            {"이메일": {"action": "drop"}},
            {},
        ),
        "설문.csv",
        "statistical",
        {},
        metadata={"columns": {"성별": {"information_type": "식별자 후보"}}},
    )
    by_name = {column["name"]: column["information_type"] for column in context["columns"]}
    descriptions = {column["name"]: column["description"] for column in context["columns"]}

    assert set(by_name.values()) <= {"준식별자", "일반정보"}
    assert by_name["지역"] == "준식별자"
    assert by_name["성별"] == "준식별자"
    assert by_name["고등학교 유형"] == "준식별자"
    assert by_name["이메일"] == "준식별자"
    assert by_name["참여경험_진로와 직업 수업"] == "일반정보"
    assert by_name["만족도_진로와 직업 수업"] == "일반정보"
    assert by_name["조사연도"] == "일반정보"
    assert descriptions["지역"] == "개인의 거주지역"
    assert descriptions["성별"] == "개인의 성별"
    assert descriptions["고등학교 유형"] == "개인의 학교유형"
    assert descriptions["참여경험_진로와 직업 수업"] == "진로와 직업 수업 참여경험 응답정보"
    assert descriptions["만족도_진로와 직업 수업"] == "진로와 직업 수업 만족도 응답정보"
    assert descriptions["조사연도"] == "조사연도 정보"
    assert context["information_area_summaries"]["준식별자"] == "고등학생 응답자의 개인 특성정보"
    assert context["information_area_summaries"]["일반정보"] == "진로수업 경험 및 진로인식 정보"
    assert "정보영역 및 항목 설명은 자동 분류 결과 기준" in context["special_notes"]


def test_information_area_uses_values_when_column_name_is_ambiguous():
    assert classify_information_type("항목A", pd.Series(["세종", "충남", "전남광주", "세종"])) == "준식별자"
    assert classify_information_type("항목B", pd.Series(["남", "여", "남성", "여성"])) == "준식별자"
    assert classify_information_type("항목C", pd.Series(["10대", "20대", "30대", "40대"])) == "준식별자"
    assert classify_information_type("항목D", pd.Series(["일반고", "특성화고", "자율고"])) == "준식별자"
    assert classify_information_type("항목E", pd.Series(["고졸", "대졸", "석사"])) == "준식별자"
    assert classify_information_type("항목F", pd.Series(["1분위", "2분위", "3분위"])) == "준식별자"
    assert classify_information_type("항목G", pd.Series(["관리자", "사무 종사자", "학생"])) == "준식별자"
    assert classify_information_type("문항1", pd.Series([1, 2, 1, 2])) == "일반정보"


def test_openai_polishing_is_optional_and_cached(monkeypatch, tmp_path):
    from synthetic_engine.exporters import openai_text

    cache = tmp_path / "cache.json"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_COLUMN_DESCRIPTION_ENABLED", "true")
    monkeypatch.setenv("OPENAI_COLUMN_DESCRIPTION_MODEL", "gpt-5-nano")
    monkeypatch.setenv("OPENAI_COLUMN_DESCRIPTION_CACHE_PATH", str(cache))
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"output_text": "진로수업 만족도 응답정보"}).encode("utf-8")

    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        return Response()

    monkeypatch.setattr(openai_text.urlrequest, "urlopen", fake_urlopen)

    kwargs = {
        "column_name": "만족도_진로와 직업 수업",
        "information_type": "일반정보",
        "base_description": "진로와 직업 수업 만족도 응답정보",
        "sample_values": ["만족", "보통"],
    }

    assert openai_text.polish_column_description(**kwargs) == "진로수업 만족도 응답정보"
    assert openai_text.polish_column_description(**kwargs) == "진로수업 만족도 응답정보"
    assert len(calls) == 1
    assert json.loads(calls[0][0].data)["reasoning"] == {"effort": "minimal"}


def test_numbered_original_file_uses_review_folder_naming(tmp_path):
    frame = pd.DataFrame({"성별": ["남", "여"], "연령대": ["10대", "20대"]})
    plan = ColumnPlan(["성별", "연령대"], [], [], {}, {})
    outputs = build_review_documents(
        raw=frame,
        synthetic=frame,
        plan=plan,
        original_filename="1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx",
        model_type="statistical",
        metrics={},
        output_review_dir=tmp_path,
    )

    assert outputs["original_spec"].name == "1. 원본데이터 명세서(고등학생 진로수업 경험과 진로정보 인식_세종).hwpx"
    assert outputs["synthetic_spec"].name == "1. 합성데이터 명세서(고등학생 진로수업 경험과 진로정보 인식_세종).hwpx"
    assert outputs["review_report"].name == "1. 합성데이터 안전성 및 유용성 측정결과서(고등학생 진로수업 경험과 진로정보 인식_세종).hwpx"

    data = json.loads((tmp_path / "심의자료_입력내용.json").read_text(encoding="utf-8"))
    assert data["dataset_name"] == "고등학생 진로수업 경험과 진로정보 인식_세종"
    assert data["document_sequence"] == "1."


def test_submission_package_uses_docs_folder_and_filename_conventions(tmp_path):
    original_filename = "1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx"
    dirs = make_submission_package_dirs(tmp_path, "job-test", original_filename)

    assert dirs["root"].name == "job-test_고등학생 진로수업 경험과 진로정보 인식_세종"
    assert dirs["original"].name == "원본데이터_세종"
    assert dirs["synthetic"].name == "합성데이터_세종"
    assert dirs["review"].name == "심의자료_세종"
    assert synthetic_data_filename("고등학생 진로수업 경험과 진로정보 인식_세종", "1.", ".xlsx") == "1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx"
    assert numbered_submission_filename("1. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx", 1) == "01. 고등학생 진로수업 경험과 진로정보 인식_세종.xlsx"


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
