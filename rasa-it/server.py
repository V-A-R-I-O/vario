"""Lightweight local IT role-pack runtime implementing the VARIO ADR-002 contract.

The canonical Rasa training assets live beside this server. This small runtime keeps
local development and CI lightweight; the live ticket lookup belongs to Slice 20.
"""
import logging
import re
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pathlib import Path

from actions.actions import ActionCheckTicketStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_it_server")

app = FastAPI(
    title="Rasa IT Support Role Pack Runtime",
    description="Implements the VARIO ADR-002 converse webhook for IT Support.",
    version="1.0.0",
)

action_handler = ActionCheckTicketStatus()
TICKET_ID_REGEX = re.compile(r"\b(TKT-\d{4})\b", re.IGNORECASE)
FALLBACK_THRESHOLD = 0.4
AMBIGUITY_THRESHOLD = 0.1

RAISE_WORDS = ("raise", "create", "open", "report", "submit", "log")
TICKET_WORDS = ("ticket", "incident", "issue", "support request", "help desk", "service desk")
STATUS_WORDS = ("status", "track", "progress", "update", "resolved", "closed", "pending", "assigned", "fixed")
PASSWORD_WORDS = ("password", "sign in", "sign-in", "login", "log in", "locked out", "unlock account", "account recovery")
GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
GOODBYES = {"bye", "goodbye", "see you later", "thanks, bye", "thank you, bye"}


def load_nlu_training_examples() -> Dict[str, list[str]]:
    """Load examples from the canonical Rasa NLU YAML for the local classifier."""
    path = Path(__file__).parent / "data" / "nlu.yml"
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        examples_by_intent: Dict[str, list[str]] = {}
        for item in content.get("nlu", []):
            intent = item.get("intent")
            examples = []
            for line in item.get("examples", "").splitlines():
                line = line.strip()
                if line.startswith("- "):
                    phrase = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line[2:]).strip().lower()
                    if phrase:
                        examples.append(phrase)
            if intent:
                examples_by_intent[intent] = examples
        return examples_by_intent
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Unable to load IT NLU examples: %s", type(exc).__name__)
        return {}


TRAINING_DATA = load_nlu_training_examples()


class SessionState(BaseModel):
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)


class ConverseRequest(BaseModel):
    sender: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1, max_length=2000)
    session: Optional[SessionState] = None


class ConverseResponse(BaseModel):
    intent: Optional[str]
    confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)
    template_key: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _similarity_score(message: str, examples: list[str]) -> float:
    message_tokens = _tokens(message)
    if not message_tokens:
        return 0.0
    best = 0.0
    for example in examples:
        example_tokens = _tokens(example)
        if not example_tokens:
            continue
        overlap = len(message_tokens & example_tokens)
        jaccard = overlap / len(message_tokens | example_tokens)
        coverage = overlap / len(message_tokens)
        score = 0.3 * jaccard + 0.7 * coverage
        if message.strip().lower() == example:
            score = 0.98
        elif example in message.lower() or message.lower() in example:
            score = max(score, 0.92)
        best = max(best, score)
    return best


