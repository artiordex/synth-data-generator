# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "domain_catalog.json"

class DomainCatalog:
    _domains: list[dict[str, Any]] = []
    _domain_map: dict[str, dict[str, Any]] = {}
    _alias_map: dict[str, dict[str, Any]] = {}

    @classmethod
    def _load(cls) -> None:
        if cls._domains:
            return
        if not CATALOG_PATH.exists():
            return
        with CATALOG_PATH.open("r", encoding="utf-8") as f:
            cls._domains = json.load(f)

        for item in cls._domains:
            domain_id = item["id"]
            cls._domain_map[domain_id] = item
            for alias in item.get("aliases", []):
                norm = re.sub(r"[\s_\-\.\(\)]+", "", alias.lower())
                cls._alias_map[norm] = item

    @classmethod
    def list_domains(cls, category: str | None = None) -> list[dict[str, Any]]:
        cls._load()
        if category:
            return [d for d in cls._domains if d.get("category") == category]
        return list(cls._domains)

    @classmethod
    def get_categories(cls) -> list[str]:
        cls._load()
        cats = []
        for d in cls._domains:
            c = d.get("category", "기타")
            if c not in cats:
                cats.append(c)
        return cats

    @classmethod
    def get_domain(cls, domain_id: str) -> dict[str, Any] | None:
        cls._load()
        return cls._domain_map.get(domain_id)

    @classmethod
    def infer_domain_by_name(cls, column_name: str) -> dict[str, Any]:
        """Smart matcher that maps an arbitrary column name to the closest standard domain."""
        cls._load()
        col_clean = re.sub(r"[\s_\-\.\(\)]+", "", str(column_name).lower())

        # 1. Exact alias match
        if col_clean in cls._alias_map:
            return cls._alias_map[col_clean]

        # 2. Substring matching against aliases
        for alias_norm, domain in cls._alias_map.items():
            if len(alias_norm) >= 2 and (alias_norm in col_clean or col_clean in alias_norm):
                return domain

        # 3. Fallback default based on keywords
        if any(k in col_clean for k in ["금액", "가격", "비용", "price", "amount", "cost"]):
            return cls._domain_map.get("payment_amount", cls._domains[0])
        if any(k in col_clean for k in ["일자", "일시", "날짜", "date", "time"]):
            return cls._domain_map.get("created_datetime", cls._domains[0])
        if any(k in col_clean for k in ["수량", "건수", "개수", "count", "qty"]):
            return cls._domain_map.get("order_quantity", cls._domains[0])
        if any(k in col_clean for k in ["번호", "id", "코드", "code"]):
            return cls._domain_map.get("user_id", cls._domains[0])

        # Default string fallback
        return {
            "id": "generic_text",
            "name": column_name,
            "english_name": column_name,
            "category": "일반 문자열",
            "data_type": "STRING",
            "rule": { "type": "choice", "values": [f"{column_name}_1", f"{column_name}_2", f"{column_name}_3"] },
            "sample": f"{column_name}_샘플"
        }

    @classmethod
    def get_templates(cls) -> list[dict[str, Any]]:
        """Predefined standard schemas for 1-click creation."""
        cls._load()
        return [
            {
                "id": "user_account",
                "name": "회원 / 고객 계정 정보",
                "desc": "일반 웹/앱 서비스의 표준 회원 계정 및 프로필 테이블",
                "icon": "User",
                "columns": [
                    { "name": "user_id", "domain_id": "user_id" },
                    { "name": "user_name", "domain_id": "korean_name" },
                    { "name": "mobile_phone", "domain_id": "phone_mobile" },
                    { "name": "email", "domain_id": "email" },
                    { "name": "gender", "domain_id": "gender" },
                    { "name": "age", "domain_id": "age" },
                    { "name": "road_address", "domain_id": "road_address" },
                    { "name": "join_date", "domain_id": "created_datetime" }
                ]
            },
            {
                "id": "ecommerce_order",
                "name": "이커머스 주문 결제 내역",
                "desc": "온라인 쇼핑몰의 주문, 상품, 결제 및 배송 상태 테이블",
                "icon": "Package",
                "columns": [
                    { "name": "order_id", "domain_id": "order_id" },
                    { "name": "customer_name", "domain_id": "korean_name" },
                    { "name": "product_name", "domain_id": "product_name" },
                    { "name": "category", "domain_id": "category_large" },
                    { "name": "quantity", "domain_id": "order_quantity" },
                    { "name": "pay_amount", "domain_id": "payment_amount" },
                    { "name": "pay_method", "domain_id": "payment_method" },
                    { "name": "delivery_status", "domain_id": "delivery_status" },
                    { "name": "order_date", "domain_id": "created_datetime" }
                ]
            },
            {
                "id": "card_transaction",
                "name": "카드사 거래 및 승인 내역",
                "desc": "금융 마이데이터 표준 카드 결제 승인 및 취소 트랜잭션",
                "icon": "CreditCard",
                "columns": [
                    { "name": "card_company", "domain_id": "card_company" },
                    { "name": "card_number", "domain_id": "credit_card_number" },
                    { "name": "approval_status", "domain_id": "approval_status" },
                    { "name": "amount", "domain_id": "payment_amount" },
                    { "name": "currency", "domain_id": "currency" },
                    { "name": "installment", "domain_id": "installment_month" },
                    { "name": "transaction_date", "domain_id": "created_datetime" }
                ]
            },
            {
                "id": "hospital_health",
                "name": "병원 진료 및 건강검진",
                "desc": "기초 신체 활력징후 및 혈압, 혈당 진료 내역",
                "icon": "Activity",
                "columns": [
                    { "name": "patient_id", "domain_id": "patient_id" },
                    { "name": "patient_name", "domain_id": "korean_name" },
                    { "name": "gender", "domain_id": "gender" },
                    { "name": "age", "domain_id": "age" },
                    { "name": "systolic_bp", "domain_id": "systolic_bp" },
                    { "name": "diastolic_bp", "domain_id": "diastolic_bp" },
                    { "name": "blood_glucose", "domain_id": "fasting_glucose" },
                    { "name": "department", "domain_id": "medical_department" }
                ]
            },
            {
                "id": "corporate_info",
                "name": "기업 및 사업자 명세",
                "desc": "법인 및 개인사업자 등록정보, 매출액, 임직원 현황",
                "icon": "Building",
                "columns": [
                    { "name": "company_name", "domain_id": "company_name" },
                    { "name": "biz_no", "domain_id": "business_number" },
                    { "name": "corp_no", "domain_id": "corporate_number" },
                    { "name": "ceo_name", "domain_id": "ceo_name" },
                    { "name": "industry", "domain_id": "industry_type" },
                    { "name": "headcount", "domain_id": "employee_headcount" },
                    { "name": "revenue", "domain_id": "annual_revenue" }
                ]
            },
            {
                "id": "web_access_log",
                "name": "웹 서버 접속 로그",
                "desc": "웹/API 서비스 트래픽, IP, User-Agent 및 응답시간 로그",
                "icon": "Server",
                "columns": [
                    { "name": "request_id", "domain_id": "uuid" },
                    { "name": "client_ip", "domain_id": "ip_address" },
                    { "name": "http_status", "domain_id": "http_status" },
                    { "name": "response_time", "domain_id": "response_time_ms" },
                    { "name": "user_agent", "domain_id": "user_agent" },
                    { "name": "log_time", "domain_id": "created_datetime" }
                ]
            }
        ]
