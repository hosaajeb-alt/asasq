from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.collections.scope import visible_collection_ids
from app.domain.models import Entity, Relationship, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{entity_id}")
def neighborhood(
    entity_id: UUID,
    depth: int = Query(1, ge=1, le=3),
    collection_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    root = db.get(Entity, entity_id)
    if not root:
        raise HTTPException(404, "entity not found")

    nodes = {root.id: root}
    edges: list[Relationship] = []
    frontier = {root.id}
    for _ in range(depth):
        nxt = set()
        rq = db.query(Relationship).filter(
            (Relationship.from_entity_id.in_(frontier)) | (Relationship.to_entity_id.in_(frontier))
        )
        if collection_id:
            rq = rq.filter(Relationship.source_collection_id == collection_id)
        rels = rq.all()
        for r in rels:
            edges.append(r)
            for eid in (r.from_entity_id, r.to_entity_id):
                if eid not in nodes:
                    ent = db.get(Entity, eid)
                    if ent:
                        nodes[eid] = ent
                        nxt.add(eid)
        frontier = nxt
        if not frontier:
            break

    # de-dupe edges
    seen = set()
    edge_out = []
    for r in edges:
        if r.id in seen:
            continue
        seen.add(r.id)
        edge_out.append(
            {
                "id": str(r.id),
                "from": str(r.from_entity_id),
                "to": str(r.to_entity_id),
                "rel_type": r.rel_type,
                "origin": r.origin,
                "confidence": r.confidence,
                "source": r.source,
                "source_collection_id": str(r.source_collection_id) if r.source_collection_id else None,
                "derivation_method": r.derivation_method,
            }
        )
    return {
        "root": str(root.id),
        "nodes": [
            {
                "id": str(e.id),
                "label": e.canonical_name,
                "entity_type": e.entity_type,
                "confidence": e.confidence,
                "status": e.status,
            }
            for e in nodes.values()
        ],
        "edges": edge_out,
    }


@router.get("")
def overview(
    limit: int = 80,
    collection_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = visible_collection_ids(db, user, "view")
    q = db.query(Relationship)
    if collection_id:
        q = q.filter(Relationship.source_collection_id == collection_id)
    elif allowed:
        q = q.filter((Relationship.source_collection_id.in_(allowed)) | (Relationship.source_collection_id.is_(None)))
    rels = q.limit(limit * 2).all()
    ids = set()
    for r in rels:
        ids.add(r.from_entity_id)
        ids.add(r.to_entity_id)
    ents = db.query(Entity).filter(Entity.id.in_(ids)).all() if ids else []
    if not ents:
        ents = db.query(Entity).filter(Entity.status == "active").limit(limit).all()
    return {
        "nodes": [
            {
                "id": str(e.id),
                "label": e.canonical_name,
                "entity_type": e.entity_type,
                "confidence": e.confidence,
                "status": e.status,
            }
            for e in ents
        ],
        "edges": [
            {
                "id": str(r.id),
                "from": str(r.from_entity_id),
                "to": str(r.to_entity_id),
                "rel_type": r.rel_type,
                "origin": r.origin,
                "confidence": r.confidence,
                "source": r.source,
                "source_collection_id": str(r.source_collection_id) if r.source_collection_id else None,
                "derivation_method": r.derivation_method,
            }
            for r in rels
            if r.from_entity_id in ids and r.to_entity_id in ids
        ],
    }
