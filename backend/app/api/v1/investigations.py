from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.application.serializers import investigation_out
from app.domain.models import Evidence, Investigation, InvestigationItem, Note, TimelineEvent, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/investigations", tags=["investigations"])


class CaseIn(BaseModel):
    title: str
    summary: str = ""
    classification: str = "internal"
    tags: list[str] = []


class ItemIn(BaseModel):
    item_type: str
    item_id: str
    label: str = ""
    meta: dict = {}


class NoteIn(BaseModel):
    body: str


class EvidenceIn(BaseModel):
    title: str
    notes: str = ""
    record_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    entity_id: Optional[UUID] = None
    origin: str = "observed"


@router.get("")
def list_cases(
    q: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Investigation)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Investigation.title.ilike(like), Investigation.summary.ilike(like)))
    if status:
        query = query.filter(Investigation.status == status)
    total = query.count()
    rows = query.order_by(Investigation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for c in rows:
        n_items = db.query(InvestigationItem).filter(InvestigationItem.investigation_id == c.id).count()
        items.append({**investigation_out(c), "item_count": n_items})
    return {"total": total, "page": page, "items": items}


@router.post("")
def create_case(body: CaseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = Investigation(
        title=body.title,
        summary=body.summary,
        classification=body.classification,
        tags=body.tags,
        owner_id=user.id,
        status="open",
    )
    db.add(c)
    db.flush()
    write_audit(db, actor_id=user.id, action="case_creation", resource_type="investigation", resource_id=str(c.id))
    db.commit()
    db.refresh(c)
    return investigation_out(c)


@router.get("/{case_id}")
def get_case(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    items = db.query(InvestigationItem).filter(InvestigationItem.investigation_id == c.id).all()
    notes = db.query(Note).filter(Note.investigation_id == c.id).order_by(Note.created_at.desc()).all()
    evidence = db.query(Evidence).filter(Evidence.investigation_id == c.id).all()
    timeline = (
        db.query(TimelineEvent).filter(TimelineEvent.investigation_id == c.id).order_by(TimelineEvent.occurred_at).all()
    )
    return {
        **investigation_out(c),
        "items": [
            {
                "id": str(i.id),
                "item_type": i.item_type,
                "item_id": i.item_id,
                "label": i.label,
                "meta": i.meta,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
        "notes": [
            {
                "id": str(n.id),
                "body": n.body,
                "author_id": str(n.author_id) if n.author_id else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
        "evidence": [
            {
                "id": str(e.id),
                "title": e.title,
                "notes": e.notes,
                "origin": e.origin,
                "record_id": str(e.record_id) if e.record_id else None,
                "dataset_id": str(e.dataset_id) if e.dataset_id else None,
                "entity_id": str(e.entity_id) if e.entity_id else None,
                "captured_at": e.captured_at.isoformat() if e.captured_at else None,
            }
            for e in evidence
        ],
        "timeline": [
            {
                "id": str(t.id),
                "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None,
                "title": t.title,
                "body": t.body,
                "origin": t.origin,
                "entity_id": str(t.entity_id) if t.entity_id else None,
            }
            for t in timeline
        ],
    }


@router.patch("/{case_id}")
def patch_case(case_id: UUID, body: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    for k in ("title", "summary", "status", "classification"):
        if k in body:
            setattr(c, k, body[k])
    db.commit()
    db.refresh(c)
    return investigation_out(c)


@router.post("/{case_id}/items")
def add_item(case_id: UUID, body: ItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    item = InvestigationItem(
        investigation_id=c.id,
        item_type=body.item_type,
        item_id=body.item_id,
        label=body.label,
        meta=body.meta,
        added_by=user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}


@router.post("/{case_id}/notes")
def add_note(case_id: UUID, body: NoteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    n = Note(investigation_id=c.id, body=body.body, author_id=user.id)
    db.add(n)
    db.commit()
    return {"id": str(n.id)}


@router.post("/{case_id}/evidence")
def add_evidence(case_id: UUID, body: EvidenceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    e = Evidence(
        investigation_id=c.id,
        title=body.title,
        notes=body.notes,
        record_id=body.record_id,
        dataset_id=body.dataset_id,
        entity_id=body.entity_id,
        origin=body.origin,
        created_by=user.id,
    )
    db.add(e)
    db.commit()
    return {"id": str(e.id)}
