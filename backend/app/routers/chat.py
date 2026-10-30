"""POST /api/chat — the chat-mode conversation engine.

Flow (ADD chat-mode diagram):
  persist user message
    → load session
    → route to the role pack's Rasa instance
    → render a stored variant (or clarify if below confidence threshold)
    → persist bot message
    → update session
    → return {response_text, intent, confidence, entities, session}

For `mode: "talk"` (slice-06) the rendered text is additionally sent to the
tts-service for synthesis; the reply then carries `audio_base64`,
`audio_content_type`, and `tts_available`. TTS degrades gracefully — on failure
the text reply is still returned with `tts_available: false`.

ADR-006 rules applied here: no clarification override while a form is active;
a user message is redacted when the previous reply set `sensitive_next_input`;
an unreachable role pack yields a friendly `degraded` reply instead of a 500.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.models.message import Message
from app.schemas.chat import ChatRequest, ChatResponse, SessionState
from app.services import dialogue_router, response_renderer, session_manager, tts_service, audit_log_service

TALK_MODE = "talk"

logger = logging.getLogger("vario.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

CLARIFICATION_PROMPT = (
    "I'm not sure I understood that. Could you rephrase it, or give me a little "
    "more detail about what you need?"
)
FALLBACK_RESPONSE = "Sorry, I couldn't put together a response for that just now."
REDACTED_CONTENT = "[security answer redacted]"

_PACK_NAMES = {"hr": "HR", "it": "IT support", "admissions": "Admissions"}


def degraded_reply(role_pack: str) -> str:
    name = _PACK_NAMES.get(role_pack, role_pack)
    return f"The {name} assistant is unavailable right now. Please try again in a moment."


def _is_legacy_it_secret_step(conversation: Conversation, session) -> bool:
    """The v1 IT pack's security-answer step; remove once slice-37 sends the flag."""
    return (
        conversation.role_pack == "it"
        and session.current_form == "reset_password_form"
        and session.current_step == "await_security_answer"
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id

    # --- Ownership checks ---
    conv_result = await db.execute(
        select(Conversation).where(Conversation.conversation_id == payload.conversation_id)
    )
    conversation = conv_result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Conversation does not belong to this user")

    # --- 1. Load session state before persistence so sensitive workflow input can be redacted ---
    session = await session_manager.load_or_create(db, conversation.conversation_id)

    # Secrets (e.g. security answers) reach the role pack but are never stored in chat history.
    is_sensitive = session.sensitive_next_input or _is_legacy_it_secret_step(conversation, session)
    user_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="user",
        content=REDACTED_CONTENT if is_sensitive else payload.message,
    )
    db.add(user_msg)
    await db.flush()

    # --- 3. Route to the correct Rasa instance ---
    auth_result = await db.execute(select(User).where(User.user_id == user_id))
    auth_user = auth_result.scalars().first()
    auth_context = (
        {"employee_id": auth_user.external_id, "full_name": auth_user.full_name, "role": auth_user.role}
        if auth_user
        else {}
    )
    form_was_active = bool(session.current_form)
    try:
        rasa_result = await dialogue_router.route(
            conversation.role_pack,
            conversation.conversation_id,
            payload.message,
            session,
            auth_context,
            user_id=user_id,
            sensitive=is_sensitive,
        )
    except dialogue_router.RolePackUnavailableError:
        rasa_result = None

    # --- 4. Render the response: degrade, clarify (FR-2) or render the workflow reply ---
    degraded = rasa_result is None
    intent = confidence = card = None
    entities: dict = {}
    if degraded:
        logger.warning(
            "chat turn degraded conversation=%s role_pack=%s",
            conversation.conversation_id,
            conversation.role_pack,
        )
        response_text = degraded_reply(conversation.role_pack)
        card = {"type": "error", "text": response_text}
        # The dialogue doesn't advance; a pending secret prompt stays pending.
        next_form, next_step, next_slots = session.current_form, session.current_step, None
        next_sensitive = session.sensitive_next_input
    else:
        intent, confidence, entities = rasa_result.intent, rasa_result.confidence, rasa_result.entities
        # FR-5 — record the classification/routing decision for this turn.
        logger.info(
            "chat turn conversation=%s role_pack=%s intent=%s confidence=%.3f",
            conversation.conversation_id,
            conversation.role_pack,
            intent,
            confidence,
        )
        # Inside a form, low-confidence text is usually a slot answer ("fever"), not a new request.
        if confidence < settings.CONFIDENCE_THRESHOLD and not form_was_active:
            response_text = CLARIFICATION_PROMPT
            next_form, next_step, next_slots = session.current_form, session.current_step, None
            next_sensitive = session.sensitive_next_input
        else:
            rendered = None
            if rasa_result.template_key:
                rendered = await response_renderer.render(
                    db, rasa_result.template_key, rasa_result.slots
                )
            response_text = rendered or rasa_result.response_text or FALLBACK_RESPONSE
            card = rasa_result.card
            if card and card.get("type") == "faq_answer" and rendered:
                card = {**card, "text": rendered}
            next_form, next_step, next_slots = (
                rasa_result.current_form,
                rasa_result.current_step,
                rasa_result.slots,
            )
            next_sensitive = rasa_result.sensitive_next_input

    # --- 5. Persist the bot message ---
    bot_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="bot",
        content=response_text,
        intent_name=intent,
        confidence=confidence,
        entities=entities or None,
        card=card,
    )
    db.add(bot_msg)

    # --- 6. Update session + conversation bookkeeping ---
    session = await session_manager.update_after_turn(
        db, session, next_form, next_step, next_slots, next_sensitive
    )
    conversation.last_message_at = datetime.utcnow()

    await db.commit()

    # --- 6.5. Fire audit event if present (slice-15) ---
    if rasa_result and rasa_result.audit_event:
        await audit_log_service.record(
            db,
            actor_id=user_id,
            role_pack=conversation.role_pack,
            action_type=rasa_result.audit_event.get("action_type", "unknown"),
            reference_id=rasa_result.audit_event.get("reference_id"),
            details=rasa_result.audit_event.get("details"),
        )

    # --- 7. Talk mode — synthesize the reply to audio (degrades gracefully) ---
    audio_base64 = audio_content_type = tts_available = None
    if payload.mode == TALK_MODE:
        tts = await tts_service.synthesize(response_text)
        tts_available = tts.available
        audio_base64 = tts.audio_base64
        audio_content_type = tts.audio_content_type

    return ChatResponse(
        response_text=response_text,
        intent=intent,
        confidence=confidence,
        entities=entities or {},
        session=SessionState(
            current_form=session.current_form,
            current_step=session.current_step,
            slots=session.slots or {},
        ),
        card=card,
        degraded=degraded,
        audio_base64=audio_base64,
        audio_content_type=audio_content_type,
        tts_available=tts_available,
    )
