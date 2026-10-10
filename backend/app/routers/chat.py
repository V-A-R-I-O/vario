"""POST /api/chat — the chat-mode conversation engine.

Flow (ADD chat-mode diagram):
  persist user message
    → load session
    → route to the role pack's Rasa instance
    → render a stored variant (or clarify if below confidence threshold)
    → persist bot message
    → update session
    → return {response_text, intent, confidence, entities, session}

Talk mode (TTS) is a later slice; the `mode` field is accepted but only `chat`
is handled here.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatRequest, ChatResponse, SessionState
from app.services import dialogue_router, response_renderer, session_manager

logger = logging.getLogger("vario.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

CLARIFICATION_PROMPT = (
    "I'm not sure I understood that. Could you rephrase it, or give me a little "
    "more detail about what you need?"
)
FALLBACK_RESPONSE = "Sorry, I couldn't put together a response for that just now."


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

    # --- 1. Persist the user message ---
    user_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="user",
        content=payload.message,
    )
    db.add(user_msg)
    await db.flush()

    # --- 2. Load session state (Postgres is authoritative) ---
    session = await session_manager.load_or_create(db, conversation.conversation_id)

    # --- 3. Route to the correct Rasa instance ---
    rasa_result = await dialogue_router.route(
        role_pack=conversation.role_pack,
        sender=user_id,
        message=payload.message,
        session=session,
    )

    # FR-5 — record the classification/routing decision for this turn.
    logger.info(
        "chat turn conversation=%s role_pack=%s intent=%s confidence=%.3f",
        conversation.conversation_id,
        conversation.role_pack,
        rasa_result.intent,
        rasa_result.confidence,
    )

    # --- 4. Render the response (or clarify when below threshold, FR-2) ---
    below_threshold = rasa_result.confidence < settings.CONFIDENCE_THRESHOLD

    if below_threshold:
        response_text = CLARIFICATION_PROMPT
        # Do not advance the workflow — keep the current form/step, don't merge slots.
        next_form, next_step, next_slots = session.current_form, session.current_step, None
    else:
        rendered = None
        if rasa_result.template_key:
            rendered = await response_renderer.render(
                db, rasa_result.template_key, rasa_result.slots
            )
        response_text = rendered or rasa_result.response_text or FALLBACK_RESPONSE
        next_form, next_step, next_slots = (
            rasa_result.current_form,
            rasa_result.current_step,
            rasa_result.slots,
        )

    # --- 5. Persist the bot message ---
    bot_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="bot",
        content=response_text,
        intent_name=rasa_result.intent,
        confidence=rasa_result.confidence,
        entities=rasa_result.entities or None,
    )
    db.add(bot_msg)

    # --- 6. Update session + conversation bookkeeping ---
    session = await session_manager.update_after_turn(
        db, session, next_form, next_step, next_slots
    )
    conversation.last_message_at = datetime.utcnow()

    await db.commit()

    return ChatResponse(
        response_text=response_text,
        intent=rasa_result.intent,
        confidence=rasa_result.confidence,
        entities=rasa_result.entities or {},
        session=SessionState(
            current_form=session.current_form,
            current_step=session.current_step,
            slots=session.slots or {},
        ),
    )
