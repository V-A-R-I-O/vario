"""session-manager — per-conversation dialogue state.

PostgreSQL is the source of truth (ADD §session-manager). The session row is
loaded at the start of every turn and written back after the bot responds.
There is no in-memory cache.

Under ADR-006 the row is a *mirror* of what the role pack reports each turn:
Rasa packs keep the real dialogue state in their own tracker store, and the
pre-Rasa (v1) packs return their full state in `slots`. The mirror is stored
as returned — never merged — so values from finished workflows can't linger.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.models.session import Session


def _expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=settings.SESSION_TTL_MINUTES)


def _reset(session: Session) -> None:
    session.current_form = None
    session.current_step = None
    session.slots = {}
    session.sensitive_next_input = False


async def load_or_create(db: AsyncSession, conversation_id: str) -> Session:
    """Return the `sessions` row for a conversation, creating it on first turn.

    An expired session starts the turn with no form, step or slots. Rasa packs
    expire their tracker on the same TTL via `session_config`.
    """
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
            sensitive_next_input=False,
            expires_at=_expiry(),
        )
        db.add(session)
        await db.flush()
    elif session.expires_at is not None and session.expires_at < datetime.utcnow():
        _reset(session)
        await db.flush()

    return session


async def update_after_turn(
    db: AsyncSession,
    session: Session,
    current_form: Optional[str],
    current_step: Optional[str],
    slots: Optional[dict],
    sensitive_next_input: bool = False,
) -> Session:
    """Store the role pack's reported state and refresh the TTL.

    `slots` replaces the stored slots; `None` keeps them unchanged (used by
    clarification and degraded turns, which don't advance the dialogue).
    """
    session.current_form = current_form
    session.current_step = current_step
    if slots is not None:
        # A new dict so SQLAlchemy reliably detects the JSON change.
        session.slots = dict(slots)
    session.sensitive_next_input = sensitive_next_input
    session.expires_at = _expiry()

    await db.flush()
    return session
