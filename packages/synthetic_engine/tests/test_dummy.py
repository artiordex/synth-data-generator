# -*- coding: utf-8 -*-
import pytest
import pandas as pd
from synthetic_engine.common.catalog import DomainCatalog
from synthetic_engine.generators.rule_based.dummy_generator import DummyDataGenerator

def test_domain_catalog_load():
    domains = DomainCatalog.list_domains()
    assert len(domains) >= 100, f"Expected at least 100 domains, got {len(domains)}"
    
    categories = DomainCatalog.get_categories()
    assert len(categories) >= 7, f"Expected at least 7 categories, got {len(categories)}"
    
    templates = DomainCatalog.get_templates()
    assert len(templates) >= 6, f"Expected at least 6 templates, got {len(templates)}"

def test_domain_catalog_inference():
    # Korean aliases
    assert DomainCatalog.infer_domain_by_name("고객명")["id"] == "korean_name"
    assert DomainCatalog.infer_domain_by_name("핸드폰")["id"] == "phone_mobile"
    assert DomainCatalog.infer_domain_by_name("생년월일")["id"] == "birth_date"
    assert DomainCatalog.infer_domain_by_name("결제금액")["id"] == "payment_amount"
    assert DomainCatalog.infer_domain_by_name("주민번호")["id"] == "resident_registration_number"
    assert DomainCatalog.infer_domain_by_name("도로명주소")["id"] == "road_address"

    # English aliases
    assert DomainCatalog.infer_domain_by_name("user_id")["id"] == "user_id"
    assert DomainCatalog.infer_domain_by_name("email_addr")["id"] == "email"
    assert DomainCatalog.infer_domain_by_name("ip_address")["id"] == "ip_address"
    assert DomainCatalog.infer_domain_by_name("order_id")["id"] == "order_id"

def test_dummy_generator_with_template():
    gen = DummyDataGenerator(seed=42)
    templates = DomainCatalog.get_templates()
    user_template = templates[0]  # Standard user/member template

    df = gen.generate(columns=user_template["columns"], num_rows=100)
    assert len(df) == 100
    assert len(df.columns) == len(user_template["columns"])
    assert "user_id" in df.columns
    assert "user_name" in df.columns

    # Verify that sequence generation works as expected
    assert str(df["user_id"].iloc[0]).startswith("USR_")

def test_dummy_generator_all_domains():
    """Ensure that every single standard domain in the catalog can generate data without error."""
    domains = DomainCatalog.list_domains()
    columns = [{"name": d["id"], "domain_id": d["id"]} for d in domains]
    
    gen = DummyDataGenerator(seed=123)
    df = gen.generate(columns=columns, num_rows=50)
    assert df.shape == (50, len(domains))

def test_dummy_sql_insert_export():
    gen = DummyDataGenerator(seed=42)
    cols = [
        {"name": "id", "domain_id": "user_id"},
        {"name": "name", "domain_id": "korean_name"},
        {"name": "amount", "domain_id": "payment_amount"}
    ]
    df = gen.generate(cols, num_rows=10)
    sql = DummyDataGenerator.to_sql_insert(df, table_name="test_users", limit=10)
    assert "INSERT INTO `test_users`" in sql
    assert "`id`, `name`, `amount`" in sql
    assert "USR_" in sql
