from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.models import Dataset, Entity, Evidence, Record, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("")
def list_evidence(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Evidence).order_by(Evidence.created_at.desc()).limit(200).all()
    items = []
    for e in rows:
        ds = db.get(Dataset, e.dataset_id) if e.dataset_id else None
        ent = db.get(Entity, e.entity_id) if e.entity_id else None
        items.append(
            {
                "id": str(e.id),
                "title": e.title,
                "notes": e.notes,
                "origin": e.origin,
                "investigation_id": str(e.investigation_id) if e.investigation_id else None,
                "record_id": str(e.record_id) if e.record_id else None,
                "dataset_id": str(e.dataset_id) if e.dataset_id else None,
                "dataset_name": ds.name if ds else None,
                "entity_id": str(e.entity_id) if e.entity_id else None,
                "entity_name": ent.canonical_name if ent else None,
                "object_uri": e.object_uri,
                "captured_at": e.captured_at.isoformat() if e.captured_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return {"items": items}


@router.get("/{evidence_id}")
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = db.get(Evidence, evidence_id)
    if not e:
        raise HTTPException(404, "not found")
    rec = db.get(Record, e.record_id) if e.record_id else None
    ds = db.get(Dataset, e.dataset_id) if e.dataset_id else None
    ent = db.get(Entity, e.entity_id) if e.entity_id else None
    spine = {
        "evidence": str(e.id),
        "entity": {"id": str(ent.id), "name": ent.canonical_name} if ent else None,
        "record": {"id": str(rec.id), "raw": rec.raw_payload} if rec else None,
        "dataset": {"id": str(ds.id), "name": ds.name, "source": ds.source} if ds else None,
        "import": ds.provenance if ds else None,
        "captured_at": e.captured_at.isoformat() if e.captured_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "origin": e.origin,
    }
    return spine