def classify_message(text: str) -> tuple[str, float, Dict[str, Any]]:
    """Classify common IT requests deterministically for local development and tests."""
    clean = text.strip().lower()
    entities: Dict[str, Any] = {}
    ticket_match = TICKET_ID_REGEX.search(text)
    if ticket_match:
        entities["ticket_id"] = ticket_match.group(1).upper()

    if clean in GREETINGS or any(clean.startswith(greeting + " ") for greeting in GREETINGS):
        return "greet", 0.96, entities
    if clean in GOODBYES or any(clean.startswith(goodbye + " ") for goodbye in GOODBYES):
        return "goodbye", 0.95, entities

    has_password = any(word in clean for word in PASSWORD_WORDS)
    has_raise = any(word in clean for word in RAISE_WORDS) and any(word in clean for word in TICKET_WORDS)
    has_status = any(word in clean for word in STATUS_WORDS)
    has_ticket_context = any(word in clean for word in TICKET_WORDS)
    has_it_context = has_ticket_context or has_password or any(
        word in clean
        for word in (
            "computer", "laptop", "wifi", "network", "email", "vpn",
            "software", "printer", "technical", "it support", "reset",
            "account", "sign in", "sign-in", "login", "log in",
        )
    )

    # Reject unrelated messages before token-overlap scoring (e.g. weather/jokes).
    if not has_it_context and not ticket_match:
        return "nlu_fallback", 0.15, entities

    # Specific requests take priority over the ticket-ID prior.
    if has_password:
        return "reset_password", 0.94, entities
    if has_raise:
        return "raise_ticket", 0.94, entities
    if ticket_match and not has_password and not has_raise:
        return "check_ticket_status", 0.96, entities
    if has_status and has_ticket_context:
        return "check_ticket_status", 0.91, entities

    scores = {
        intent: _similarity_score(clean, examples)
        for intent, examples in TRAINING_DATA.items()
        if intent not in {"nlu_fallback"}
    }
    # A ticket-support context is strong evidence for a status query even without an ID.
    if has_ticket_context and any(word in clean for word in ("check", "where", "look", "tell", "know", "follow", "track")):
        scores["check_ticket_status"] = max(scores.get("check_ticket_status", 0.0), 0.86)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < FALLBACK_THRESHOLD:
        return "nlu_fallback", 0.15, entities
    top_intent, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if second_score >= 0.25 and top_score - second_score < AMBIGUITY_THRESHOLD:
        return "nlu_fallback", round(top_score, 2), entities
    return top_intent, round(min(0.96, max(0.85, top_score)), 2), entities


@app.get("/")
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rasa-it", "port": 5006}


@app.post("/webhooks/vario/converse", response_model=ConverseResponse)
async def converse(req: ConverseRequest) -> ConverseResponse:
    """Primary endpoint consumed by the backend dialogue router."""
    message = req.message
    session = req.session or SessionState()

    if session.current_step == "await_ticket_id" or session.current_form == "check_ticket_status_form":
        ticket_match = TICKET_ID_REGEX.search(message)
        if not ticket_match:
            return ConverseResponse(
                intent="check_ticket_status",
                confidence=0.95,
                entities={},
                template_key=None,
                slots=session.slots,
                current_form="check_ticket_status_form",
                current_step="await_ticket_id",
                response_text="Please provide a valid ticket ID such as TKT-1234.",
            )
        intent, confidence, entities = "check_ticket_status", 0.96, {"ticket_id": ticket_match.group(1).upper()}
    else:
        intent, confidence, entities = classify_message(message)

    logger.info(
        "IT converse sender=%s intent=%s confidence=%.2f",
        req.sender,
        intent,
        confidence,
    )

    if intent == "nlu_fallback" or confidence < FALLBACK_THRESHOLD:
        return ConverseResponse(
            intent="nlu_fallback",
            confidence=confidence,
            entities=entities,
            slots=session.slots,
            current_form=session.current_form,
            current_step=session.current_step,
            response_text=(
                "I'm sorry, I didn't understand that. You can ask me to check an IT ticket, "
                "raise a support ticket, or get password-reset help."
            ),
        )

    if intent == "check_ticket_status":
        ticket_id = entities.get("ticket_id") or session.slots.get("ticket_id")
        action_result = action_handler.execute_logic(ticket_id)
        merged_slots = dict(session.slots)
        merged_slots.update(action_result.get("slots", {}))

        if action_result.get("missing_slot") == "ticket_id":
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                slots=merged_slots,
                current_form="check_ticket_status_form",
                current_step="await_ticket_id",
                response_text=action_result["response_text"],
            )

        # Do not invent a status before Slice 20 connects the ITSM adapter.
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            slots=merged_slots,
            current_form=None,
            current_step=None,
            response_text=(
                f"I recognized ticket {merged_slots['ticket_id']}. "
                "The live status lookup will be available when the ITSM adapter is connected."
            ),
        )

    if intent == "raise_ticket":
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            slots=session.slots,
            response_text="I can help with a new support ticket. The guided ticket-creation workflow is being connected.",
        )

    if intent == "reset_password":
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            slots=session.slots,
            response_text="I can help with password-reset guidance. The verified reset workflow is being connected.",
        )

    if intent == "greet":
        response = "Hello! I am your VARIO IT Support Assistant. I can check a ticket status, help raise a ticket, or guide you to password-reset support."
    else:
        response = "Thanks for contacting IT Support. Have a good day!"
    return ConverseResponse(
        intent=intent,
        confidence=confidence,
        entities=entities,
        slots=session.slots,
        response_text=response,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5006)
