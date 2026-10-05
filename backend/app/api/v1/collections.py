from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.application.collection_stats import refresh_counts, stats_payload
from app.application.serializers import dataset_out, entity_out
from app.collections.index_manager import provision, rebuild
from app.collections.scope import require_collection, resolve_collection_ids, visible_collection_ids
from app.domain.enums import DEFAULT_INDEX_POLICY
from app.domain.models import (
    Collection,
    CollectionGrant,
    CollectionIndex,
    CollectionVersion,
    Dataset,
    Entity,
    EntityCollectionLink,
    ImageAsset,
    ImportJob,
    User,
    Workspace,
)
from app.infrastructure.db import get_db
from app.vector.face import run_pipeline
from app.vector.store import get_face_store

router = APIRouter(prefix="/collections", tags=["collections"])


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "collection"


def collection_out(c: Collection, extra: dict | None = None) -> dict:
    data = {
        "id": str(c.id),
        "workspace_id": str(c.workspace_id) if c.workspace_id else None,
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "source": c.source,
        "source_type": c.source_type,
        "category": c.category,
        "status": c.status,
        "visibility": c.visibility,
        "owner_id": str(c.owner_id) if c.owner_id else None,
        "created_by": str(c.created_by) if c.created_by else None,
        "version": c.version,
        "record_count": c.record_count,
        "entity_count": c.entity_count,
        "dataset_count": c.dataset_count,
        "image_count": c.image_count,
        "embedding_count": c.embedding_count,
        "language_distribution": c.language_distribution or {},
        "country_distribution": c.country_distribution or {},
        "tags": c.tags or [],
        "metadata": c.extra_metadata or {},
        "provenance": c.provenance or {},
        "retention_policy": c.retention_policy or {},
        "index_policy": c.index_policy or {},
        "dedup_policy": c.dedup_policy or {},
        "normalization_policy": c.normalization_policy or {},
        "access_policy": c.access_policy or {},
        "languages": c.languages or [],
        "geographic_scope": c.geographic_scope,
        "legal_classification": c.legal_classification,
        "last_import_at": c.last_import_at.isoformat() if c.last_import_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
    if extra:
        data.update(extra)
    return data


class CollectionIn(BaseModel):
    name: str
    description: str = ""
    source: str = ""
    source_type: str = "custom"
    category: str = "custom"
    visibility: str = "team"
    languages: list[str] = Field(default_factory=list)
    geographic_scope: str = ""
    tags: list[str] = Field(default_factory=list)
    legal_classification: str = "internal"
    retention_policy: dict[str, Any] = Field(default_factory=dict)
    index_policy: dict[str, Any] = Field(default_factory=dict)
    dedup_policy: dict[str, Any] = Field(default_factory=dict)
    normalization_policy: dict[str, Any] = Field(default_factory=dict)
    access_policy: dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = None


class CollectionPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    languages: Optional[list[str]] = None
    geographic_scope: Optional[str] = None
    tags: Optional[list[str]] = None
    legal_classification: Optional[str] = None
    index_policy: Optional[dict[str, Any]] = None
    dedup_policy: Optional[dict[str, Any]] = None
    normalization_policy: Optional[dict[str, Any]] = None
    retention_policy: Optional[dict[str, Any]] = None
    access_policy: Optional[dict[str, Any]] = None


class GrantIn(BaseModel):
    user_id: UUID
    permission: str


def _default_workspace(db: Session, user: User) -> Workspace:
    ws = db.query(Workspace).first()
    if ws:
        return ws
    ws = Workspace(name="OSINT", slug="osint", description="Default workspace", owner_id=user.id)
    db.add(ws)
    db.flush()
    return ws


@router.get("")
def list_collections(
    q: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ids = visible_collection_ids(db, user, "view")
    query = db.query(Collection).filter(Collection.id.in_(ids) if ids else Collection.id == None)  # noqa: E711
    if not ids:
        return {"total": 0, "page": page, "items": []}
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Collection.name.ilike(like), Collection.description.ilike(like), Collection.slug.ilike(like)))
    if status:
        query = query.filter(Collection.status == status)
    else:
        query = query.filter(Collection.status != "deleted")
    total = query.count()
    rows = query.order_by(Collection.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "items": [collection_out(c) for c in rows]}


