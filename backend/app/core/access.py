"""RBAC now, ABAC-shaped later.

Every authorization decision should go through `evaluate` so attribute-based
rules (classification, purpose, geo) can be added without rewriting callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


ROLE_RANK = {
    "viewer": 10,
    "investigator": 20,
    "analyst": 30,
    "admin": 90,
}


@dataclass
class Principal:
    user_id: str
    role: str
    team_ids: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Resource:
    type: str
    id: Optional[str] = None
    owner_id: Optional[str] = None
    team_id: Optional[str] = None
    classification: str = "internal"
    grants: dict[str, str] = field(default_factory=dict)  # user_id -> perm


# actions
VIEW = "view"
EDIT = "edit"
IMPORT = "import"
EXPORT = "export"
MERGE = "merge"
ADMIN = "admin"
SEARCH = "search"
AUDIT = "audit"


def evaluate(principal: Principal, action: str, resource: Optional[Resource] = None) -> bool:
    rank = ROLE_RANK.get(principal.role, 0)
    if not principal.user_id or rank <= 0:
        return False
    if principal.role == "admin":
        return True

    if action == ADMIN:
        return False
    if action == AUDIT:
        return rank >= ROLE_RANK["analyst"]
    if action == MERGE:
        return rank >= ROLE_RANK["analyst"]
    if action == IMPORT:
        return rank >= ROLE_RANK["analyst"]
    if action == EXPORT:
        return rank >= ROLE_RANK["investigator"]

    if resource is None:
        if action in (VIEW, SEARCH):
            return rank >= ROLE_RANK["viewer"]
        if action == EDIT:
            return rank >= ROLE_RANK["investigator"]
        return False

    if resource.owner_id and resource.owner_id == principal.user_id:
        return True
    if resource.team_id and resource.team_id in principal.team_ids:
        if action == VIEW or action == SEARCH:
            return True
        if action == EDIT:
            return rank >= ROLE_RANK["investigator"]
    if principal.user_id in resource.grants:
        grant = resource.grants[principal.user_id]
        if action == VIEW and grant in ("view", "edit", "owner"):
            return True
        if action == EDIT and grant in ("edit", "owner"):
            return True

    # default: viewers can view non-restricted resources they can list
    if action in (VIEW, SEARCH) and resource.classification in ("public", "internal") and rank >= ROLE_RANK["viewer"]:
        return True
    if action == EDIT and rank >= ROLE_RANK["analyst"] and resource.classification != "restricted":
        return True
    return False


def require(principal: Principal, action: str, resource: Optional[Resource] = None) -> None:
    if not evaluate(principal, action, resource):
        raise PermissionError(f"not allowed to {action} {resource.type if resource else 'resource'}")
