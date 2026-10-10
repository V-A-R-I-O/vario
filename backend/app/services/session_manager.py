"""session-manager — per-conversation dialogue state.

PostgreSQL is the source of truth (ADD §session-manager). The session row is
loaded at the start of every turn and written back after the bot responds.
There is no in-memory cache.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.models.session import Session


def _expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=settings.SESSION_TTL_MINUTES)


async def load_or_create(db: AsyncSession, conversation_id: str) -> Session:
    """Return the `sessions` row for a conversation, creating it on first turn."""
    result = await db.execute(
        select(Session).where(Session.conversation_id == conversation_id)
    )
    session = result.scalars().first()

    if session is None:
        session = Session(
            conversation_id=conversation_id,
            current_form=None,
            current_step=None,
            slots={},
            expires_at=_expiry(),
        )
        db.add(session)
        await db.flush()

    return session


async def update_after_turn(
    db: AsyncSession,
    session: Session,
    current_form: Optional[str],
    current_step: Optional[str],
    slots: Optional[dict],
) -> Session:
    """Persist the dialogue state returned by Rasa and refresh the TTL.

    Slots are merged onto the existing slots so values collected in earlier
    turns survive across the conversation (FR-4).
    """
    merged = dict(session.slots or {})
    if slots:
        merged.update(slots)

    session.current_form = current_form
    session.current_step = current_step
    session.slots = merged
    session.expires_at = _expiry()

    # Reassign so SQLAlchemy reliably detects the JSON mutation.
    session.slots = merged
    await db.flush()
    return session
