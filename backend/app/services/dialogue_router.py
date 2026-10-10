"""dialogue-router — pure dispatcher to the correct Rasa instance.

Reads the conversation's `role_pack`, forwards the message + session state to the
matching `RASA_*_URL`, and returns the Rasa result for rendering. No NLU logic of
its own (ADD §dialogue-router).

The Rasa request/response contract is documented in
`docs/decisions/ADR-002-rasa-chat-contract.md`. The role-pack Rasa instances that
implement it are built in later slices (12/17/22); here we only consume the
contract and mock it in tests.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.models.session import Session

logger = logging.getLogger("vario.dialogue_router")

# VARIO-specific converse endpoint each Rasa instance exposes (see ADR-002).
RASA_CONVERSE_PATH = "/webhooks/vario/converse"
_RASA_TIMEOUT_SECONDS = 10.0


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


async def route(
    role_pack: str,
    sender: str,
    message: str,
    session: Session,
) -> RasaResult:
    """Forward a message to the role pack's Rasa instance and parse the result."""
    base_url = get_rasa_url(role_pack)
    url = base_url.rstrip("/") + RASA_CONVERSE_PATH

    payload = {
        "sender": sender,
        "message": message,
        "session": {
            "current_form": session.current_form,
            "current_step": session.current_step,
            "slots": session.slots or {},
        },
    }

    raw = await _post_to_rasa(url, payload)

    result = RasaResult(
        intent=raw.get("intent"),
        confidence=float(raw.get("confidence", 0.0)),
        entities=raw.get("entities") or {},
        template_key=raw.get("template_key"),
        slots=raw.get("slots") or {},
        current_form=raw.get("current_form"),
        current_step=raw.get("current_step"),
        response_text=raw.get("response_text"),
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