@router.post("")
def create_collection(
    body: CollectionIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("admin", "analyst", "investigator"):
        raise HTTPException(403, "insufficient role")
    ws = _default_workspace(db, user)
    slug = _slug(body.name)
    base, i = slug, 2
    while db.query(Collection).filter(Collection.slug == slug).first():
        slug = f"{base}-{i}"
        i += 1
    policy = dict(DEFAULT_INDEX_POLICY)
    policy.update(body.index_policy or {})
    c = Collection(
        workspace_id=UUID(body.workspace_id) if body.workspace_id else ws.id,
        name=body.name,
        slug=slug,
        description=body.description,
        source=body.source,
        source_type=body.source_type,
        category=body.category,
        status="active",
        visibility=body.visibility,
        owner_id=user.id,
        created_by=user.id,
        languages=body.languages,
        geographic_scope=body.geographic_scope,
        tags=body.tags,
        legal_classification=body.legal_classification,
        retention_policy=body.retention_policy or {"mode": "indefinite"},
        index_policy=policy,
        dedup_policy=body.dedup_policy or {"scope": "collection", "auto_merge": False},
        normalization_policy=body.normalization_policy or {},
        access_policy=body.access_policy or {"default": "team"},
        provenance={"created_by": str(user.id)},
    )
    db.add(c)
    db.flush()
    provision(db, c)
    db.add(CollectionVersion(collection_id=c.id, version_number=1, version_label="v1", snapshot={"created": True}, created_by=user.id))
    write_audit(
        db,
        actor_id=user.id,
        action="collection_created",
        resource_type="collection",
        resource_id=str(c.id),
        payload={"slug": slug},
    )
    db.commit()
    db.refresh(c)
    return collection_out(c)


@router.get("/{collection_id}")
def get_collection(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = require_collection(db, user, collection_id, "view")
    refresh_counts(db, c)
    db.commit()
    return collection_out(c, {"stats": stats_payload(db, c)})


@router.patch("/{collection_id}")
def patch_collection(
    collection_id: UUID,
    body: CollectionPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = require_collection(db, user, collection_id, "edit")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] == "deleted":
        raise HTTPException(400, "use DELETE for lifecycle deletion")
    for k, v in data.items():
        setattr(c, k, v)
    if "index_policy" in data:
        provision(db, c)
    write_audit(db, actor_id=user.id, action="collection_updated", resource_type="collection", resource_id=str(c.id))
    db.commit()
    db.refresh(c)
    return collection_out(c)


@router.delete("/{collection_id}")
def delete_collection(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Soft-delete. Large collections are detached asynchronously — never a huge sync wipe."""
    c = require_collection(db, user, collection_id, "delete")
    c.status = "deleted"
    c.deleted_at = datetime.now(timezone.utc)
    write_audit(db, actor_id=user.id, action="collection_deleted", resource_type="collection", resource_id=str(c.id))
    db.commit()
    return {"ok": True, "status": "deleted", "cleanup": "background"}


@router.get("/{collection_id}/datasets")
def collection_datasets(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "view")
    rows = db.query(Dataset).filter(Dataset.collection_id == collection_id).order_by(Dataset.updated_at.desc()).all()
    return {"items": [dataset_out(d) for d in rows]}


@router.get("/{collection_id}/stats")
def collection_stats(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = require_collection(db, user, collection_id, "view")
    return stats_payload(db, c)


@router.get("/{collection_id}/entities")
def collection_entities(
    collection_id: UUID,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_collection(db, user, collection_id, "view")
    ids = db.query(EntityCollectionLink.entity_id).filter(EntityCollectionLink.collection_id == collection_id)
    query = db.query(Entity).filter(Entity.id.in_(ids), Entity.status == "active")
    if q:
        query = query.filter(Entity.canonical_name.ilike(f"%{q}%"))
    total = query.count()
    rows = query.order_by(Entity.confidence.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [entity_out(e) for e in rows]}


@router.get("/{collection_id}/indexes")
def list_indexes(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = require_collection(db, user, collection_id, "view")
    provision(db, c)
    db.commit()
    rows = db.query(CollectionIndex).filter(CollectionIndex.collection_id == collection_id).all()
    return {
        "items": [
            {
                "kind": i.kind,
                "status": i.status,
                "backend": i.backend,
                "alias": i.alias,
                "document_count": i.document_count,
                "last_rebuild_at": i.last_rebuild_at.isoformat() if i.last_rebuild_at else None,
            }
            for i in rows
        ]
    }


@router.post("/{collection_id}/indexes/rebuild")
def rebuild_indexes(
    collection_id: UUID,
    kind: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_collection(db, user, collection_id, "manage")
    result = rebuild(db, collection_id, kind)
    write_audit(db, actor_id=user.id, action="index_rebuilt", resource_type="collection", resource_id=str(collection_id), payload=result)
    db.commit()
    return result


@router.get("/{collection_id}/versions")
def list_versions(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "view")
    rows = (
        db.query(CollectionVersion)
        .filter(CollectionVersion.collection_id == collection_id)
        .order_by(CollectionVersion.version_number.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "version_label": v.version_label,
                "snapshot": v.snapshot,
                "notes": v.notes,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in rows
        ]
    }


@router.post("/{collection_id}/versions")
def snapshot(
    collection_id: UUID,
    notes: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = require_collection(db, user, collection_id, "edit")
    refresh_counts(db, c)
    n = (db.query(CollectionVersion).filter(CollectionVersion.collection_id == c.id).count() or 0) + 1
    snap = CollectionVersion(
        collection_id=c.id,
        version_number=n,
        version_label=f"v{n}",
        snapshot=stats_payload(db, c),
        notes=notes,
        created_by=user.id,
    )
    c.version = n
    db.add(snap)
    db.commit()
    return {"version": n}


@router.get("/{collection_id}/permissions")
def list_grants(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "view")
    rows = db.query(CollectionGrant).filter(CollectionGrant.collection_id == collection_id).all()
    return {"items": [{"user_id": str(g.user_id), "permission": g.permission} for g in rows]}


@router.post("/{collection_id}/permissions")
def add_grant(collection_id: UUID, body: GrantIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "manage")
    db.add(CollectionGrant(collection_id=collection_id, user_id=body.user_id, permission=body.permission, created_by=user.id))
    write_audit(db, actor_id=user.id, action="permission_change", resource_type="collection", resource_id=str(collection_id))
    db.commit()
    return {"ok": True}


@router.get("/{collection_id}/images")
def list_images(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "view")
    rows = db.query(ImageAsset).filter(ImageAsset.collection_id == collection_id).limit(100).all()
    return {
        "items": [
            {
                "id": str(i.id),
                "uri": i.uri,
                "quality": i.quality,
                "entity_id": str(i.entity_id) if i.entity_id else None,
                "dataset_id": str(i.dataset_id) if i.dataset_id else None,
            }
            for i in rows
        ]
    }


@router.get("/{collection_id}/imports")
def list_imports(collection_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_collection(db, user, collection_id, "view")
    rows = db.query(ImportJob).filter(ImportJob.collection_id == collection_id).order_by(ImportJob.created_at.desc()).limit(50).all()
    from app.application.serializers import job_out

    return {"items": [job_out(j) for j in rows]}


@router.post("/{collection_id}/search")
def collection_search(
    collection_id: UUID,
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_collection(db, user, collection_id, "search")
    from app.api.v1.search import SearchIn, search as run_search

    payload = SearchIn(
        q=body.get("q") or body.get("query") or "",
        mode=body.get("mode") or "balanced",
        entity_type=body.get("entity_type"),
        dataset_id=body.get("dataset_id"),
        language=body.get("language"),
        semantic_type=body.get("semantic_type"),
        page=body.get("page") or 1,
        page_size=body.get("page_size") or 25,
        scope={"collections": [str(collection_id)], "datasets": body.get("datasets") or []},
    )
    return run_search(payload, request, db, user)


@router.post("/{collection_id}/face-search")
async def collection_face_search(
    collection_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    top_k: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_collection(db, user, collection_id, "search")
    c = db.get(Collection, collection_id)
    policy = (c.index_policy or {}) if c else {}
    if policy.get("face_search") is False:
        raise HTTPException(400, "face search is disabled for this collection")
    raw = await file.read()
    pipe = run_pipeline(raw)
    store = get_face_store(db)
    hits = store.search(pipe["vector"], [collection_id], top_k=top_k, min_score=0.15)
    # hydrate names
    from app.domain.models import Entity, Dataset

    for h in hits:
        if h.get("entity_id"):
            ent = db.get(Entity, UUID(h["entity_id"]))
            h["entity_name"] = ent.canonical_name if ent else None
            h["entity_type"] = ent.entity_type if ent else None
        if h.get("dataset_id"):
            ds = db.get(Dataset, UUID(h["dataset_id"]))
            h["dataset_name"] = ds.name if ds else None
        h["collection_name"] = c.name if c else None
    write_audit(
        db,
        actor_id=user.id,
        action="face_search_executed",
        resource_type="collection",
        resource_id=str(collection_id),
        payload={"hits": len(hits), "quality": pipe["quality"]},
        ip=request.client.host if request.client else "",
    )
    db.commit()
    return {
        "pipeline": {k: v for k, v in pipe.items() if k != "vector"},
        "scope": {"collections": [str(collection_id)]},
        "identity_asserted": False,
        "review": "human_required",
        "total": len(hits),
        "items": hits,
    }
