"""Collection scope resolver — authorization happens here, before any index fan-out."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.models import Collection, CollectionGrant, User


def _is_admin(user: User) -> bool:
    return user.role == "admin"


def visible_collection_ids(db: Session, user: User, permission: str = "view") -> list[UUID]:
    q = db.query(Collection).filter(Collection.status != "deleted")
    rows = q.all()
    if _is_admin(user):
        return [c.id for c in rows]
    grants = {
        (g.collection_id, g.permission)
        for g in db.query(CollectionGrant).filter(CollectionGrant.user_id == user.id).all()
    }
    out = []
    for c in rows:
        if c.owner_id == user.id or c.created_by == user.id:
            out.append(c.id)
            continue
        if (c.id, permission) in grants or (c.id, "admin") in grants or (c.id, "manage") in grants:
            out.append(c.id)
            continue
        if permission in ("view", "search") and c.visibility in ("workspace", "team") and c.legal_classification in (
            "public",
            "internal",
        ):
            out.append(c.id)
    return out


def resolve_collection_ids(
    db: Session,
    user: User,
    requested: list[str] | None,
    permission: str = "search",
) -> list[UUID]:
    allowed = visible_collection_ids(db, user, permission)
    allowed_set = set(allowed)
    if not requested or requested == ["*"] or (len(requested) == 1 and requested[0] == "*"):
        return allowed
    resolved: list[UUID] = []
    for raw in requested:
        if not raw or raw == "*":
            continue
        col = None
        try:
            cid = UUID(raw)
            col = db.get(Collection, cid)
        except ValueError:
            col = db.query(Collection).filter(Collection.slug == raw).first()
        if not col or col.status == "deleted":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"collection not found: {raw}")
        if col.id not in allowed_set:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"not allowed to {permission} collection {col.slug}")
        resolved.append(col.id)
    return resolved


def require_collection(db: Session, user: User, collection_id: UUID, permission: str) -> Collection:
    col = db.get(Collection, collection_id)
    if not col or col.status == "deleted":
        raise HTTPException(404, "collection not found")
    allowed = set(visible_collection_ids(db, user, permission))
    if col.id not in allowed and not _is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"not allowed to {permission} this collection")
    return col
