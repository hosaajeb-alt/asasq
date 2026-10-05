from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.application.audit import write_audit
from app.application.serializers import user_out
from app.core.security import hash_password
from app.domain.enums import BUILTIN_SEMANTIC_TYPES
from app.domain.models import AuditLog, SemanticType, Team, TeamMember, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class UserIn(BaseModel):
    email: str
    password: str
    display_name: str
    role: str = "analyst"
    locale: str = "en"


class SemanticIn(BaseModel):
    key: str
    label: str
    description: str = ""
    physical_hint: str = "string"
    privacy_classification: str = "public"
    entity_mappings: list = []
    validation_rules: dict = {}
    normalization_rules: dict = {}
    analyzers: dict = {}


class TeamIn(BaseModel):
    name: str
    description: str = ""


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    rows = db.query(User).order_by(User.created_at).all()
    return {"items": [user_out(u) for u in rows]}


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "email exists")
    u = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
        locale=body.locale,
    )
    db.add(u)
    write_audit(db, actor_id=admin.id, action="permission_change", resource_type="user", payload={"email": u.email, "role": u.role})
    db.commit()
    db.refresh(u)
    return user_out(u)


@router.get("/teams")
def list_teams(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Team).all()
    items = []
    for t in rows:
        members = db.query(TeamMember).filter(TeamMember.team_id == t.id).all()
        items.append(
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "members": [{"user_id": str(m.user_id), "role": m.role} for m in members],
            }
        )
    return {"items": items}


@router.post("/teams")
def create_team(body: TeamIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    t = Team(name=body.name, description=body.description)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": str(t.id), "name": t.name}


@router.get("/semantic-types")
def list_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(SemanticType).order_by(SemanticType.key).all()
    return {
        "items": [
            {
                "key": r.key,
                "label": r.label,
                "description": r.description,
                "physical_hint": r.physical_hint,
                "privacy_classification": r.privacy_classification,
                "entity_mappings": r.entity_mappings,
                "validation_rules": r.validation_rules,
                "normalization_rules": r.normalization_rules,
                "analyzers": r.analyzers,
                "is_system": r.is_system,
            }
            for r in rows
        ],
        "builtin": BUILTIN_SEMANTIC_TYPES,
    }


@router.post("/semantic-types")
def create_type(body: SemanticIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if db.get(SemanticType, body.key):
        raise HTTPException(409, "exists")
    st = SemanticType(
        key=body.key,
        label=body.label,
        description=body.description,
        physical_hint=body.physical_hint,
        privacy_classification=body.privacy_classification,
        entity_mappings=body.entity_mappings,
        validation_rules=body.validation_rules,
        normalization_rules=body.normalization_rules,
        analyzers=body.analyzers,
        is_system=False,
        created_by=admin.id,
    )
    db.add(st)
    write_audit(db, actor_id=admin.id, action="schema_change", resource_type="semantic_type", resource_id=body.key)
    db.commit()
    return {"ok": True, "key": body.key}


@router.get("/audit")
def list_audit(
    action: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            {
                "id": str(a.id),
                "actor_id": str(a.actor_id) if a.actor_id else None,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "ip": a.ip,
                "payload": a.payload,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ],
    }


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import func

    from app.domain.models import Dataset, Entity, Investigation, Record, SearchDoc

    return {
        "users": db.query(func.count(User.id)).scalar(),
        "datasets": db.query(func.count(Dataset.id)).scalar(),
        "records": db.query(func.count(Record.id)).scalar() or 0,
        "entities": db.query(func.count(Entity.id)).scalar() or 0,
        "investigations": db.query(func.count(Investigation.id)).scalar() or 0,
        "search_docs": db.query(func.count(SearchDoc.id)).scalar() or 0,
        "architecture": {
            "raw_layer": "object-store (Phase 1: local volume + PG payload)",
            "normalized_layer": "record_values",
            "entity_layer": "entities + relationships",
            "search_layer": "search_docs (OpenSearch in Phase 3)",
            "analytics_layer": "PostgreSQL (ClickHouse in Phase 6)",
        },
    }
