from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.application.serializers import entity_out
from app.domain.models import (
    Collection,
    Dataset,
    Entity,
    EntityAlias,
    EntityAttribute,
    EntityCollectionLink,
    EntityRecordLink,
    Record,
    Relationship,
    User,
)
from app.entity_resolution.engine import EntityResolutionEngine
from app.infrastructure.db import get_db
from app.normalization.engine import NormalizationEngine

router = APIRouter(prefix="/entities", tags=["entities"])


class MergeIn(BaseModel):
    into_id: UUID


@router.get("")
def list_entities(
    q: Optional[str] = None,
    entity_type: Optional[str] = None,
    status: Optional[str] = "active",
    collection_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Entity)
    if status:
        query = query.filter(Entity.status == status)
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if collection_id:
        linked = db.query(EntityCollectionLink.entity_id).filter(EntityCollectionLink.collection_id == collection_id)
        query = query.filter(Entity.id.in_(linked))
    if q:
        like = f"%{q}%"
        alias_ids = db.query(EntityAlias.entity_id).filter(EntityAlias.alias.ilike(like))
        query = query.filter(or_(Entity.canonical_name.ilike(like), Entity.id.in_(alias_ids)))
    total = query.count()
    rows = query.order_by(Entity.confidence.desc(), Entity.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for e in rows:
        n_links = db.query(EntityRecordLink).filter(EntityRecordLink.entity_id == e.id).count()
        items.append(entity_out(e, {"record_count": n_links}))
    return {"total": total, "page": page, "items": items}


@router.get("/{entity_id}")
def get_entity(entity_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = db.get(Entity, entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    aliases = db.query(EntityAlias).filter(EntityAlias.entity_id == e.id).all()
    attrs = db.query(EntityAttribute).filter(EntityAttribute.entity_id == e.id).all()
    links = db.query(EntityRecordLink).filter(EntityRecordLink.entity_id == e.id).all()
    rels_out = db.query(Relationship).filter(Relationship.from_entity_id == e.id).all()
    rels_in = db.query(Relationship).filter(Relationship.to_entity_id == e.id).all()

    sources = []
    for link in links:
        rec = db.get(Record, link.record_id)
        ds = db.get(Dataset, link.dataset_id)
        sources.append(
            {
                "record_id": str(link.record_id),
                "dataset_id": str(link.dataset_id),
                "dataset_name": ds.name if ds else "",
                "collection_id": str(link.collection_id) if link.collection_id else None,
                "confidence": link.match_confidence,
                "explain": link.explain_json,
                "raw": rec.raw_payload if rec else {},
                "row_number": rec.row_number if rec else None,
            }
        )

    def rel_out(r, direction: str):
        other_id = r.to_entity_id if direction == "out" else r.from_entity_id
        other = db.get(Entity, other_id)
        return {
            "id": str(r.id),
            "direction": direction,
            "rel_type": r.rel_type,
            "origin": r.origin,
            "confidence": r.confidence,
            "source": r.source,
            "other": entity_out(other) if other else None,
        }

    # provenance spine
    provenance = []
    for a in attrs:
        ds = db.get(Dataset, a.dataset_id) if a.dataset_id else None
        provenance.append(
            {
                "attribute": a.name,
                "value": a.value,
                "origin": a.origin,
                "record_id": str(a.record_id) if a.record_id else None,
                "dataset_id": str(a.dataset_id) if a.dataset_id else None,
                "dataset_name": ds.name if ds else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )

    return entity_out(
        e,
        {
            "aliases": [{"alias": a.alias, "script": a.script, "source": a.source} for a in aliases],
            "attributes": [
                {
                    "name": a.name,
                    "value": a.value,
                    "semantic_type": a.semantic_type,
                    "confidence": a.confidence,
                    "origin": a.origin,
                    "record_id": str(a.record_id) if a.record_id else None,
                    "dataset_id": str(a.dataset_id) if a.dataset_id else None,
                }
                for a in attrs
            ],
            "sources": sources,
            "relationships": [rel_out(r, "out") for r in rels_out] + [rel_out(r, "in") for r in rels_in],
            "provenance": provenance,
            "collections": [
                {
                    "id": str(cl.collection_id),
                    "name": (db.get(Collection, cl.collection_id).name if db.get(Collection, cl.collection_id) else ""),
                    "origin": cl.origin,
                    "confidence": cl.confidence,
                }
                for cl in db.query(EntityCollectionLink).filter(EntityCollectionLink.entity_id == e.id).all()
            ],
        },
    )


@router.post("/resolve")
def resolve(
    dataset_id: Optional[UUID] = None,
    collection_id: Optional[UUID] = None,
    min_confidence: float = 0.55,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run blocking ER over records (optionally scoped to a collection/dataset). Propose only."""
    from app.domain.models import RecordValue

    q = db.query(Record)
    if collection_id:
        q = q.filter(Record.collection_id == collection_id)
    if dataset_id:
        q = q.filter(Record.dataset_id == dataset_id)
    records = q.limit(5000).all()
    packed = []
    for rec in records:
        values = db.query(RecordValue).filter(RecordValue.record_id == rec.id).all()
        attrs = {}
        keys = []
        for v in values:
            attrs[v.semantic_type] = {
                "original_value": v.original_value,
                "normalized_value": v.normalized_value,
                "canonical_value": v.canonical_value,
                "transliterated_value": v.transliterated_value,
                "phonetic_value": v.phonetic_value,
            }
            keys.extend(v.block_keys or [])
        packed.append({"id": str(rec.id), "block_keys": keys, "attributes": attrs})
    proposals = EntityResolutionEngine().propose(packed, min_confidence=min_confidence)
    write_audit(db, actor_id=user.id, action="entity_resolve", resource_type="dataset", resource_id=str(dataset_id or ""), payload={"n": len(proposals)})
    db.commit()
    return {"total": len(proposals), "items": proposals[:200]}


@router.post("/{entity_id}/merge")
def merge(
    entity_id: UUID,
    body: MergeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    src = db.get(Entity, entity_id)
    dst = db.get(Entity, body.into_id)
    if not src or not dst:
        raise HTTPException(404, "entity not found")
    if src.id == dst.id:
        raise HTTPException(400, "cannot merge into self")
    db.query(EntityRecordLink).filter(EntityRecordLink.entity_id == src.id).update({"entity_id": dst.id})
    db.query(EntityAttribute).filter(EntityAttribute.entity_id == src.id).update({"entity_id": dst.id})
    db.query(EntityAlias).filter(EntityAlias.entity_id == src.id).update({"entity_id": dst.id})
    db.query(Relationship).filter(Relationship.from_entity_id == src.id).update({"from_entity_id": dst.id})
    db.query(Relationship).filter(Relationship.to_entity_id == src.id).update({"to_entity_id": dst.id})
    db.add(EntityAlias(entity_id=dst.id, alias=src.canonical_name, source="merge"))
    src.status = "merged"
    src.merged_into_id = dst.id
    dst.confidence = min(1.0, max(dst.confidence, src.confidence) + 0.05)
    write_audit(
        db,
        actor_id=user.id,
        action="entity_merge",
        resource_type="entity",
        resource_id=str(src.id),
        payload={"into": str(dst.id)},
    )
    db.commit()
    return {"ok": True, "merged": str(src.id), "into": str(dst.id)}


@router.post("/{entity_id}/unmerge")
def unmerge(entity_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    src = db.get(Entity, entity_id)
    if not src or src.status != "merged":
        raise HTTPException(400, "entity is not merged")
    src.status = "active"
    src.merged_into_id = None
    write_audit(db, actor_id=user.id, action="entity_unmerge", resource_type="entity", resource_id=str(src.id))
    db.commit()
    return {"ok": True}
