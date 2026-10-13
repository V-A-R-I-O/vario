"""Admin console API (slice-07).

The admin shell: every route here requires an admin role (via `require_admin`)
and is scoped to the admin's own role pack. Intent/template CRUD lands in later
slices; this slice ships the audit-log read endpoint.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import AuditLogEntry, AuditLogListResponse
from app.services.admin_guard import AdminContext, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


def _parse_iso(value: str, field: str) -> datetime:
    """Parse an ISO 8601 date/datetime query param, or 422 on malformed input."""
    try:
        # Accept trailing 'Z' (UTC) which fromisoformat rejects before 3.11-ish.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid ISO 8601 value for '{field}'")


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    admin: AdminContext = Depends(require_admin),
    action_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Scope to the admin's own role pack — never another pack's entries.
    base = select(AuditLog).where(AuditLog.role_pack == admin.role_pack)

    if action_type:
        base = base.where(AuditLog.action_type == action_type)
    if actor_id:
        base = base.where(AuditLog.user_id == actor_id)
    if from_:
        base = base.where(AuditLog.created_at >= _parse_iso(from_, "from"))
    if to:
        base = base.where(AuditLog.created_at <= _parse_iso(to, "to"))

    # Total matching the filters (before pagination).
    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    # Page of entries, newest first, with the actor's name joined in.
    rows_result = await db.execute(
        base.add_columns(User.full_name)
        .outerjoin(User, AuditLog.user_id == User.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    entries = [
        AuditLogEntry(
            id=log.log_id,
            actor_id=log.user_id,
            actor_name=actor_name,
            action_type=log.action_type,
            reference_id=log.reference_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log, actor_name in rows_result.all()
    ]

    return AuditLogListResponse(role_pack=admin.role_pack, total=total, entries=entries)
