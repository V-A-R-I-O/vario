"""Admin console API (slice-07).

The admin shell: every route here requires an admin role (via `require_admin`)
and is scoped to the admin's own role pack. Intent/template CRUD lands in later
slices; this slice ships the audit-log read endpoint.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.admin import (
    AuditLogEntry,
    AuditLogListResponse,
    AdminConversationSummary,
    AdminConversationListResponse,
    AdminMessageOut,
    AdminTranscriptResponse,
)
from app.services.admin_guard import AdminContext, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


def _parse_iso(value: str, field: str) -> datetime:
    """Parse an ISO 8601 date/datetime query param, or 422 on malformed input."""
    try:
        # Accept trailing 'Z' (UTC) which fromisoformat rejects before 3.11-ish.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid ISO 8601 value for '{field}'")


def _parse_iso_to(value: str, field: str = "to") -> datetime:
    """Parse an ISO 8601 date/datetime query param, making plain YYYY-MM-DD inclusive of that day."""
    dt = _parse_iso(value, field)
    if len(value.strip()) == 10:
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


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
        base = base.where(AuditLog.created_at <= _parse_iso_to(to, "to"))

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


# --- Conversation Logs (slice-11, FR-19) -----------------------------------


@router.get("/conversations", response_model=AdminConversationListResponse)
async def get_admin_conversations(
    admin: AdminContext = Depends(require_admin),
    actor_id: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversations handled by the admin's role pack, most recent first.
    Role pack is strictly scoped from JWT.
    """
    # Correlated subquery for message count
    msg_count_sub = (
        select(func.count(Message.message_id))
        .where(Message.conversation_id == Conversation.conversation_id)
        .scalar_subquery()
    )

    # Correlated subquery for last intent detected by bot
    last_intent_sub = (
        select(Message.intent_name)
        .where(
            Message.conversation_id == Conversation.conversation_id,
            Message.intent_name.isnot(None),
        )
        .order_by(Message.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )

    # Base query for count (outerjoin User for actor name/email search - N15)
    base_count = (
        select(func.count(Conversation.conversation_id))
        .outerjoin(User, Conversation.user_id == User.user_id)
        .where(Conversation.role_pack == admin.role_pack)
    )
    if actor_id:
        actor_term = f"%{actor_id}%"
        base_count = base_count.where(
            or_(
                Conversation.user_id == actor_id,
                User.email.ilike(actor_term),
                User.full_name.ilike(actor_term),
            )
        )
    if from_:
        base_count = base_count.where(Conversation.created_at >= _parse_iso(from_, "from"))
    if to:
        base_count = base_count.where(Conversation.created_at <= _parse_iso_to(to, "to"))

    total = (await db.execute(base_count)).scalar_one()

    # Query for records
    query = (
        select(
            Conversation,
            User.full_name,
            User.email,
            msg_count_sub.label("message_count"),
            last_intent_sub.label("last_intent"),
        )
        .outerjoin(User, Conversation.user_id == User.user_id)
        .where(Conversation.role_pack == admin.role_pack)
    )
    if actor_id:
        actor_term = f"%{actor_id}%"
        query = query.where(
            or_(
                Conversation.user_id == actor_id,
                User.email.ilike(actor_term),
                User.full_name.ilike(actor_term),
            )
        )
    if from_:
        query = query.where(Conversation.created_at >= _parse_iso(from_, "from"))
    if to:
        query = query.where(Conversation.created_at <= _parse_iso_to(to, "to"))

    rows = await db.execute(
        query.order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    conversations = [
        AdminConversationSummary(
            id=conv.conversation_id,
            user_name=full_name,
            user_email=email,
            title=conv.title,
            message_count=message_count or 0,
            last_intent=last_intent,
            started_at=conv.created_at,
            last_message_at=conv.last_message_at,
        )
        for conv, full_name, email, message_count, last_intent in rows.all()
    ]

    return AdminConversationListResponse(
        role_pack=admin.role_pack,
        total=total,
        conversations=conversations,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=AdminTranscriptResponse)
async def get_admin_conversation_transcript(
    conversation_id: str,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the full, read-only transcript of one conversation in the admin's role pack.
    Each bot message carries intent_name and confidence.
    Returns 403 if conversation belongs to another role pack, 404 if not found.
    """
    conv_stmt = (
        select(Conversation, User.full_name)
        .outerjoin(User, Conversation.user_id == User.user_id)
        .where(Conversation.conversation_id == conversation_id)
    )
    res = await db.execute(conv_stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv, user_name = row

    if conv.role_pack != admin.role_pack:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: conversation belongs to role pack '{conv.role_pack}', not '{admin.role_pack}'",
        )

    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    out_messages = [
        AdminMessageOut(
            id=m.message_id,
            sender=m.sender,
            content=m.content,
            intent_name=m.intent_name,
            confidence=m.confidence,
            entities=m.entities,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return AdminTranscriptResponse(
        conversation_id=conv.conversation_id,
        role_pack=conv.role_pack,
        user_name=user_name,
        messages=out_messages,
    )

