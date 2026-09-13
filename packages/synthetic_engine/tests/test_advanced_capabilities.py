# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_advanced_capabilities.py
# 경로: packages/synthetic_engine/tests/test_advanced_capabilities.py
# 목적: 고급 문서 변환 기능 및 복합 서식 처리를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pandas as pd

from synthetic_engine import (
    DummyDataGenerator,
    PanelTimeSeriesSynthesizer,
    evaluate_klt,
    import_schema,
    project_token,
)


# project tokens are consistent and scoped 기능의 정상 동작 및 제약조건을 테스트함
def test_project_tokens_are_consistent_and_scoped():
    first = project_token("customer-1", project_id="alpha", namespace="customer_id")
    assert first == project_token("customer-1", project_id="alpha", namespace="customer_id")
    assert first != project_token("customer-1", project_id="beta", namespace="customer_id")
    assert first != project_token("customer-1", project_id="alpha", namespace="email")


# klt reports group privacy 품질 지표 기능의 정상 동작 및 제약조건을 테스트함
def test_klt_reports_group_privacy_metrics():
    frame = pd.DataFrame({"age_band": ["20", "20", "30", "30"],
                          "region": ["S", "S", "B", "B"],
                          "diagnosis": ["A", "B", "A", "B"]})
    report = evaluate_klt(frame, ["age_band", "region"], ["diagnosis"],
                          k_threshold=2, l_threshold=2, t_threshold=0.2)
    assert report["status"] == "PASS"
    assert report["k"] == 2 and report["l"] == 2 and report["t"] == 0


# 스키마 import supports ddl json 스키마 and openapi 기능의 정상 동작 및 제약조건을 테스트함
def test_schema_import_supports_ddl_json_schema_and_openapi():
    ddl = """CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(200) UNIQUE NOT NULL, age INTEGER CHECK (age BETWEEN 18 AND 99));
    CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id));"""
    parsed = import_schema("ddl", ddl)
    assert [table["name"] for table in parsed["tables"]] == ["users", "orders"]
    assert parsed["relationships"][0]["child_key"] == "user_id"
    age = next(c for c in parsed["tables"][0]["columns"] if c["name"] == "age")
    assert age["rule"]["min"] == 18 and age["rule"]["max"] == 99

    schema = import_schema("json-schema", '{"title":"Person","type":"object","required":["age"],"properties":{"age":{"type":"integer","minimum":0,"maximum":120}}}')
    assert schema["tables"][0]["columns"][0]["nullable"] is False
    api = import_schema("openapi", '{"openapi":"3.0.0","components":{"schemas":{"User":{"type":"object","properties":{"id":{"type":"integer"}}}}}}')
    assert api["tables"][0]["name"] == "User"


# 더미 데이터 scenarios and panel generation 기능의 정상 동작 및 제약조건을 테스트함
def test_dummy_scenarios_and_panel_generation():
    columns = [{"name": "score", "rule": {"type": "number_range", "min": 0, "max": 10, "integer": True}}]
    boundary = DummyDataGenerator().generate(columns, 5, scenario="boundary")
    assert boundary.iloc[0, 0] == 0 and boundary.iloc[1, 0] == 10
    invalid = DummyDataGenerator().generate(columns, 5, scenario="invalid")
    assert invalid.iloc[0, 0] > 10

    raw = pd.DataFrame({"member_id": [1, 1, 2, 2], "date": ["2024-01-01", "2024-01-03", "2024-02-01", "2024-02-04"], "value": [1, 2, 10, 12]})
    generated = PanelTimeSeriesSynthesizer(7).sample(raw, entity_column="member_id", time_column="date", target_entities=3)
    assert generated["member_id"].nunique() == 3
    assert len(generated) == 6
