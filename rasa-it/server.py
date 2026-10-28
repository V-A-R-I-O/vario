"""Lightweight local IT role-pack runtime implementing the VARIO ADR-002 contract.

The canonical Rasa training assets live beside this server. The runtime calls the
ITSM HTTP adapter for live ticket status and returns structured slots for the chat UI.
"""
import logging
import re
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pathlib import Path

from actions.actions import ActionCheckTicketStatus
from actions.itsm_adapter import BackendUnavailableError, ITSMAdapter, TicketCreationRejectedError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_it_server")

app = FastAPI(
    title="Rasa IT Support Role Pack Runtime",
    description="Implements the VARIO ADR-002 converse webhook for IT Support.",
    version="1.0.0",
)

action_handler = ActionCheckTicketStatus()
TICKET_ID_REGEX = re.compile(r"\b((?:TKT|IT)-\d{4})\b", re.IGNORECASE)
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
    auth_context: Dict[str, Any] = Field(default_factory=dict)


class ConverseResponse(BaseModel):
    intent: Optional[str]
    confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)
    template_key: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None
    audit_event: Optional[Dict[str, Any]] = None


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
    message = req.message.strip()
    session = req.session or SessionState()
    slots = dict(session.slots or {})
    reporter = str(req.auth_context.get("employee_id") or "").strip().upper()
    in_create_form = session.current_form == "raise_ticket_form"

    if session.current_step == "await_ticket_id" or session.current_form == "check_ticket_status_form":
        ticket_match = TICKET_ID_REGEX.search(message)
        if not ticket_match:
            return ConverseResponse(
                intent="check_ticket_status", confidence=0.95, entities={},
                template_key=None, slots=slots, current_form="check_ticket_status_form",
                current_step="await_ticket_id",
                response_text="Please provide a valid ticket ID such as TKT-1234.",
            )
        intent, confidence, entities = "check_ticket_status", 0.96, {"ticket_id": ticket_match.group(1).upper()}
    elif in_create_form:
        intent, confidence, entities = "raise_ticket", 0.96, {}
    else:
        intent, confidence, entities = classify_message(message)

    # Dedupe only the immediately following create flow, not later requests.
    if not in_create_form and intent != "raise_ticket":
        slots["last_created_signature"] = None
        slots["last_created_ticket_id"] = None
        session = SessionState(current_form=session.current_form, current_step=session.current_step, slots=slots)

    def workflow_response(text, workflow_slots, current_form, current_step, audit_event=None):
        response_entities = dict(entities)
        response_entities.update(workflow_slots)
        return ConverseResponse(
            intent="raise_ticket", confidence=0.96, entities=response_entities,
            slots=workflow_slots, current_form=current_form, current_step=current_step,
            response_text=text, audit_event=audit_event,
        )

    if in_create_form or intent == "raise_ticket":
        if not reporter:
            return workflow_response(
                "I couldn't verify your employee profile. Please sign in again before creating an IT ticket.",
                {**slots, "requested_slot": None, "confirmation_pending": False}, None, None,
            )
        if _is_cancel(message):
            return workflow_response(
                "Ticket creation cancelled. No ticket was created.",
                _cleared_ticket_slots(slots, clear_dedupe=True), None, None,
            )
        if not in_create_form:
            preserved = {k: slots[k] for k in ("last_created_signature", "last_created_ticket_id") if slots.get(k)}
            start_slots = _cleared_ticket_slots(slots, clear_dedupe=False)
            start_slots.update(preserved)
            start_slots.update({"reporter": reporter, "requested_slot": "category", "confirmation_pending": False})
            return workflow_response(
                "What category best describes the issue? For example: hardware, software, access, network, or other.",
                start_slots, "raise_ticket_form", "ask_category",
            )

        slots["reporter"] = reporter
        if session.current_step == "ask_category":
            category = message.strip()
            if not category or len(category) > 80:
                slots["requested_slot"] = "category"
                return workflow_response("Please provide a category of 1–80 characters (for example, hardware or network).", slots, "raise_ticket_form", "ask_category")
            slots.update({"category": category, "description": None, "requested_slot": "description", "confirmation_pending": False, "ticket_result": None, "ticket_reused": None, "ticket_id": None})
            return workflow_response(
                "Please describe the IT issue. Include what happened and any useful error message, but do not include passwords or other secrets.",
                slots, "raise_ticket_form", "ask_description",
            )

        if session.current_step == "ask_description":
            description = message.strip()
            if not description or len(description) > 2000:
                slots["requested_slot"] = "description"
                return workflow_response("Please provide a description of 1–2000 characters, without passwords or other secrets.", slots, "raise_ticket_form", "ask_description")
            slots.update({"description": description, "requested_slot": None, "confirmation_pending": True, "ticket_result": None, "ticket_reused": None, "ticket_id": None})
            return workflow_response(
                "Please review the ticket details below. Reply Confirm to create the ticket or Cancel to stop.",
                slots, "raise_ticket_form", "confirm",
            )

        if session.current_step == "confirm":
            if not _is_confirm(message):
                slots["confirmation_pending"] = True
                return workflow_response("Please reply Confirm to create this ticket, or Cancel to stop without creating it.", slots, "raise_ticket_form", "confirm")
            signature = _ticket_signature(reporter, str(slots.get("category") or ""), str(slots.get("description") or ""))
            previous_signature = slots.get("last_created_signature")
            previous_ticket_id = slots.get("last_created_ticket_id")
            if signature and signature == previous_signature and previous_ticket_id:
                result_slots = _cleared_ticket_slots(slots, clear_dedupe=False)
                result_slots.update({
                    "reporter": reporter, "category": slots.get("category"), "description": slots.get("description"),
                    "ticket_id": previous_ticket_id, "ticket_result": True, "ticket_reused": True,
                    "last_created_signature": previous_signature, "last_created_ticket_id": previous_ticket_id,
                    "confirmation_pending": False, "requested_slot": None,
                })
                return workflow_response("This matches the ticket you just created, so I reused the existing ticket instead of creating a duplicate.", result_slots, None, None)
            try:
                ticket = await ITSMAdapter.create_ticket(
                    category=str(slots.get("category") or ""),
                    description=str(slots.get("description") or ""),
                    reporter=reporter,
                )
            except BackendUnavailableError:
                slots["confirmation_pending"] = True
                return workflow_response("I can't reach the IT ticket system right now. Your ticket was not created; please try Confirm again shortly.", slots, "raise_ticket_form", "confirm")
            except TicketCreationRejectedError as exc:
                slots["confirmation_pending"] = True
                return workflow_response(f"I couldn't create the ticket: {exc}. Please check your details or Cancel.", slots, "raise_ticket_form", "confirm")

            ticket_id = str(ticket["ticket_id"]).strip().upper()
            result_slots = _cleared_ticket_slots(slots, clear_dedupe=False)
            result_slots.update({
                "reporter": reporter, "category": slots.get("category"), "description": slots.get("description"),
                "ticket_id": ticket_id, "ticket_result": True, "ticket_reused": False,
                "confirmation_pending": False, "requested_slot": None,
                "last_created_signature": signature, "last_created_ticket_id": ticket_id,
            })
            return workflow_response(
                "Ticket created successfully. Reference ID:", result_slots, None, None,
                {"action_type": "ticket_created", "reference_id": ticket_id, "details": {"category": slots.get("category"), "reporter": reporter}},
            )

        restart_slots = _cleared_ticket_slots(slots, clear_dedupe=False)
        restart_slots.update({"reporter": reporter, "requested_slot": "category", "confirmation_pending": False})
        return workflow_response("Let's start your IT ticket again. What category best describes the issue?", restart_slots, "raise_ticket_form", "ask_category")

    logger.info("IT converse sender=%s intent=%s confidence=%.2f", req.sender, intent, confidence)
    if intent == "nlu_fallback" or confidence < FALLBACK_THRESHOLD:
        return ConverseResponse(
            intent="nlu_fallback", confidence=confidence, entities=entities, slots=slots,
            current_form=session.current_form, current_step=session.current_step,
            response_text="I'm sorry, I didn't understand that. You can ask me to check an IT ticket, raise a support ticket, or get password-reset help.",
        )
    if intent == "check_ticket_status":
        ticket_id = entities.get("ticket_id") or slots.get("ticket_id")
        action_result = await action_handler.lookup_logic(ticket_id)
        merged_slots = dict(slots)
        merged_slots.update(action_result.get("slots", {}))
        response_entities = dict(entities)
        response_entities.update(action_result.get("slots", {}))
        if action_result.get("missing_slot") == "ticket_id":
            return ConverseResponse(intent=intent, confidence=confidence, entities=response_entities, slots=merged_slots, current_form="check_ticket_status_form", current_step="await_ticket_id", response_text=action_result["response_text"])
        if action_result.get("backend_unavailable") or action_result.get("slots", {}).get("found") is False:
            return ConverseResponse(intent=intent, confidence=confidence, entities=response_entities, slots=merged_slots, current_form=None, current_step=None, response_text=action_result["response_text"])
        return ConverseResponse(intent=intent, confidence=confidence, entities=response_entities, slots=merged_slots, template_key=action_result["template_key"], current_form=None, current_step=None, response_text=action_result.get("response_text"))
    if intent == "reset_password":
        return ConverseResponse(intent=intent, confidence=confidence, entities=entities, slots=slots, response_text="I can help with password-reset guidance. The verified reset workflow is being connected.")
    if intent == "greet":
        response = "Hello! I am your VARIO IT Support Assistant. I can check a ticket status, help raise a ticket, or guide you to password-reset support."
    else:
        response = "Thanks for contacting IT Support. Have a good day!"
    return ConverseResponse(intent=intent, confidence=confidence, entities=entities, slots=slots, response_text=response)


def _is_confirm(message: str) -> bool:
    clean = " ".join(message.casefold().strip().split())
    return clean in {"confirm", "yes", "yes create it", "create it", "submit", "proceed", "looks good", "go ahead"}


def _is_cancel(message: str) -> bool:
    clean = " ".join(message.casefold().strip().split())
    return clean in {"cancel", "no", "no thanks", "don't create", "do not create", "discard", "stop", "never mind", "nevermind"}


def _ticket_signature(reporter: str, category: str, description: str) -> str:
    import hashlib
    normalized = "|".join((reporter.strip().casefold(), category.strip().casefold(), " ".join(description.strip().casefold().split())))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _cleared_ticket_slots(slots: Dict[str, Any], *, clear_dedupe: bool) -> Dict[str, Any]:
    cleared = dict(slots)
    for key in ("category", "description", "reporter", "requested_slot", "confirmation_pending", "ticket_id", "ticket_result", "ticket_reused"):
        cleared[key] = None
    if clear_dedupe:
        cleared["last_created_signature"] = None
        cleared["last_created_ticket_id"] = None
    return cleared


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5006)
