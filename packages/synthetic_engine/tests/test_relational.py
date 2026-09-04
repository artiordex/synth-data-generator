# -*- coding: utf-8 -*-
import pytest
import numpy as np
import pandas as pd
from synthetic_engine import (
    TableRelationship,
    TurboRelationalSampler,
    HMARelationalSynthesizer,
)

@pytest.fixture
def relational_data():
    np.random.seed(42)
    n_users = 25
    n_orders = 75

    users = pd.DataFrame({
        "user_id": [f"USR_{i:04d}" for i in range(1, n_users + 1)],
        "user_name": [f"사용자_{i}" for i in range(1, n_users + 1)],
        "age": np.random.randint(20, 65, size=n_users),
        "city": np.random.choice(["서울", "부산", "대구", "인천", "대전"], size=n_users),
    })

    orders = pd.DataFrame({
        "order_id": [f"ORD_{i:05d}" for i in range(1, n_orders + 1)],
        "user_id": np.random.choice(users["user_id"].values, size=n_orders),
        "order_amount": np.random.randint(10000, 500000, size=n_orders),
        "item_count": np.random.randint(1, 10, size=n_orders),
    })

    relationship = TableRelationship(
        parent_table="users",
        child_table="orders",
        parent_key="user_id",
        child_key="user_id"
    )

    return {"users": users, "orders": orders}, [relationship]

def test_turbo_relational_sampler(relational_data):
    tables, relationships = relational_data
    sampler = TurboRelationalSampler(seed=42)
    sampler.fit(
        tables=tables,
        relationships=relationships,
        primary_keys={"users": "user_id", "orders": "order_id"}
    )

    result = sampler.sample(num_rows_or_scale=50)

    assert "users" in result
    assert "orders" in result

    gen_users = result["users"]
    gen_orders = result["orders"]

    assert len(gen_users) == 50
    assert len(gen_orders) == 50

    # Test 100% referential integrity: Every order's user_id MUST exist in generated users
    valid_user_ids = set(gen_users["user_id"].values)
    order_user_ids = set(gen_orders["user_id"].values)

    orphans = order_user_ids - valid_user_ids
    assert len(orphans) == 0, f"Found orphan foreign keys in child table: {orphans}"

    # Verify primary keys are unique
    assert gen_users["user_id"].nunique() == len(gen_users)
    assert gen_orders["order_id"].nunique() == len(gen_orders)

def test_hma_relational_synthesizer(relational_data):
    tables, relationships = relational_data
    hma = HMARelationalSynthesizer(verbose=False)
    hma.fit(
        tables=tables,
        relationships=relationships,
        primary_keys={"users": "user_id", "orders": "order_id"}
    )

    result = hma.sample(scale=0.5)

    assert "users" in result
    assert "orders" in result
    assert len(result["users"]) > 0
    assert len(result["orders"]) > 0

    valid_user_ids = set(result["users"]["user_id"].values)
    order_user_ids = set(result["orders"]["user_id"].values)
    orphans = order_user_ids - valid_user_ids
    assert len(orphans) == 0, f"HMA generated orphan foreign keys: {orphans}"
