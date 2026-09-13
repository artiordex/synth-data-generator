# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_conversion_rules.py
# 경로: apps/api/tests/test_conversion_rules.py
# 목적: 문서 및 데이터셋 포맷 변환 규칙 엔진의 유효성을 검증함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import pytest

from synthetic_api.application.services.conversion_rules import (
    ConversionRuleError,
    catalog,
    normalize_source,
    normalize_target,
    resolve_rule,
)


# aliases are normalized before 변환 규칙 lookup 기능의 정상 동작 및 제약조건을 테스트함
def test_aliases_are_normalized_before_rule_lookup():
    assert normalize_source("report.PQ") == ".parquet"
    assert normalize_target(".MARKDOWN") == "md"
    assert normalize_target("word") == "docx"
    assert resolve_rule("report.csv", ".HTML").preview_mode == "html"


# 규칙 목록 distinguish document and 데이터셋 previews 기능의 정상 동작 및 제약조건을 테스트함
def test_rules_distinguish_document_and_dataset_previews():
    assert resolve_rule("report.pdf", "md").source_kind == "document"
    assert resolve_rule("rows.csv", "sql").source_kind == "dataset"
    assert resolve_rule("rows.csv", "csv").preview_mode == "table"
    assert resolve_rule("report.pdf", "docx").preview_mode == "none"


# unsupported pairs are rejected before upload work 기능의 정상 동작 및 제약조건을 테스트함
def test_unsupported_pairs_are_rejected_before_upload_work():
    with pytest.raises(ConversionRuleError, match="지원하지 않는 입력"):
        resolve_rule("report.exe", "md")
    with pytest.raises(ConversionRuleError, match="지원하지 않습니다"):
        resolve_rule("rows.csv", "hwp")
    with pytest.raises(ConversionRuleError, match="변환 대상"):
        resolve_rule("rows.csv", "")


# catalog has no alias duplicate and exposes contract 기능의 정상 동작 및 제약조건을 테스트함
def test_catalog_has_no_alias_duplicate_and_exposes_contract():
    rules = catalog()
    assert ".pq" not in rules
    parquet_rules = {item["target"]: item for item in rules[".parquet"]}
    assert parquet_rules["md"]["preview_mode"] == "markdown"
    assert parquet_rules["sql"]["output_extension"] == ".sql"
    assert parquet_rules["csv"]["preview_mode"] == "table"


# xml is available as 데이터셋 source and target 기능의 정상 동작 및 제약조건을 테스트함
def test_xml_is_available_as_dataset_source_and_target():
    rules = catalog()
    xml_targets = {item["target"] for item in rules[".xml"]}
    assert {"csv", "xlsx", "json", "xml"}.issubset(xml_targets)
    assert resolve_rule("records.xml", "csv").source_kind == "dataset"
    assert resolve_rule("records.csv", "xml").preview_mode == "table"


# 이미지 목록 are available as document 텍스트 sources 기능의 정상 동작 및 제약조건을 테스트함
def test_images_are_available_as_document_text_sources():
    rules = catalog()
    png_targets = {item["target"] for item in rules[".png"]}
    assert {"md", "txt", "html"}.issubset(png_targets)
    assert resolve_rule("scan.JPG", "md").source_kind == "document"
    assert resolve_rule("scan.tiff", "html").preview_mode == "html"
