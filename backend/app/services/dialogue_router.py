"""dialogue-router — pure dispatcher to the correct Rasa instance.

Reads the conversation's `role_pack`, forwards the message + session state to the
matching `RASA_*_URL`, and returns the Rasa result for rendering. No NLU logic of
its own (ADD §dialogue-router).

The request/response contract is `docs/decisions/ADR-006-rasa-contract-v2.md`
(v2 of ADR-002): `sender` is the conversation ID, the trusted identity travels
in `metadata.auth_context`, and replies may carry a `card` and a
`sensitive_next_input` flag. Any failure to get a usable reply raises
`RolePackUnavailableError` so the chat engine can degrade gracefully.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.models.session import Session

logger = logging.getLogger("vario.dialogue_router")

# VARIO-specific converse endpoint each Rasa instance exposes (see ADR-006).
RASA_CONVERSE_PATH = "/webhooks/vario/converse"
_RASA_TIMEOUT_SECONDS = 10.0

# The frontend's generic bot-message types; must match rasa-shared/contract/card-types.json.
CARD_TYPES = frozenset(
    {
        "plain_text",
        "data_card",
        "slot_prompt",
        "confirmation",
        "result",
        "not_found",
        "faq_answer",
        "error",
        "list",
    }
)


class RolePackUnavailableError(Exception):
    """The role pack could not be reached or returned an unusable reply."""

    def __init__(self, role_pack: str):
        super().__init__(f"Role pack '{role_pack}' is unavailable")
        self.role_pack = role_pack


@dataclass
class RasaResult:
    intent: Optional[str]
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    template_key: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None
    audit_event: Optional[Dict[str, Any]] = None
    card: Optional[Dict[str, Any]] = None
    sensitive_next_input: bool = False


def get_rasa_url(role_pack: str) -> str:
    """Map a role pack to its Rasa instance base URL."""
    mapping = {
        "hr": settings.RASA_HR_URL,
        "it": settings.RASA_IT_URL,
        "admissions": settings.RASA_ADMISSIONS_URL,
    }
    try:
        return mapping[role_pack]
    except KeyError:
        raise ValueError(f"No Rasa instance configured for role pack '{role_pack}'")


async def _post_to_rasa(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Injectable seam: the single outbound HTTP call. Tests patch this."""
    async with httpx.AsyncClient(timeout=_RASA_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def _valid_card(card: Any, role_pack: str) -> Optional[Dict[str, Any]]:
    if card is None:
        return None
    if isinstance(card, dict) and card.get("type") in CARD_TYPES:
        return card
    logger.warning("dropping card with unknown type from role_pack=%s", role_pack)
    return None


async def route(
    role_pack: str,
    sender: str,
    message: str,
    session: Session,
    auth_context: Optional[Dict[str, Any]] = None,
    *,
    user_id: Optional[str] = None,
    sensitive: bool = False,
) -> RasaResult:
    """Forward a message to the role pack's Rasa instance and parse the result.

    `sender` is the conversation ID, so each conversation gets its own Rasa
    tracker. Raises `RolePackUnavailableError` on any transport or payload failure.
    """
    base_url = get_rasa_url(role_pack)
    url = base_url.rstrip("/") + RASA_CONVERSE_PATH

    payload = {
        "sender": sender,
        "message": message,
        # Trusted identity comes from the authenticated backend request, never chat text.
        "metadata": {
            "auth_context": auth_context or {},
            "user_id": user_id,
            "sensitive": sensitive,
        },
        # Gateway mirror; only pre-Rasa (v1) packs read it.
        "session": {
            "current_form": session.current_form,
            "current_step": session.current_step,
            "slots": session.slots or {},
        },
    }

    if auth_context:
        # Deprecated top-level copy for the v1 IT pack; removed once slice-37 lands.
        payload["auth_context"] = auth_context

    try:
        raw = await _post_to_rasa(url, payload)
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("role pack unreachable role_pack=%s error=%s", role_pack, type(exc).__name__)
        raise RolePackUnavailableError(role_pack) from exc
    if not isinstance(raw, dict):
        raise RolePackUnavailableError(role_pack)

    result = RasaResult(
        intent=raw.get("intent"),
        confidence=float(raw.get("confidence") or 0.0),
        entities=raw.get("entities") or {},
        template_key=raw.get("template_key"),
        slots=raw.get("slots") or {},
        current_form=raw.get("current_form"),
        current_step=raw.get("current_step"),
        response_text=raw.get("response_text"),
        audit_event=raw.get("audit_event"),
        card=_valid_card(raw.get("card"), role_pack),
        sensitive_next_input=bool(raw.get("sensitive_next_input")),
    )

    # FR-5 — log every classification/routing decision.
    logger.info(
        "routed role_pack=%s rasa_url=%s intent=%s confidence=%.3f template_key=%s",
        role_pack,
        base_url,
        result.intent,
        result.confidence,
        result.template_key,
    )

    return result
