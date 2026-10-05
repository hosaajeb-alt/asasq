from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.application.serializers import dataset_out
from app.domain.models import Collection, Dataset, DatasetField, DatasetVersion, Record, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
    source: str = ""
    source_description: str = ""
    languages: list[str] = []
    geographic_scope: str = ""
    legal_classification: str = "internal"
    tags: list[str] = []
    notes: str = ""


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "dataset"


@router.get("")
def list_datasets(
    q: Optional[str] = None,
    category: Optional[str] = None,
    collection_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Dataset)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Dataset.name.ilike(like),
                Dataset.description.ilike(like),
                Dataset.source.ilike(like),
            )
        )
    if category:
        query = query.filter(Dataset.category == category)
    if collection_id:
        query = query.filter(Dataset.collection_id == collection_id)
    total = query.count()
    rows = query.order_by(Dataset.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    col_ids = {d.collection_id for d in rows if d.collection_id}
    names = (
        {c.id: c.name for c in db.query(Collection).filter(Collection.id.in_(col_ids)).all()} if col_ids else {}
    )
    items = [dataset_out(d, {"collection_name": names.get(d.collection_id)}) for d in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("")
def create_dataset(
    body: DatasetCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    slug = _slug(body.name)
    base, i = slug, 2
    while db.query(Dataset).filter(Dataset.slug == slug).first():
        slug = f"{base}-{i}"
        i += 1
    d = Dataset(
        slug=slug,
        name=body.name,
        description=body.description,
        category=body.category,
        source=body.source,
        source_description=body.source_description,
        languages=body.languages,
        geographic_scope=body.geographic_scope,
        legal_classification=body.legal_classification,
        tags=body.tags,
        notes=body.notes,
        processing_status="draft",
        owner_id=user.id,
    )
    db.add(d)
    db.flush()
    write_audit(db, actor_id=user.id, action="dataset_create", resource_type="dataset", resource_id=str(d.id))
    db.commit()
    db.refresh(d)
    return dataset_out(d)


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.get(Dataset, dataset_id)
    if not d:
        raise HTTPException(404, "dataset not found")
    write_audit(db, actor_id=user.id, action="dataset_view", resource_type="dataset", resource_id=str(d.id))
    db.commit()
    fields = db.query(DatasetField).filter(DatasetField.dataset_id == d.id).order_by(DatasetField.ordinal).all()
    versions = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == d.id)
        .order_by(DatasetVersion.version_number.desc())
        .all()
    )
    return {
        **dataset_out(d),
        "fields": [
            {
                "name": f.name,
                "physical_type": f.physical_type,
                "semantic_type": f.semantic_type,
                "confidence": f.confidence,
                "approved": f.approved,
                "nullable": f.nullable,
                "description": f.description,
            }
            for f in fields
        ],
        "versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "version_label": v.version_label,
                "record_count": v.record_count,
                "checksum": v.checksum,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.get("/{dataset_id}/records")
def list_records(
    dataset_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.get(Dataset, dataset_id)
    if not d:
        raise HTTPException(404, "dataset not found")
    q = db.query(Record).filter(Record.dataset_id == dataset_id)
    total = q.count()
    rows = q.order_by(Record.row_number).offset((page - 1) * page_size).limit(page_size).all()
    write_audit(db, actor_id=user.id, action="record_view", resource_type="dataset", resource_id=str(dataset_id))
    db.commit()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": str(r.id),
                "row_number": r.row_number,
                "raw": r.raw_payload,
                "language": r.language,
                "content_hash": r.content_hash,
                "duplicate_of": str(r.duplicate_of) if r.duplicate_of else None,
                "duplicate_reason": r.duplicate_reason,
            }
            for r in rows
        ],
    }


@router.get("/{dataset_id}/profile")
def dataset_profile(dataset_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Dataset, dataset_id)
    if not d:
        raise HTTPException(404, "dataset not found")
    return d.data_quality or {}
