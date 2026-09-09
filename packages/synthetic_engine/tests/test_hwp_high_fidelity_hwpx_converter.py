import base64
import re
import zipfile

from hwpx.document import HwpxDocument

from synthetic_engine.exporters.hwp_high_fidelity_hwpx_converter import (
    _build_hwpx_from_html,
    convert_any_hwp_to_hwpx,
)


def _section_xml(path):
    with zipfile.ZipFile(path) as zf:
        section_name = next(
            name for name in zf.namelist()
            if "section" in name.lower() and name.endswith(".xml")
        )
        return zf.read(section_name).decode("utf-8")


def test_html_table_grid_preserves_rowspan_shift_and_colspan(tmp_path):
    output = tmp_path / "table.hwpx"
    html = """
    <html><body>
      <table>
        <tr><th rowspan="2">Group</th><th>Name</th><th>Value</th></tr>
        <tr><td colspan="2">Merged child row</td></tr>
      </table>
    </body></html>
    """

    _build_hwpx_from_html(html, output)

    doc = HwpxDocument.open(output)
    assert doc.validate().ok
    xml = _section_xml(output)
    assert 'rowCnt="2"' in xml
    assert 'colCnt="3"' in xml
    assert re.search(r'colSpan="1"\s+rowSpan="2"', xml)
    assert re.search(r'colSpan="2"\s+rowSpan="1"', xml)
    assert "Merged child row" in doc.text.plain()


def test_html_images_are_embedded_for_paragraphs_and_table_cells(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    image_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    (media / "pixel.png").write_bytes(image_bytes)
    output = tmp_path / "images.hwpx"
    html = """
    <html><body>
      <p>Before <img src="pixel.png" width="12mm" height="10mm" alt="pixel"> After</p>
      <table><tr><td><p>Cell <img src="pixel.png" width="8mm" height="8mm"></p></td></tr></table>
    </body></html>
    """

    _build_hwpx_from_html(html, output, media_dir=media)

    with zipfile.ZipFile(output) as zf:
        media_entries = [
            name for name in zf.namelist()
            if name.startswith("BinData/") and name.lower().endswith(".png")
        ]
    xml = _section_xml(output)
    assert len(media_entries) == 2
    assert xml.count("<hp:pic") == 2


def test_hwpx_input_copy_preserves_package_bytes(tmp_path):
    source = tmp_path / "source.hwpx"
    target = tmp_path / "copy.hwpx"
    doc = HwpxDocument.new()
    doc.add_paragraph("original package")
    doc.save_to_path(source)

    convert_any_hwp_to_hwpx(source, target)

    assert target.read_bytes() == source.read_bytes()
