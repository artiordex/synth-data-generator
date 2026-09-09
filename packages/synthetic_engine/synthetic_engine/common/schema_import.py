"""
파일명: schema_import.py
경로: packages/synthetic_engine/synthetic_engine/common/schema_import.py
목적: DDL·JSON Schema·OpenAPI 스키마를 더미데이터 입력 구조로 변환함
작성자: 개발팀
작성일: 2026-09-09
수정일: 2026-09-09
"""
from __future__ import annotations

import json
import re
from typing import Any


def _rule_for(name: str, data_type: str, spec: dict[str, Any]) -> dict[str, Any] | None:
    """컬럼 이름과 스키마 제약조건에 맞는 생성 규칙을 추론함"""
    if spec.get("enum"):
        return {"type": "choice", "values": spec["enum"]}
    if data_type in {"integer", "number"}:
        return {"type": "number_range", "min": spec.get("minimum", 0),
                "max": spec.get("maximum", 1000), "integer": data_type == "integer"}
    if spec.get("format") in {"date", "date-time"}:
        return {"type": "date_between", "start": "2020-01-01", "end": "2026-12-31"}
    if spec.get("pattern"):
        # The UI rule engine uses # for digits and ? for uppercase letters.
        return {"type": "pattern", "format": "????????"}
    if name.lower().endswith("_id") or name.lower() == "id":
        return {"type": "sequence", "start": 1, "prefix": "ID-"}
    return None


def _json_table(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    """JSON Schema 객체를 테이블과 컬럼 정의로 변환함"""
    required = set(schema.get("required", []))
    columns = []
    for column_name, spec in schema.get("properties", {}).items():
        data_type = spec.get("type", "string")
        if isinstance(data_type, list):
            data_type = next((x for x in data_type if x != "null"), "string")
        columns.append({
            "name": column_name,
            "data_type": data_type,
            "nullable": column_name not in required,
            "primary_key": column_name.lower() in {"id", f"{name.lower()}_id"},
            "unique": bool(spec.get("unique", False)),
            "rule": _rule_for(column_name, data_type, spec),
            "constraints": {k: spec[k] for k in ("minimum", "maximum", "minLength", "maxLength", "pattern", "enum") if k in spec},
        })
    return {"name": name, "columns": columns}


def import_schema(source_type: str, content: str) -> dict[str, Any]:
    """DDL·JSON Schema·OpenAPI 문서를 공통 스키마로 가져옴"""
    kind = source_type.lower().replace("_", "-")
    if kind in {"json-schema", "json", "openapi"}:
        document = json.loads(content)
        if kind == "openapi" or "openapi" in document or "swagger" in document:
            schemas = document.get("components", {}).get("schemas", {})
            if not schemas and "definitions" in document:
                schemas = document["definitions"]
            tables = [_json_table(name, schema) for name, schema in schemas.items()
                      if isinstance(schema, dict) and schema.get("type", "object") == "object"]
        else:
            tables = [_json_table(document.get("title", "dummy_table"), document)]
        if not tables:
            raise ValueError("객체형 스키마를 찾지 못했습니다.")
        return {"source_type": kind, "tables": tables, "relationships": []}

    if kind != "ddl":
        raise ValueError("source_type은 ddl, json-schema, openapi 중 하나여야 합니다.")
    tables: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    table_pattern = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([\w가-힣]+)[`\"\]]?\s*\((.*?)\)\s*;", re.I | re.S)
    for table_name, body in table_pattern.findall(content):
        parts = re.split(r",\s*(?![^()]*\))", body)
        columns: list[dict[str, Any]] = []
        primary: set[str] = set()
        checks: dict[str, dict[str, Any]] = {}
        for part in parts:
            text = part.strip()
            check_match = re.search(r"CHECK\s*\(\s*[`\"\[]?([\w가-힣]+)[`\"\]]?\s+BETWEEN\s+(-?\d+(?:\.\d+)?)\s+AND\s+(-?\d+(?:\.\d+)?)\s*\)", text, re.I)
            if check_match:
                checks[check_match.group(1)] = {"minimum": float(check_match.group(2)), "maximum": float(check_match.group(3))}
                if text.upper().startswith("CHECK"):
                    continue
            pk_match = re.match(r"PRIMARY\s+KEY\s*\(([^)]+)\)", text, re.I)
            if pk_match:
                primary.update(x.strip(" `\"[]") for x in pk_match.group(1).split(","))
                continue
            fk_match = re.match(r"FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+[`\"\[]?([\w가-힣]+)[`\"\]]?\s*\(([^)]+)\)", text, re.I)
            if fk_match:
                relationships.append({"parent_table": fk_match.group(2), "child_table": table_name,
                                      "parent_key": fk_match.group(3).strip(" `\"[]"),
                                      "child_key": fk_match.group(1).strip(" `\"[]")})
                continue
            match = re.match(r"[`\"\[]?([\w가-힣]+)[`\"\]]?\s+([\w]+(?:\s*\([^)]*\))?)(.*)", text, re.I | re.S)
            if not match:
                continue
            name, sql_type, tail = match.groups()
            upper_type = sql_type.upper()
            data_type = "integer" if "INT" in upper_type else "number" if any(x in upper_type for x in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")) else "string"
            inline_pk = bool(re.search(r"\bPRIMARY\s+KEY\b", tail, re.I))
            columns.append({"name": name, "data_type": data_type,
                            "nullable": not bool(re.search(r"\bNOT\s+NULL\b", tail, re.I)),
                            "primary_key": inline_pk, "unique": bool(re.search(r"\bUNIQUE\b", tail, re.I)),
                            "rule": _rule_for(name, data_type, {}), "constraints": {"sql_type": sql_type}})
        for column in columns:
            if column["name"] in primary:
                column["primary_key"] = True
            if column["name"] in checks:
                column["constraints"].update(checks[column["name"]])
                column["rule"] = _rule_for(column["name"], column["data_type"], checks[column["name"]])
        tables.append({"name": table_name, "columns": columns})
    if not tables:
        raise ValueError("CREATE TABLE 문을 찾지 못했습니다. 각 문장은 세미콜론(;)으로 끝나야 합니다.")
    return {"source_type": "ddl", "tables": tables, "relationships": relationships}
