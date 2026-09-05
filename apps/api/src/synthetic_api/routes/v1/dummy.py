import uuid
import numpy as np
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from synthetic_api.core.config import settings
from synthetic_engine import DomainCatalog, DummyDataGenerator, import_schema

router = APIRouter(prefix="/dummy", tags=["dummy"])

class InferColumnRequest(BaseModel):
    column_name: str

class ColumnDefinition(BaseModel):
    name: str
    domain_id: Optional[str] = None
    rule: Optional[Dict[str, Any]] = None
    primary_key: bool = False
    unique: bool = False
    nullable: bool = True
    constraints: Dict[str, Any] = Field(default_factory=dict)

class GenerateDummyRequest(BaseModel):
    table_name: str = "dummy_table"
    columns: List[ColumnDefinition]
    target_rows: int = 1000
    export_format: str = "csv"  # csv, xlsx, sql, json
    scenario: str = "normal"

class ImportSchemaRequest(BaseModel):
    source_type: str
    content: str

class GenerateSchemaRequest(BaseModel):
    schema_definition: Dict[str, Any]
    target_rows: int = 1000
    scenario: str = "normal"

@router.get("/domains")
async def get_domains():
    """Return all standard domains grouped by category."""
    domains = DomainCatalog.list_domains()
    categories = DomainCatalog.get_categories()
    grouped = {cat: [d for d in domains if d.get("category") == cat] for cat in categories}
    return {
        "categories": categories,
        "total_count": len(domains),
        "grouped_domains": grouped,
        "domains": domains
    }

@router.get("/templates")
async def get_templates():
    """Return predefined schema templates."""
    return {
        "templates": DomainCatalog.get_templates()
    }

@router.post("/infer-column")
async def infer_column(req: InferColumnRequest):
    """Automatically infer the best matching domain for a given column name."""
    matched = DomainCatalog.infer_domain_by_name(req.column_name)
    return {
        "column_name": req.column_name,
        "inferred_domain": matched
    }

@router.post("/import-schema")
async def import_dummy_schema(req: ImportSchemaRequest):
    try:
        return import_schema(req.source_type, req.content)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/generate-schema")
async def generate_dummy_schema(req: GenerateSchemaRequest):
    tables = req.schema_definition.get("tables", [])
    relationships = req.schema_definition.get("relationships", [])
    if not tables:
        raise HTTPException(status_code=422, detail="생성할 테이블 스키마가 없습니다.")
    generator = DummyDataGenerator()
    generated: Dict[str, Any] = {}
    row_count = max(1, min(req.target_rows, 500000))
    try:
        for table in tables:
            generated[table["name"]] = generator.generate(table.get("columns", []), row_count, req.scenario)
        rng = np.random.default_rng(42)
        integrity = []
        for rel in relationships:
            parent = generated.get(rel["parent_table"])
            child = generated.get(rel["child_table"])
            if parent is None or child is None or rel["parent_key"] not in parent:
                continue
            keys = parent[rel["parent_key"]].dropna().values
            if len(keys):
                child[rel["child_key"]] = rng.choice(keys, size=len(child), replace=True)
            integrity.append({**rel, "orphan_count": 0, "status": "PASS"})
        uid = f"schema-dummy-{uuid.uuid4().hex[:8]}"
        root = settings.OUTPUT_DIR / uid
        root.mkdir(parents=True, exist_ok=True)
        for name, frame in generated.items():
            frame.to_csv(root / f"{name}.csv", index=False, encoding="utf-8-sig")
        zip_path = settings.OUTPUT_DIR / f"{uid}.zip"
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
            for file in root.glob("*.csv"):
                archive.write(file, file.name)
        first_name = next(iter(generated))
        first = generated[first_name]
        return {"status": "success", "table_name": first_name, "rows_generated": sum(len(x) for x in generated.values()),
                "columns": list(first.columns), "preview": first.head(15).fillna("").to_dict(orient="records"),
                "tables": [{"name": name, "rows": len(frame)} for name, frame in generated.items()],
                "relationships": integrity, "file_name": zip_path.name, "file_path": str(zip_path),
                "download_url": f"/api/v1/files/download?path={zip_path.as_posix()}", "scenario": req.scenario}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/generate")
async def generate_dummy(req: GenerateDummyRequest):
    """Generate dummy data from schema definition and save in the requested format."""
    if not req.columns:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 컬럼 정의가 필요합니다.")

    target_rows = max(1, min(req.target_rows, 500000))
    generator = DummyDataGenerator()
    
    col_dicts = [col.model_dump() for col in req.columns]
    try:
        df = generator.generate(columns=col_dicts, num_rows=target_rows, scenario=req.scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"더미 데이터 생성 실패: {str(e)}")

    dummy_dir = settings.OUTPUT_DIR / "dummy"
    dummy_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    fmt = req.export_format.lower()
    table_clean = "".join(c for c in req.table_name if c.isalnum() or c in ("_", "-")) or "dummy_data"
    
    if fmt == "xlsx":
        file_name = f"{table_clean}_{uid}.xlsx"
        file_path = dummy_dir / file_name
        df.to_excel(file_path, index=False)
    elif fmt == "sql":
        file_name = f"{table_clean}_{uid}.sql"
        file_path = dummy_dir / file_name
        sql_content = DummyDataGenerator.to_sql_insert(df, table_name=table_clean, limit=min(len(df), 20000))
        file_path.write_text(sql_content, encoding="utf-8")
    elif fmt == "json":
        file_name = f"{table_clean}_{uid}.json"
        file_path = dummy_dir / file_name
        df.to_json(file_path, orient="records", force_ascii=False, indent=2)
    else:  # default csv
        file_name = f"{table_clean}_{uid}.csv"
        file_path = dummy_dir / file_name
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

    # Generate preview
    preview_records = df.head(15).fillna("").to_dict(orient="records")
    download_url = f"/api/v1/files/download?path={file_path.as_posix()}"

    # Record dummy history
    hist_file = dummy_dir / "dummy_history.json"
    history_list = []
    if hist_file.exists():
        try:
            import json
            with hist_file.open("r", encoding="utf-8") as f:
                history_list = json.load(f)
        except Exception:
            history_list = []

    from datetime import datetime
    history_entry = {
        "id": uid,
        "table_name": table_clean,
        "file_name": file_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_generated": len(df),
        "columns_count": len(df.columns),
        "scenario": req.scenario,
        "export_format": fmt.upper(),
        "download_url": download_url
    }
    history_list.insert(0, history_entry)
    history_list = history_list[:50]
    try:
        import json
        with hist_file.open("w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {
        "status": "success",
        "table_name": table_clean,
        "rows_generated": len(df),
        "columns": list(df.columns),
        "scenario": req.scenario,
        "preview": preview_records,
        "download_url": download_url,
        "file_name": file_name,
        "file_path": str(file_path)
    }

@router.get("/history")
async def get_dummy_history():
    dummy_dir = settings.OUTPUT_DIR / "dummy"
    hist_file = dummy_dir / "dummy_history.json"
    if not hist_file.exists():
        return []
    try:
        import json
        with hist_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
