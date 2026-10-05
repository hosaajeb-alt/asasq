from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models import (
    Collection,
    CollectionIndex,
    Dataset,
    EntityCollectionLink,
    FaceEmbedding,
    ImageAsset,
    ImportJob,
    Record,
    SearchDoc,
)


def refresh_counts(db: Session, collection: Collection) -> Collection:
    cid = collection.id
    collection.dataset_count = db.query(func.count(Dataset.id)).filter(Dataset.collection_id == cid).scalar() or 0
    collection.record_count = db.query(func.count(Record.id)).filter(Record.collection_id == cid).scalar() or 0
    collection.entity_count = (
        db.query(func.count(EntityCollectionLink.id)).filter(EntityCollectionLink.collection_id == cid).scalar() or 0
    )
    collection.image_count = db.query(func.count(ImageAsset.id)).filter(ImageAsset.collection_id == cid).scalar() or 0
    collection.embedding_count = (
        db.query(func.count(FaceEmbedding.id)).filter(FaceEmbedding.collection_id == cid).scalar() or 0
    )
    langs: Counter[str] = Counter()
    countries: Counter[str] = Counter()
    for ds in db.query(Dataset).filter(Dataset.collection_id == cid).all():
        for lg in ds.languages or []:
            langs[lg] += ds.record_count or 0
        if ds.geographic_scope:
            countries[ds.geographic_scope] += 1
    collection.language_distribution = dict(langs)
    collection.country_distribution = dict(countries)
    last = (
        db.query(ImportJob)
        .filter(ImportJob.collection_id == cid, ImportJob.status == "completed")
        .order_by(ImportJob.finished_at.desc())
        .first()
    )
    if last and last.finished_at:
        collection.last_import_at = last.finished_at
    return collection


def stats_payload(db: Session, collection: Collection) -> dict:
    refresh_counts(db, collection)
    indexes = db.query(CollectionIndex).filter(CollectionIndex.collection_id == collection.id).all()
    dupes = (
        db.query(func.count(Record.id))
        .filter(Record.collection_id == collection.id, Record.duplicate_of.isnot(None))
        .scalar()
        or 0
    )
    return {
        "records": collection.record_count,
        "datasets": collection.dataset_count,
        "entities": collection.entity_count,
        "images": collection.image_count,
        "faces": collection.embedding_count,
        "embeddings": collection.embedding_count,
        "languages": collection.language_distribution,
        "countries": collection.country_distribution,
        "duplicates": dupes,
        "last_import": collection.last_import_at.isoformat() if collection.last_import_at else None,
        "index_status": "healthy"
        if indexes and all(i.status == "healthy" for i in indexes)
        else ("empty" if not indexes else "degraded"),
        "indexes": [
            {
                "kind": i.kind,
                "status": i.status,
                "backend": i.backend,
                "alias": i.alias,
                "document_count": i.document_count,
                "last_rebuild_at": i.last_rebuild_at.isoformat() if i.last_rebuild_at else None,
            }
            for i in indexes
        ],
        "search_docs": db.query(func.count(SearchDoc.id)).filter(SearchDoc.collection_id == collection.id).scalar() or 0,
    }
