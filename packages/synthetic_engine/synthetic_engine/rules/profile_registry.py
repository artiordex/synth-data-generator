# -*- coding: utf-8 -*-
"""외부 선언형 프로파일 레지스트리.

데이터셋 이름·컬럼명·업무규칙은 엔진의 분기문이 아니라 프로파일 설정이다.
이 모듈은 YAML/JSON 프로파일을 검증하고 ``DatasetSchemaConfig`` 객체로
변환하며, 데이터셋 힌트와 컬럼 구성을 이용한 프로파일 매칭을 제공한다.

프로파일 파일에는 Python callable(validator/repairer)을 저장하지 않는다.
규칙은 ``RuleType``과 파라미터로만 표현하고, 실행은 ``operators.py``의
allow-list 연산자가 담당한다.
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from .base import ActionType, DatasetRule, DatasetSchemaConfig, RuleType


DEFAULT_PROFILE_PATH = Path(__file__).with_name("profiles.yaml")
PROFILE_PATH_ENV = "SYNTHETIC_ENGINE_PROFILE_PATH"
SUPPORTED_PROFILE_SUFFIXES = {".json", ".yaml", ".yml"}

_PROFILE_FIELDS = {
    "dataset_name",
    "dataset_id",
    "aliases",
    "quasi_identifiers",
    "sensitive_columns",
    "numerical_columns",
    "categorical_columns",
    "date_columns",
    "rules",
    "identifiers",
    "derived_columns",
    "rare_category_threshold",
    "rare_category_label",
    "extreme_value_quantile",
    "notes",
    "public_bounds",
    "domain_constraints",
}
_RULE_FIELDS = {"name", "rule_type", "type", "columns", "action", "params", "description"}
_SCHEMA_VERSION = 1


class ProfileRegistryError(ValueError):
    """프로파일 파일의 구조·값이 잘못되었을 때 발생하는 오류."""


def _context(path: Path, index: int | None = None) -> str:
    suffix = f" profile[{index}]" if index is not None else ""
    return f"{path}{suffix}"


def _as_mapping(value: Any, *, field: str, source: Path) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProfileRegistryError(f"{source}: {field} must be a mapping")
    return value


def _as_string_list(value: Any, *, field: str, source: Path, allow_scalar: bool = True) -> list[str]:
    if value is None:
        return []
    if allow_scalar and isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ProfileRegistryError(f"{source}: {field} must be a list of strings")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ProfileRegistryError(f"{source}: {field} contains an empty/non-string value")
        result.append(item)
    if len(set(result)) != len(result):
        raise ProfileRegistryError(f"{source}: {field} contains duplicate values")
    return result


def _enum_value(enum_type: type[RuleType] | type[ActionType], value: Any, *, field: str, source: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ProfileRegistryError(f"{source}: invalid {field}={value!r}; expected one of {allowed}") from exc


def _load_document(path: Path) -> Mapping[str, Any]:
    if path.suffix.lower() not in SUPPORTED_PROFILE_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_PROFILE_SUFFIXES))
        raise ProfileRegistryError(f"{path}: unsupported profile extension; expected {supported}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileRegistryError(f"cannot read profile file {path}: {exc}") from exc

    try:
        if path.suffix.lower() == ".json":
            document = json.loads(text)
        else:
            try:
                import yaml
            except ImportError as exc:  # pragma: no cover - packaging/environment guard
                raise ProfileRegistryError(
                    "YAML profiles require the PyYAML package; install the engine dependencies first"
                ) from exc
            document = yaml.safe_load(text)
    except ProfileRegistryError:
        raise
    except Exception as exc:
        raise ProfileRegistryError(f"{path}: failed to parse profile document: {exc}") from exc

    return _as_mapping(document or {}, field="document", source=path)


def _profile_items(document: Mapping[str, Any], *, source: Path) -> list[dict[str, Any]]:
    version = document.get("schema_version", _SCHEMA_VERSION)
    if version != _SCHEMA_VERSION:
        raise ProfileRegistryError(
            f"{source}: unsupported schema_version={version!r}; supported version is {_SCHEMA_VERSION}"
        )

    raw_profiles = document.get("profiles")
    if isinstance(raw_profiles, Mapping):
        # A mapping keyed by dataset_id is accepted in addition to the canonical
        # list form. This makes small hand-written registries less repetitive.
        items: list[dict[str, Any]] = []
        for dataset_id, raw_profile in raw_profiles.items():
            profile = dict(_as_mapping(raw_profile, field=f"profiles.{dataset_id}", source=source))
            profile.setdefault("dataset_id", dataset_id)
            items.append(profile)
        return items
    if not isinstance(raw_profiles, list):
        raise ProfileRegistryError(f"{source}: profiles must be a list or mapping")
    return [dict(_as_mapping(item, field="profiles[]", source=source)) for item in raw_profiles]


def _settings_from_document(document: Mapping[str, Any], *, source: Path) -> dict[str, Any]:
    settings = document.get("defaults", {}) or {}
    if not isinstance(settings, Mapping):
        raise ProfileRegistryError(f"{source}: defaults must be a mapping")
    return deepcopy(dict(settings))


def _merge_settings(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """중첩된 기본 설정을 외부 설정으로 안전하게 덮어쓴다."""
    merged = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _merge_settings(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _build_rule(raw_rule: Mapping[str, Any], *, source: Path, profile_id: str, index: int) -> DatasetRule:
    location = f"{source}: profile={profile_id!r} rule[{index}]"
    unknown = set(raw_rule) - _RULE_FIELDS
    if unknown:
        raise ProfileRegistryError(f"{location}: unknown fields: {sorted(unknown)}")

    name = raw_rule.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ProfileRegistryError(f"{location}: name must be a non-empty string")

    rule_type_raw = raw_rule.get("rule_type", raw_rule.get("type"))
    if rule_type_raw is None:
        raise ProfileRegistryError(f"{location}: rule_type is required")
    rule_type = _enum_value(RuleType, rule_type_raw, field="rule_type", source=location)

    columns = _as_string_list(raw_rule.get("columns", []), field="columns", source=location)
    params = raw_rule.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, Mapping):
        raise ProfileRegistryError(f"{location}: params must be a mapping")

    action = _enum_value(
        ActionType,
        raw_rule.get("action", ActionType.REPAIR_CONDITIONAL.value),
        field="action",
        source=location,
    )
    description = raw_rule.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ProfileRegistryError(f"{location}: description must be a string")

    return DatasetRule(
        name=name,
        rule_type=rule_type,
        columns=columns,
        action=action,
        params=dict(params),
        description=description,
    )


def profile_from_dict(
    raw_profile: Mapping[str, Any],
    *,
    source: Path,
    index: int = 0,
    defaults: Mapping[str, Any] | None = None,
) -> DatasetSchemaConfig:
    """한 개의 선언형 프로파일을 검증하고 런타임 스키마로 변환한다."""
    location = _context(source, index)
    unknown = set(raw_profile) - _PROFILE_FIELDS
    if unknown:
        raise ProfileRegistryError(f"{location}: unknown fields: {sorted(unknown)}")

    dataset_name = raw_profile.get("dataset_name")
    dataset_id = raw_profile.get("dataset_id")
    if not isinstance(dataset_name, str) or not dataset_name.strip():
        raise ProfileRegistryError(f"{location}: dataset_name must be a non-empty string")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ProfileRegistryError(f"{location}: dataset_id must be a non-empty string")

    list_fields = (
        "aliases",
        "quasi_identifiers",
        "sensitive_columns",
        "numerical_columns",
        "categorical_columns",
        "date_columns",
        "identifiers",
        "derived_columns",
    )
    lists = {
        field: _as_string_list(raw_profile.get(field, []), field=field, source=location)
        for field in list_fields
    }

    raw_rules = raw_profile.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ProfileRegistryError(f"{location}: rules must be a list")
    rules = [
        _build_rule(_as_mapping(rule, field="rules[]", source=location), source=source, profile_id=dataset_id, index=rule_index)
        for rule_index, rule in enumerate(raw_rules)
    ]
    rule_names = [rule.name for rule in rules]
    if len(set(rule_names)) != len(rule_names):
        raise ProfileRegistryError(f"{location}: rules contain duplicate names")

    label_defaults = (defaults or {}).get("labels", {}) or {}
    rare_threshold = raw_profile.get(
        "rare_category_threshold",
        label_defaults.get("rare_category_threshold", 0.01),
    )
    extreme_quantile = raw_profile.get("extreme_value_quantile", 0.999)
    for field, value in (("rare_category_threshold", rare_threshold), ("extreme_value_quantile", extreme_quantile)):
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise ProfileRegistryError(f"{location}: {field} must be a number between 0 and 1")

    rare_label = raw_profile.get(
        "rare_category_label",
        label_defaults.get("rare_category", "기타"),
    )
    notes = raw_profile.get("notes", "")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ProfileRegistryError(f"{location}: notes must be a string")

    public_bounds = raw_profile.get("public_bounds", {}) or {}
    domain_constraints = raw_profile.get("domain_constraints", {}) or {}
    if not isinstance(public_bounds, Mapping) or not isinstance(domain_constraints, Mapping):
        raise ProfileRegistryError(f"{location}: public_bounds and domain_constraints must be mappings")
    if any(not isinstance(value, Mapping) for value in domain_constraints.values()):
        raise ProfileRegistryError(f"{location}: domain_constraints values must be mappings")

    return DatasetSchemaConfig(
        dataset_name=dataset_name,
        dataset_id=dataset_id,
        aliases=lists["aliases"],
        quasi_identifiers=lists["quasi_identifiers"],
        sensitive_columns=lists["sensitive_columns"],
        numerical_columns=lists["numerical_columns"],
        categorical_columns=lists["categorical_columns"],
        date_columns=lists["date_columns"],
        rules=rules,
        identifiers=lists["identifiers"],
        derived_columns=lists["derived_columns"],
        rare_category_threshold=float(rare_threshold),
        rare_category_label=rare_label,
        extreme_value_quantile=float(extreme_quantile),
        notes=notes,
        public_bounds=dict(public_bounds),
        domain_constraints={str(key): dict(value) for key, value in domain_constraints.items()},
    )


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"[\s_()\[\]\-_/]", "", str(value)).lower()


class ProfileRegistry:
    """검증된 데이터셋 프로파일의 순서 보존 레지스트리."""

    def __init__(
        self,
        profiles: Iterable[DatasetSchemaConfig] = (),
        settings: Mapping[str, Any] | None = None,
    ):
        self._profiles: list[DatasetSchemaConfig] = []
        self._by_id: dict[str, DatasetSchemaConfig] = {}
        self._settings: dict[str, Any] = deepcopy(dict(settings or {}))
        self.add(profiles)

    @property
    def profiles(self) -> list[DatasetSchemaConfig]:
        return list(self._profiles)

    def list_profiles(self) -> list[str]:
        return [profile.dataset_id for profile in self._profiles]

    @property
    def settings(self) -> dict[str, Any]:
        """프로파일 파일의 공통 기본 설정 사본."""
        return deepcopy(self._settings)

    def merge_settings(self, settings: Mapping[str, Any] | None) -> "ProfileRegistry":
        if settings:
            self._settings = _merge_settings(self._settings, settings)
        return self

    def add(
        self,
        profiles: Iterable[DatasetSchemaConfig],
        *,
        allow_overrides: bool = False,
    ) -> "ProfileRegistry":
        for profile in profiles:
            if not isinstance(profile, DatasetSchemaConfig):
                raise TypeError("ProfileRegistry accepts DatasetSchemaConfig objects")
            existing = self._by_id.get(profile.dataset_id)
            if existing is not None and not allow_overrides:
                raise ProfileRegistryError(f"duplicate dataset_id: {profile.dataset_id}")
            if existing is not None:
                self._profiles[self._profiles.index(existing)] = profile
            else:
                self._profiles.append(profile)
            self._by_id[profile.dataset_id] = profile
        return self

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> "ProfileRegistry":
        profile_path = Path(path).expanduser().resolve()
        document = _load_document(profile_path)
        settings = _settings_from_document(document, source=profile_path)
        profiles = [
            profile_from_dict(raw, source=profile_path, index=index, defaults=settings)
            for index, raw in enumerate(_profile_items(document, source=profile_path))
        ]
        return cls(profiles, settings=settings)

    @classmethod
    def from_directory(cls, path: str | os.PathLike[str]) -> "ProfileRegistry":
        directory = Path(path).expanduser().resolve()
        if not directory.is_dir():
            raise ProfileRegistryError(f"profile directory does not exist: {directory}")
        registry = cls()
        files = sorted(
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_PROFILE_SUFFIXES
        )
        for file_path in files:
            file_registry = cls.from_file(file_path)
            registry.merge_settings(file_registry.settings)
            registry.add(file_registry.profiles)
        return registry

    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> "ProfileRegistry":
        profile_path = Path(path).expanduser()
        if profile_path.is_dir():
            return cls.from_directory(profile_path)
        return cls.from_file(profile_path)

    @classmethod
    def default(cls, external_path: str | os.PathLike[str] | None = None) -> "ProfileRegistry":
        """내장 레지스트리와 선택적인 외부 프로파일을 합친다.

        외부 경로는 ``SYNTHETIC_ENGINE_PROFILE_PATH``로 지정할 수 있다.
        외부 프로파일의 동일 ``dataset_id``는 의도적인 프로파일 교체를
        지원하기 위해 내장 프로파일을 덮어쓴다.
        """
        registry = cls.from_file(DEFAULT_PROFILE_PATH)
        configured_path = external_path or os.getenv(PROFILE_PATH_ENV)
        if configured_path:
            external_registry = cls.from_path(configured_path)
            registry.merge_settings(external_registry.settings)
            registry.add(external_registry.profiles, allow_overrides=True)
        return registry

    def match(
        self,
        df: Any = None,
        dataset_hint: str = "",
        *,
        cols: list[str] | None = None,
        dataset_name: str = "",
    ) -> DatasetSchemaConfig | None:
        """힌트 우선, 컬럼 스코어 차선으로 가장 적합한 프로파일을 반환한다."""
        hint = dataset_hint or dataset_name
        if isinstance(df, str) and not hint:
            hint = df
            df = None

        if hint:
            hint_clean = _normalize_identifier(hint)
            hint_matches: list[tuple[int, int, DatasetSchemaConfig]] = []
            for profile_index, profile in enumerate(self._profiles):
                names = [profile.dataset_name, profile.dataset_id, *profile.aliases]
                for alias in names:
                    alias_clean = _normalize_identifier(alias)
                    if not alias_clean:
                        continue
                    if hint_clean == alias_clean:
                        score = 3_000_000 + len(alias_clean)
                    elif alias_clean in hint_clean:
                        score = 2_000_000 + len(alias_clean)
                    elif hint_clean in alias_clean:
                        score = 1_000_000 + len(hint_clean)
                    else:
                        continue
                    hint_matches.append((score, -profile_index, profile))
            if hint_matches:
                return max(hint_matches, key=lambda item: (item[0], item[1]))[2]

        target_cols = (
            cols
            if cols is not None
            else list(df.columns)
            if hasattr(df, "columns")
            else list(df)
            if df is not None and not isinstance(df, (str, bytes, bytearray))
            else []
        )
        if not target_cols:
            return None

        # Imported lazily to keep ``catalog.resolve_column_name`` as a stable
        # public API without introducing a catalog/registry import cycle.
        from .catalog import resolve_column_name

        best_profile: DatasetSchemaConfig | None = None
        best_score = 0
        for profile in self._profiles:
            all_targets = (
                profile.quasi_identifiers
                + profile.sensitive_columns
                + profile.numerical_columns
                + profile.categorical_columns
                + profile.date_columns
            )
            matched_count = sum(
                1 for target in set(all_targets) if resolve_column_name(target_cols, [target]) is not None
            )
            if matched_count >= 2 and matched_count > best_score:
                best_score = matched_count
                best_profile = profile
        return best_profile


def default_profile_registry(
    external_path: str | os.PathLike[str] | None = None,
) -> ProfileRegistry:
    """기본 내장 프로파일 레지스트리를 생성한다."""
    configured_path = external_path or os.getenv(PROFILE_PATH_ENV)
    normalized_path = None
    if configured_path:
        normalized_path = str(Path(configured_path).expanduser().resolve())
    return _cached_default_profile_registry(normalized_path)


@lru_cache(maxsize=16)
def _cached_default_profile_registry(external_path: str | None) -> ProfileRegistry:
    """반복되는 엔진 호출에서 YAML을 매번 파싱하지 않도록 캐시한다."""
    return ProfileRegistry.default(external_path=external_path)


def default_engine_settings(
    external_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """프로파일과 함께 로드되는 공통 엔진 설정을 반환한다."""
    return default_profile_registry(external_path=external_path).settings


__all__ = [
    "DEFAULT_PROFILE_PATH",
    "PROFILE_PATH_ENV",
    "ProfileRegistry",
    "ProfileRegistryError",
    "default_profile_registry",
    "default_engine_settings",
    "profile_from_dict",
]
