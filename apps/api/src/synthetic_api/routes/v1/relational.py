from __future__ import annotations

import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from synthetic_api.core.config import settings
from synthetic_engine import HMARelationalSynthesizer, TableRelationship, TurboRelationalSampler, read_table


router = APIRouter(prefix="/relational", tags=["relational-synthesis"])


class RelationshipSpec(BaseModel):
    parent_table: str
    child_table: str
    parent_key: str
    child_key: str


class RelationalRequest(BaseModel):
    file_names: list[str] = Field(min_length=2, max_length=20)
    relationships: list[RelationshipSpec] = Field(default_factory=list)
    primary_keys: dict[str, str] = Field(default_factory=dict)
    model_type: str = "turbo"
    scale: float = Field(default=1.0, gt=0, le=20)
    seed: int = 42


def _load_tables(file_names: list[str]) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for file_name in file_names:
        path = settings.UPLOAD_DIR / Path(file_name).name
        if not path.exists():
            raise FileNotFoundError(Path(file_name).name)
        name = Path(file_name).stem
        candidate, suffix = name, 2
        while candidate in tables:
            candidate, suffix = f"{name}_{suffix}", suffix + 1
        tables[candidate] = read_table(path)
    return tables


def _infer(tables: dict[str, pd.DataFrame]) -> tuple[dict[str, str], list[TableRelationship]]:
    primary: dict[str, str] = {}
    for table, frame in tables.items():
        candidates = [c for c in frame.columns if frame[c].notna().all() and frame[c].is_unique]
        preferred = [c for c in candidates if str(c).lower() in {"id", f"{table.lower()}_id"} or str(c).lower().endswith("_id")]
        if preferred or candidates:
            primary[table] = str((preferred or candidates)[0])

    relationships: list[TableRelationship] = []
    for parent, key in primary.items():
        parent_values = set(tables[parent][key].dropna().astype(str))
        if not parent_values:
            continue
        for child, frame in tables.items():
            if child == parent:
                continue
            for column in frame.columns:
                child_values = frame[column].dropna().astype(str)
                if len(child_values) == 0:
                    continue
                overlap = float(child_values.isin(parent_values).mean())
                name_match = str(column).lower() == key.lower()
                if overlap >= 0.8 and (name_match or str(column).lower().endswith("_id")):
                    relationships.append(TableRelationship(parent, child, key, str(column)))
                    break
    return primary, relationships


@router.post("/profile")
def profile_relational(req: RelationalRequest):
    try:
        tables = _load_tables(req.file_names)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"업로드 파일을 찾을 수 없습니다: {exc}")
    primary, relationships = _infer(tables)
    return {
        "tables": [{"name": name, "rows": len(frame), "columns": list(frame.columns),
                    "primary_key": primary.get(name)} for name, frame in tables.items()],
        "primary_keys": primary,
        "relationships": [rel.__dict__ for rel in relationships],
    }


@router.post("/generate")
def generate_relational(req: RelationalRequest):
    try:
        tables = _load_tables(req.file_names)
        inferred_primary, inferred_relationships = _infer(tables)
        primary = {**inferred_primary, **req.primary_keys}
        relationships = [TableRelationship(**item.model_dump()) for item in req.relationships] or inferred_relationships
        if not relationships:
            raise ValueError("PK/FK 관계를 자동 탐지하지 못했습니다. 관계를 직접 지정하세요.")
        if req.model_type == "hma":
            generator = HMARelationalSynthesizer()
            generator.fit(tables, relationships, primary)
            generated = generator.sample(scale=req.scale)
        else:
            generator = TurboRelationalSampler(seed=req.seed)
            generator.fit(tables, relationships, primary)
            generated = generator.sample(req.scale)

        job_id = f"rel-{uuid.uuid4().hex[:8]}"
        root = settings.OUTPUT_DIR / job_id
        root.mkdir(parents=True, exist_ok=True)
        integrity = []
        for name, frame in generated.items():
            frame.to_csv(root / f"{name}.csv", index=False, encoding="utf-8-sig")
        for rel in relationships:
            parent_keys = set(generated[rel.parent_table][rel.parent_key].dropna().astype(str))
            child_keys = generated[rel.child_table][rel.child_key].dropna().astype(str)
            orphans = int((~child_keys.isin(parent_keys)).sum())
            integrity.append({**rel.__dict__, "orphan_count": orphans, "status": "PASS" if orphans == 0 else "FAIL"})
        zip_path = settings.OUTPUT_DIR / f"{job_id}.zip"
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
            for file in root.glob("*.csv"):
                archive.write(file, file.name)
        return {
            "status": "completed", "id": job_id, "model_type": req.model_type,
            "tables": [{"name": name, "rows": len(frame), "columns": list(frame.columns),
                        "preview": frame.head(5).fillna("").to_dict(orient="records")}
                       for name, frame in generated.items()],
            "primary_keys": primary, "relationships": integrity,
            "download_url": f"/api/v1/files/download?path={zip_path.as_posix()}",
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"업로드 파일을 찾을 수 없습니다: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
