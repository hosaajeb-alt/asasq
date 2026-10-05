"""Logical Collection indexes. Shared infrastructure, collection_id partitions.

A Collection rebuild never rebuilds the global platform.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.enums import DEFAULT_INDEX_POLICY
from app.domain.models import Collection, CollectionIndex, FaceEmbedding, SearchDoc


KIND_MAP = {
    "text_search": "text",
    "metadata_search": "metadata",
    "vector_search": "vector",
    "face_search": "face",
    "graph_index": "graph",
    "fuzzy_search": "text",
    "phonetic_search": "text",
}


def provision(db: Session, collection: Collection) -> list[CollectionIndex]:
    policy = collection.index_policy or DEFAULT_INDEX_POLICY
    kinds = []
    for key, enabled in policy.items():
        if enabled and key in KIND_MAP:
            k = KIND_MAP[key]
            if k not in kinds:
                kinds.append(k)
    if "entity" not in kinds:
        kinds.append("entity")
    existing = {i.kind: i for i in db.query(CollectionIndex).filter(CollectionIndex.collection_id == collection.id).all()}
    out = []
    for kind in kinds:
        row = existing.get(kind)
        if not row:
            row = CollectionIndex(
                collection_id=collection.id,
                kind=kind,
                status="healthy",
                backend="projection" if kind != "face" else "face-store",
                alias=f"col-{collection.slug}-{kind}",
            )
            db.add(row)
        out.append(row)
    return out


def rebuild(db: Session, collection_id: UUID, kind: str | None = None) -> dict:
    """Rebuild only this collection's logical indexes."""
    col = db.get(Collection, collection_id)
    if not col:
        raise ValueError("collection not found")
    indexes = provision(db, col)
    now = datetime.now(timezone.utc)
    rebuilt = []
    for idx in indexes:
        if kind and idx.kind != kind:
            continue
        if idx.kind in ("text", "metadata"):
            idx.document_count = (
                db.query(func.count(SearchDoc.id)).filter(SearchDoc.collection_id == collection_id).scalar() or 0
            )
        elif idx.kind == "face":
            idx.document_count = (
                db.query(func.count(FaceEmbedding.id)).filter(FaceEmbedding.collection_id == collection_id).scalar()
                or 0
            )
        idx.status = "healthy"
        idx.last_rebuild_at = now
        rebuilt.append(idx.kind)
    db.flush()
    return {"collection_id": str(collection_id), "rebuilt": rebuilt, "at": now.isoformat()}
