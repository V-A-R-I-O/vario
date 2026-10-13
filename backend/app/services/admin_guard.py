"""admin-guard — reusable authorization for the admin console (slice-07).

Sits on top of the gateway's JWT middleware (slice-03), which has already
authenticated the request and put the role claim on `request.state`. This guard
turns that claim into an `AdminContext` and rejects non-admins with 403.

Every admin request is scoped to the admin's *own* role pack: an `hr_admin`
only ever sees `hr` data. The role → role_pack mapping lives here so admin
routers never hard-code it.
"""
from dataclasses import dataclass

from fastapi import HTTPException, Request

# JWT admin role claim → the role pack it administers.
ADMIN_ROLE_TO_PACK = {
    "hr_admin": "hr",
    "it_admin": "it",
    "admissions_admin": "admissions",
}


@dataclass
class AdminContext:
    """The authenticated admin, resolved from the JWT role claim."""

    user_id: str
    role: str
    role_pack: str
    email: str | None = None


def require_admin(request: Request) -> AdminContext:
    """FastAPI dependency: allow only admin roles; expose the admin's role pack.

    Raises 403 for any non-admin (or missing) role. The JWT itself is verified
    upstream by the gateway middleware; a missing/invalid token is already a 401
    before we get here.
    """
    role = getattr(request.state, "role", None)
    role_pack = ADMIN_ROLE_TO_PACK.get(role)
    if role_pack is None:
        raise HTTPException(status_code=403, detail="Admin access required")

    return AdminContext(
        user_id=getattr(request.state, "user_id", None),
        role=role,
        role_pack=role_pack,
        email=getattr(request.state, "email", None),
    )
