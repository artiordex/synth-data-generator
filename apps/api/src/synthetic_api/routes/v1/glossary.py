import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

GLOSSARY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "glossary.json"

_glossary_cache: Optional[List[Dict[str, Any]]] = None

def get_glossary_data() -> List[Dict[str, Any]]:
    global _glossary_cache
    if _glossary_cache is None:
        if GLOSSARY_FILE.exists():
            with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                _glossary_cache = json.load(f)
        else:
            _glossary_cache = []
    return _glossary_cache

class GlossaryItemResponse(BaseModel):
    id: str
    name: str
    description: str
    url: str
    category: str
    initial: str

class GlossaryListResponse(BaseModel):
    total_count: int
    items: List[GlossaryItemResponse]
    categories: List[str]
    category_counts: Dict[str, int]

@router.get("", response_model=GlossaryListResponse)
def list_glossary_terms(
    q: Optional[str] = Query(None, description="검색어 (용어명 또는 설명문 검색)"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    initial: Optional[str] = Query(None, description="초성 또는 알파벳 필터 (ㄱ-ㅎ, A-Z, 0-9)"),
) -> GlossaryListResponse:
    terms = get_glossary_data()
    
    # Calculate category counts across whole dataset
    category_counts: Dict[str, int] = {}
    for t in terms:
        c = t.get("category", "기타")
        category_counts[c] = category_counts.get(c, 0) + 1

    filtered = terms
    if q and q.strip():
        query = q.strip().lower()
        filtered = [
            t for t in filtered 
            if query in t.get("name", "").lower() or query in t.get("description", "").lower()
        ]

    if category and category.strip() and category != "전체":
        filtered = [t for t in filtered if t.get("category") == category.strip()]

    if initial and initial.strip() and initial != "전체":
        init = initial.strip()
        if init == "A-Z":
            filtered = [
                t for t in filtered 
                if t.get("name", "").strip() and 'A' <= t.get("name", "").strip()[0].upper() <= 'Z'
            ]
        elif init == "0-9":
            filtered = [
                t for t in filtered 
                if t.get("name", "").strip() and '0' <= t.get("name", "").strip()[0] <= '9'
            ]
        else:
            filtered = [t for t in filtered if t.get("initial") == init]

    categories = [
        "전체",
        "머신러닝 & 딥러닝",
        "자연어 & 멀티모달",
        "LLM & 생성형 AI",
        "보안 & 프라이버시",
        "비즈니스 AI & 자동화",
        "AI 에이전트 & RAG"
    ]

    return GlossaryListResponse(
        total_count=len(filtered),
        items=[GlossaryItemResponse(**item) for item in filtered],
        categories=categories,
        category_counts=category_counts
    )

@router.get("/{item_id}", response_model=GlossaryItemResponse)
def get_glossary_term(item_id: str) -> GlossaryItemResponse:
    terms = get_glossary_data()
    for t in terms:
        if t.get("id") == item_id or t.get("name") == item_id:
            return GlossaryItemResponse(**t)
    raise HTTPException(status_code=404, detail="해당 용어를 찾을 수 없습니다.")
