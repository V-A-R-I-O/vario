"""audit-log service — write-only sink for business events (slice-07).

Any module can append an audit entry via `record(...)`. It is *fire-and-forget*:
a logging failure must never break the business action that triggered it, so a
failed write is swallowed and logged rather than raised.

Reads live in the admin router (`GET /api/admin/audit-log`), scoped per role
pack. This module only writes.
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("vario.audit_log")


async def record(
    db: AsyncSession,
    *,
    actor_id: Optional[str],
    role_pack: str,
    action_type: str,
    reference_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """Append an audit_log row. Returns the row, or None if the write failed.

    The caller's business transaction is never jeopardised: on any error we roll
    back just this write and return None.
    """
    entry = AuditLog(
        user_id=actor_id,
        role_pack=role_pack,
        action_type=action_type,
        reference_id=reference_id,
        details=details,
    )
    try:
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry
    except Exception:
        logger.exception(
            "audit-log write failed action_type=%s role_pack=%s reference_id=%s",
            action_type,
            role_pack,
            reference_id,
        )
        await db.rollback()
        return None
