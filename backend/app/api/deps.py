from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.access import Principal
from app.core.security import decode_token
from app.domain.models import TeamMember, User
from app.infrastructure.db import get_db

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
    x_nexus_token: Optional[str] = Header(default=None, alias="X-Nexus-Token"),
) -> User:
    token = None
    if creds:
        token = creds.credentials
    elif x_nexus_token:
        token = x_nexus_token
    elif request.cookies.get("nexus_token"):
        token = request.cookies.get("nexus_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        payload = decode_token(token, "access")
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="inactive user")
    return user


def get_principal(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Principal:
    teams = db.query(TeamMember.team_id).filter(TeamMember.user_id == user.id).all()
    return Principal(
        user_id=str(user.id),
        role=user.role,
        team_ids=[str(t[0]) for t in teams],
    )


def require_roles(*roles: str):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return _inner
