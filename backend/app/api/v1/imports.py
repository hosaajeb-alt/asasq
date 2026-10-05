from __future__ import annotations

import hashlib
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.application.ingest import commit_import
from app.application.parsers import sample_columns, sniff_kind
from app.application.serializers import dataset_out, job_out
from app.core.config import get_settings
from app.collections.scope import require_collection
from app.domain.models import Collection, Dataset, DatasetField, DatasetVersion, ImportJob, User
from app.infrastructure.db import get_db
from app.profiling.profiler import DataProfiler
from app.schema_detection.detector import SchemaDetector

router = APIRouter(prefix="/imports", tags=["imports"])


def _data_dir() -> Path:
    p = Path(get_settings().data_dir) / "imports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "dataset"


class MetaIn(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
    source: str = ""
    source_description: str = ""
    dataset_date: Optional[date] = None
    languages: list[str] = []
    geographic_scope: str = ""
    version_label: str = "v1"
    legal_classification: str = "internal"
    tags: list[str] = []
    notes: str = ""
    collection_id: Optional[str] = None


class CollectionBindIn(BaseModel):
    collection_id: str


class MapIn(BaseModel):
    fields: list[dict[str, Any]]


class NormIn(BaseModel):
    rules: dict[str, Any] = {}


class EntityMapIn(BaseModel):
    mappings: dict[str, str] = {}


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "file too large")
    allowed = (".csv", ".json", ".jsonl", ".ndjson", ".parquet")
    name = file.filename or "upload.csv"
    if not any(name.lower().endswith(a) for a in allowed):
        raise HTTPException(400, "unsupported file type")
    checksum = hashlib.sha256(raw).hexdigest()
    job = ImportJob(
        created_by=user.id,
        filename=name,
        content_type=file.content_type or "",
        byte_size=len(raw),
        checksum=checksum,
        status="draft",
        step=1,
        wizard_state={"filename": name},
    )
    db.add(job)
    db.flush()
    dest = _data_dir() / str(job.id)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / name
    path.write_bytes(raw)
    job.storage_path = str(path)
    try:
        cols, rows = sample_columns(path, name, job.content_type, limit=50)
        job.wizard_state = {
            **job.wizard_state,
            "columns": cols,
            "sample": rows[:12],
            "kind": sniff_kind(name, job.content_type),
        }
        job.total_records = 0
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:500]
    write_audit(db, actor_id=user.id, action="dataset_import", resource_type="import_job", resource_id=str(job.id))
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.get("/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job_out(job)


@router.post("/{job_id}/meta")
def set_meta(job_id: UUID, body: MetaIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    state = dict(job.wizard_state or {})
    state["meta"] = body.model_dump(mode="json")
    job.wizard_state = state
    job.step = max(job.step, 2)
    if body.collection_id:
        cid = UUID(body.collection_id)
        require_collection(db, user, cid, "import")
        job.collection_id = cid
        state["collection_id"] = body.collection_id
        job.wizard_state = state
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.post("/{job_id}/collection")
def bind_collection(job_id: UUID, body: CollectionBindIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    cid = UUID(body.collection_id)
    require_collection(db, user, cid, "import")
    job.collection_id = cid
    state = dict(job.wizard_state or {})
    state["collection_id"] = body.collection_id
    job.wizard_state = state
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.post("/{job_id}/detect-schema")
def detect_schema(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    cols, rows = sample_columns(job.storage_path, job.filename, job.content_type, limit=400)
    columns: dict[str, list] = {c: [] for c in cols}
    for row in rows:
        for c in cols:
            columns[c].append(row.get(c))
    detected = SchemaDetector().detect_table(columns)
    state = dict(job.wizard_state or {})
    state["detected_schema"] = detected
    state["columns"] = cols
    job.wizard_state = state
    job.step = max(job.step, 3)
    db.commit()
    db.refresh(job)
    return {**job_out(job), "detected_schema": detected}


@router.post("/{job_id}/map-fields")
def map_fields(job_id: UUID, body: MapIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    state = dict(job.wizard_state or {})
    state["mapped_fields"] = body.fields
    job.wizard_state = state
    job.step = max(job.step, 4)
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.post("/{job_id}/normalization")
def set_norm(job_id: UUID, body: NormIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    state = dict(job.wizard_state or {})
    state["normalization"] = body.rules
    job.wizard_state = state
    job.step = max(job.step, 5)
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.post("/{job_id}/profile")
def profile_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    _cols, rows = sample_columns(job.storage_path, job.filename, job.content_type, limit=2000)
    schema = (job.wizard_state or {}).get("mapped_fields") or (job.wizard_state or {}).get("detected_schema") or []
    meta = (job.wizard_state or {}).get("meta") or {}
    profile = DataProfiler().profile(rows, schema=schema, dataset_name=meta.get("name") or job.filename)
    state = dict(job.wizard_state or {})
    state["profile"] = profile
    job.wizard_state = state
    job.step = max(job.step, 6)
    job.total_records = profile.get("records", 0)
    db.commit()
    db.refresh(job)
    return {**job_out(job), "profile": profile}


@router.post("/{job_id}/entity-mapping")
def entity_map(job_id: UUID, body: EntityMapIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    state = dict(job.wizard_state or {})
    state["entity_mappings"] = body.mappings
    job.wizard_state = state
    job.step = max(job.step, 7)
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.post("/{job_id}/commit")
def commit_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status in ("processing", "completed"):
        raise HTTPException(409, f"job already {job.status}")
    state = job.wizard_state or {}
    meta = state.get("meta") or {}
    if not meta.get("name"):
        raise HTTPException(400, "dataset metadata required")
    schema_fields = state.get("mapped_fields") or state.get("detected_schema") or []
    if not schema_fields:
        raise HTTPException(400, "schema mapping required")
    collection_id = job.collection_id or (UUID(state["collection_id"]) if state.get("collection_id") else None)
    if not collection_id:
        raise HTTPException(400, "collection context required — select or create a collection before import")
    col = require_collection(db, user, collection_id, "import")

    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.step = 9
    db.flush()

    slug = _slug(meta["name"])
    base, i = slug, 2
    while db.query(Dataset).filter(Dataset.slug == slug).first():
        slug = f"{base}-{i}"
        i += 1
    langs = meta.get("languages") or []
    ds = Dataset(
        slug=slug,
        name=meta["name"],
        description=meta.get("description") or "",
        category=meta.get("category") or "custom",
        source=meta.get("source") or "",
        source_description=meta.get("source_description") or "",
        dataset_date=date.fromisoformat(meta["dataset_date"]) if meta.get("dataset_date") else None,
        languages=langs,
        geographic_scope=meta.get("geographic_scope") or "",
        version_label=meta.get("version_label") or "v1",
        legal_classification=meta.get("legal_classification") or "internal",
        tags=meta.get("tags") or [],
        notes=meta.get("notes") or "",
        processing_status="processing",
        schema_json={"fields": schema_fields},
        data_quality=state.get("profile") or {},
        provenance={
            "filename": job.filename,
            "checksum": job.checksum,
            "byte_size": job.byte_size,
            "importer_id": str(user.id),
        },
        owner_id=user.id,
        collection_id=collection_id,
    )
    db.add(ds)
    db.flush()
    version = DatasetVersion(
        dataset_id=ds.id,
        version_number=1,
        version_label=ds.version_label,
        schema_json=ds.schema_json,
        quality_json=ds.data_quality,
        object_uri=job.storage_path,
        checksum=job.checksum,
    )
    db.add(version)
    db.flush()
    for i, f in enumerate(schema_fields):
        db.add(
            DatasetField(
                dataset_id=ds.id,
                version_id=version.id,
                name=f.get("name"),
                physical_type=f.get("physical_type") or "string",
                semantic_type=f.get("semantic_type") or "FreeText",
                confidence=float(f.get("confidence") or 0),
                approved=True,
                ordinal=i,
            )
        )
    lang_hint = langs[0] if langs else None
    stats = commit_import(
        db,
        dataset=ds,
        version=version,
        storage_path=job.storage_path,
        filename=job.filename,
        content_type=job.content_type,
        schema_fields=schema_fields,
        language_hint=lang_hint,
        entity_mappings=state.get("entity_mappings") or {},
        collection_id=collection_id,
        normalization_policy=col.normalization_policy or {},
    )
    job.dataset_id = ds.id
    job.collection_id = collection_id
    col.dataset_count = (col.dataset_count or 0) + 1
    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)
    job.records_processed = stats["records_processed"]
    job.invalid_count = stats["invalid_count"]
    job.duplicate_count = stats["duplicate_count"]
    job.total_records = stats["records_processed"]
    write_audit(
        db,
        actor_id=user.id,
        action="dataset_imported",
        resource_type="dataset",
        resource_id=str(ds.id),
        payload=stats,
        collection_id=collection_id,
        dataset_id=ds.id,
    )
    db.commit()
    db.refresh(ds)
    db.refresh(job)
    return {"job": job_out(job), "dataset": dataset_out(ds)}


@router.post("/{job_id}/cancel")
def cancel(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status == "completed":
        raise HTTPException(409, "already completed")
    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return job_out(job)
