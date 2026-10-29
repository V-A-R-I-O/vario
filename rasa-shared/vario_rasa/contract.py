"""VARIO converse contract v2 — pure-Python helpers shared by every role pack.

See docs/decisions/ADR-006-rasa-contract-v2.md. This module has no Rasa
dependency so custom-action servers can import `vario_payload` too.
"""
from typing import Any, Dict, Iterable, List, Optional

CONTRACT_VERSION = 2

# Key under which actions/responses put VARIO fields in a custom JSON message.
VARIO_PAYLOAD_KEY = "vario"

# Stored in place of a user message marked `metadata.sensitive` (ADR-006 §6).
REDACTED_TEXT = "[redacted]"

# The frontend's generic bot-message types (frontend/src/components/chat/types.ts).
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

_PAYLOAD_FIELDS = ("template_key", "slots", "card", "audit_event", "sensitive_next_input")


def vario_payload(
    *,
    template_key: Optional[str] = None,
    slots: Optional[Dict[str, Any]] = None,
    card: Optional[Dict[str, Any]] = None,
    audit_event: Optional[Dict[str, Any]] = None,
    sensitive_next_input: bool = False,
) -> Dict[str, Any]:
    """Build the custom JSON an action passes to `dispatcher.utter_message(json_message=...)`."""
    if card is not None and not is_valid_card(card):
        raise ValueError(f"card type must be one of {sorted(CARD_TYPES)}")
    fields = {
        "template_key": template_key,
        "slots": slots,
        "card": card,
        "audit_event": audit_event,
        "sensitive_next_input": sensitive_next_input or None,
    }
    return {VARIO_PAYLOAD_KEY: {k: v for k, v in fields.items() if v is not None}}


def is_valid_card(card: Any) -> bool:
    return isinstance(card, dict) and card.get("type") in CARD_TYPES


def validate_converse_request(body: Any) -> Optional[str]:
    """Return an error message for a malformed converse request, else None."""
    if not isinstance(body, dict):
        return "request body must be a JSON object"
    for key in ("sender", "message"):
        if not isinstance(body.get(key), str) or not body[key].strip():
            return f"'{key}' must be a non-empty string"
    if not isinstance(body.get("metadata", {}), dict):
        return "'metadata' must be an object"
    return None


def entities_to_dict(entities: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Rasa's entity list → {entity: value}; the last value for an entity wins."""
    return {e["entity"]: e.get("value") for e in entities or [] if e.get("entity")}


def _buttons_card(text: Optional[str], buttons: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "type": "slot_prompt",
        "text": text or "",
        "options": [{"label": b.get("title", ""), "value": b.get("payload")} for b in buttons],
    }


def build_converse_response(
    *,
    parse_data: Dict[str, Any],
    active_loop: Optional[str],
    requested_slot: Optional[str],
    bot_messages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assemble the gateway response from one Rasa turn (ADR-006 §3).

    `bot_messages` are the CollectingOutputChannel messages for the turn: text
    parts become `response_text`; the last `vario` custom payload supplies the
    template/slots/card/audit fields. A text message with buttons becomes a
    `slot_prompt` card when no explicit card was sent.
    """
    texts: List[str] = []
    vario: Dict[str, Any] = {}
    buttons_card = None
    for message in bot_messages:
        if message.get("text"):
            texts.append(message["text"])
            if message.get("buttons"):
                buttons_card = _buttons_card(message["text"], message["buttons"])
        custom = message.get("custom")
        if isinstance(custom, dict) and isinstance(custom.get(VARIO_PAYLOAD_KEY), dict):
            vario.update(custom[VARIO_PAYLOAD_KEY])

    card = vario.get("card")
    if not is_valid_card(card):
        card = buttons_card

    intent = parse_data.get("intent") or {}
    return {
        "intent": intent.get("name"),
        "confidence": float(intent.get("confidence") or 0.0),
        "entities": entities_to_dict(parse_data.get("entities")),
        "template_key": vario.get("template_key"),
        "slots": vario.get("slots") or {},
        "current_form": active_loop,
        "current_step": requested_slot if active_loop else None,
        "response_text": "\n\n".join(texts) or None,
        "audit_event": vario.get("audit_event"),
        "card": card,
        "sensitive_next_input": bool(vario.get("sensitive_next_input")),
    }
