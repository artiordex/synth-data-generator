# -*- coding: utf-8 -*-
"""단일 YAML 프로파일 레지스트리의 로딩·검증·확장 테스트."""
from __future__ import annotations

import pytest

from synthetic_engine.rules.catalog import get_dataset_catalog, match_dataset_schema
from synthetic_engine.rules.profile_registry import (
    ProfileRegistry,
    ProfileRegistryError,
    PROFILE_PATH_ENV,
    default_engine_settings,
)


def test_builtin_registry_contains_all_profiles_and_rules():
    catalog = get_dataset_catalog()

    assert len(catalog) == 12
    assert {profile.dataset_id for profile in catalog} == {
        "vulnerable_support",
        "redevelopment_rental",
        "purchase_rental",
        "shift_rental",
        "national_rental",
        "youth_rent",
        "housing_benefit",
        "parental_leave",
        "family_helper",
        "housing_counseling",
        "rental_arrears",
        "birth_fertility",
    }
    assert sum(len(profile.rules) for profile in catalog) == 36


def test_builtin_registry_exposes_shared_engine_defaults():
    settings = default_engine_settings()

    assert settings["privacy"]["phone"]["region_prefixes"]["서울"] == "02"
    assert settings["notebook_presets"][0]["name"] == "보육교사 근무 제약"
    assert ["자산", "가액"] in settings["semantic"]["synonym_pairs"]
    assert settings["constraints"]["global"][0]["type"] == "inequality"


def test_external_profile_can_be_added_without_python_code_change(tmp_path, monkeypatch):
    profile_path = tmp_path / "profiles.yaml"
    profile_path.write_text(
        """
schema_version: 1
profiles:
  - dataset_name: 임의 데이터셋
    dataset_id: arbitrary_dataset
    aliases: [임의, arbitrary]
    numerical_columns: [amount]
    categorical_columns: [status]
    rules:
      - name: amount_non_negative
        type: min_max
        columns: [amount]
        params: {column: amount, min: 0}
""".lstrip(),
        encoding="utf-8",
    )

    monkeypatch.setenv(PROFILE_PATH_ENV, str(profile_path))
    matched = match_dataset_schema(dataset_name="임의")

    assert matched is not None
    assert matched.dataset_id == "arbitrary_dataset"
    assert matched.rules[0].rule_type.value == "min_max"
    assert matched.rules[0].params["min"] == 0


def test_registry_supports_a_standalone_profile_file(tmp_path):
    profile_path = tmp_path / "custom.json"
    profile_path.write_text(
        '{"schema_version": 1, "profiles": [{"dataset_name": "JSON 데이터셋", '
        '"dataset_id": "json_dataset", "aliases": ["json"], '
        '"rules": []}]}',
        encoding="utf-8",
    )

    registry = ProfileRegistry.from_file(profile_path)

    assert registry.list_profiles() == ["json_dataset"]
    assert registry.match(dataset_name="json") is not None


def test_registry_rejects_unknown_rule_type(tmp_path):
    profile_path = tmp_path / "invalid.yaml"
    profile_path.write_text(
        """
schema_version: 1
profiles:
  - dataset_name: 잘못된 데이터셋
    dataset_id: invalid_dataset
    rules:
      - name: unsupported
        rule_type: arbitrary_python
        columns: [value]
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ProfileRegistryError, match="invalid rule_type"):
        ProfileRegistry.from_file(profile_path)


def test_registry_rejects_python_callable_fields(tmp_path):
    profile_path = tmp_path / "callable.yaml"
    profile_path.write_text(
        """
schema_version: 1
profiles:
  - dataset_name: 호출 가능한 데이터셋
    dataset_id: callable_dataset
    rules:
      - name: unsafe
        rule_type: custom
        columns: [value]
        validator: some_python_function
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ProfileRegistryError, match="unknown fields"):
        ProfileRegistry.from_file(profile_path)
