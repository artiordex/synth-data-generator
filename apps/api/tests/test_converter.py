from hwpx.document import HwpxDocument

from synthetic_api.routes.v1 import converter


def test_pure_hwp_to_hwpx_writes_valid_package(tmp_path, monkeypatch):
    source = tmp_path / "source.hwp"
    source.write_bytes(b"placeholder")
    target = tmp_path / "target.hwpx"
    monkeypatch.setattr(converter, "_extract_hwp_paragraphs_pure", lambda _: ["첫 문단", "둘째 문단"])

    converter._convert_hwp_to_hwpx_pure(source, target)

    doc = HwpxDocument.open(target)
    assert doc.validate().ok
    text = doc.export_text()
    assert "첫 문단" in text
    assert "둘째 문단" in text


def test_hwpx_validation_rejects_broken_zip(tmp_path):
    target = tmp_path / "broken.hwpx"
    target.write_text("not a zip", encoding="utf-8")

    import pytest

    with pytest.raises(RuntimeError, match="ZIP 패키지"):
        converter._validate_hwpx_output(target)
