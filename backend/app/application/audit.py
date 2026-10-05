from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import AuditLog


def write_audit(
    db: Session,
    *,
    actor_id: Optional[UUID],
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    ip: str = "",
    user_agent: str = "",
    payload: Optional[dict[str, Any]] = None,
    collection_id: Optional[UUID] = None,
    dataset_id: Optional[UUID] = None,
    request_id: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            ip=ip or "",
            user_agent=(user_agent or "")[:400],
            payload=payload or {},
            collection_id=collection_id,
            dataset_id=dataset_id,
            request_id=request_id,
            result_summary=str((payload or {}).get("hits", ""))[:200],
        )
    )
