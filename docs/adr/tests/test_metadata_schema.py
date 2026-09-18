"""통합 XML에서 만든 렌더링 표본으로 프로젝트 XSD 1.0을 검증한다.

실행: .venv/Scripts/python.exe docs/adr/tests/test_metadata_schema.py
XSD 외의 Canonical 값 대응/문서 검토 요약 계산은 이 시험의 범위가 아니다.
"""

from copy import deepcopy
from pathlib import Path
import unittest

from lxml import etree as ET


ROOT = Path(__file__).resolve().parents[3] / "apps" / "api" / "src" / "synthetic_api" / "data" / "ai_guide" / "templates"
NS = {"m": "urn:synthetic-data:ai-ready:v2:"}
NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
PARSER = ET.XMLParser(resolve_entities=False, no_network=True, remove_comments=True)


def node(root, path):
    return root.find("/".join("m:" + p for p in path.split("/")), NS)


def put(element, value):
    element.attrib.pop(NIL, None)
    element.text = value
    if value is None:
        element.set(NIL, "true")


def fixture(category="api"):
    """전체 구조를 보존하고 미확정 값을 nil로 채운 검증 전용 표본."""
    root = ET.parse(str(ROOT / "ai_ready_metadata_template.xml"), PARSER).getroot()
    for element in root.iter():
        if element.text and "{{" in element.text:
            put(element, None)
        for attr, value in list(element.attrib.items()):
            if "{{" in value:
                if attr in {"isApplicable", "required"}:
                    element.set(attr, "false")
                elif attr in {"order", "httpStatus"}:
                    element.set(attr, "1" if attr == "order" else "200")
                elif attr == "status":
                    element.set(attr, "REVIEW_REQUIRED")
                else:
                    element.set(attr, "sample")
        if ET.QName(element).localname in {"status", "contractStatus"}:
            put(element, "REVIEW_REQUIRED")
    for path, value in {
        "document/status": "REVIEW_REQUIRED",
        "document/generatedUtc": "2026-09-16T00:00:00Z",
        "document/docType": category + "_dataset",
        "document/review_status": "INCOMPLETE_REVIEW",
        "document/isDraft": "true",
        "document/reviewNotice": "임시 검토본 - 기관 공식 확인 필요",
        "structure/dataCategory": category,
        "structure/hasFileData": "true" if category in {"file", "hybrid"} else "false",
        "structure/hasApiData": "true" if category in {"api", "hybrid"} else "false",
        "structure/rootType": "object" if category == "api" else "table",
        "dataset/title": '검증용 <데이터> & "표본"',
        "dataset/byteSize": "100",
        "dataset/description": "검증용 추론 설명",
        "dataset/publisher": "검증용 승인 기관",
        "analysis/scope": "SAMPLE",
        "analysis/sampleSize": "2",
        "statistics/totalRecords": "20",
        "modalitySpecifications/imageMetadata/width": "1920",
        "modalitySpecifications/audioMetadata/sampleRate": "16000",
        "modalitySpecifications/spatialSensorMetadata/jointNames": '["joint_1", "joint_2"]',
        "modalitySpecifications/spatialSensorMetadata/trajectoryFields": '{"position": "/frames/position"}',
        "structure/apiSpecification/operations/operation/sampleMessages/xmlSample": '<item name="a&b">]]></item>',
        "structure/apiSpecification/operations/operation/sampleMessages/jsonSample": '{"value": false}',
        "quality/metrics/completeness/score": "95.5",
    }.items():
        put(node(root, path), value)
    entries = node(root, "canonicalItems")
    prototype = deepcopy(entries[0])
    entries.clear()
    samples = [
        ("observed", "/dataset/byte_size", "100", "integer", "AUTO_CONFIRMED"),
        ("inferred", "/dataset/description", "검증용 추론 설명", "string", "AUTO_INFERRED"),
        ("approved", "/dataset/publisher", "검증용 승인 기관", "string", "USER_CONFIRMED"),
        ("review", "/usage/license", None, "null", "REVIEW_REQUIRED"),
        ("na", "/modality/audio/duration", None, "null", "NOT_APPLICABLE"),
    ]
    for identifier, path, value, value_type, status in samples:
        entry = deepcopy(prototype)
        for key, val in {
            "id": identifier, "bindingPath": path, "label": "검증용 항목",
            "property": "m:value", "namespace": NS["m"], "value": value,
            "valueType": value_type, "sourceType": "UNKNOWN", "status": status,
            "confidence": None if value is None else "0.8",
            "reason": "구조 검증용 표본", "updatedAt": "2026-09-16T00:00:00Z",
            "sourceReference": "검증 fixture",
        }.items():
            put(node(entry, key), val)
        entries.append(entry)
    item = node(root, "reviewRequired/item")
    item.set("id", "review")
    for key in ("bindingPath", "sourceType", "confidence", "updatedAt", "label", "reason"):
        put(node(item, key), node(entries[3], key).text)
    if category == "file":
        node(root, "structure/apiSpecification/operations").clear()
        node(root, "structure/apiSpecification/errorCodes").clear()
        put(node(root, "structure/apiSpecification/contractStatus"), "NOT_APPLICABLE")
    return root


class MetadataSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = ET.XMLSchema(ET.parse(str(ROOT / "ai_ready_metadata_schema.xsd"), PARSER))

    def test_file_and_api_profiles_with_all_modality_blocks(self):
        for category in ("file", "api"):
            with self.subTest(category=category):
                root = fixture(category)
                self.schema.assertValid(root)
                reparsed = ET.fromstring(ET.tostring(root), PARSER)
                self.schema.assertValid(reparsed)
                self.assertEqual(node(root, "dataset/title").text, node(reparsed, "dataset/title").text)

    def test_empty_and_multiple_collections(self):
        root = fixture()
        for path in ("fields", "modalitySpecifications/annotations", "quality/traitChecks"):
            parent = node(root, path)
            parent.append(deepcopy(parent[0]))
        self.schema.assertValid(root)
        for path in ("fields", "canonicalItems", "reviewRequired", "references",
                     "modalitySpecifications/annotations", "quality/traitChecks"):
            node(root, path).clear()
        self.schema.assertValid(root)

    def test_optional_profile_blocks(self):
        for absent in ("distribution", "apiSpecification"):
            root = fixture()
            parent = node(root, "structure")
            parent.remove(node(parent, absent))
            self.schema.assertValid(root)

    def test_invalid_values_rejected(self):
        cases = [
            ("canonicalItems/entry/status", "APPROVED"),
            ("canonicalItems/entry/status", None),
            ("canonicalItems/entry/confidence", "1.01"),
            ("canonicalItems/entry/confidence", "-0.1"),
            ("canonicalItems/entry/valueType", "floatish"),
            ("canonicalItems/entry/reason", "   "),
            ("canonicalItems/entry/bindingPath", "dataset.title"),
            ("canonicalItems/entry/updatedAt", "yesterday"),
            ("document/review_status", "CONFIRMED"),
            ("document/isDraft", "yes"),
            ("structure/dataCategory", "other"),
            ("statistics/totalRecords", "-1"),
            ("quality/metrics/completeness/score", "101"),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                root = fixture()
                put(node(root, path), value)
                self.assertFalse(self.schema.validate(root))

    def test_identity_constraints_and_required_metadata(self):
        root = fixture()
        node(root, "canonicalItems").append(deepcopy(node(root, "canonicalItems/entry")))
        self.assertFalse(self.schema.validate(root))
        root = fixture()
        node(root, "reviewRequired/item").set("id", "missing-entry")
        self.assertFalse(self.schema.validate(root))
        root = fixture()
        node(root, "reviewRequired/item").set("status", "AUTO_CONFIRMED")
        self.assertFalse(self.schema.validate(root))
        root = fixture()
        entry = node(root, "canonicalItems/entry")
        entry.remove(node(entry, "confidence"))
        self.assertFalse(self.schema.validate(root))

    def test_template_is_not_a_rendered_instance(self):
        self.assertFalse(self.schema.validate(ET.parse(str(ROOT / "ai_ready_metadata_template.xml"), PARSER)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
