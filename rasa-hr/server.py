"""
Rasa HR Role Pack Runtime Server.

Dual-mode architecture:
1. Live Rasa Mode: When RASA_NLU_URL is configured, proxies classification to the actual
   trained Rasa Open Source NLU engine (/model/parse).
2. Scoped Development Mock Mode: When RASA_NLU_URL is unset (e.g. in local unit tests and CI
   before OCI deployment in Slice 29), operates as a scoped rule-based mock implementing
   the ADR-002 converse webhook contract.

Adheres strictly to docs/decisions/ADR-002-rasa-chat-contract.md.
"""
import os
import re
import logging
from typing import Dict, Any, Optional, List
import httpx
from fastapi import FastAPI, Request, status
from pydantic import BaseModel

from actions.actions import ActionCheckLeaveBalance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_hr_server")

app = FastAPI(
    title="Rasa HR Role Pack Runtime",
    description="Implements ADR-002 converse webhook for HR NLU and dialogue.",
    version="1.0.0",
)

action_handler = ActionCheckLeaveBalance()

# Regex for employee IDs (e.g. EMP-1042)
EMP_ID_REGEX = re.compile(r"\b(EMP-\d{4})\b", re.IGNORECASE)

LEAVE_TYPES = ["annual", "sick", "casual", "maternity", "paternity", "pto", "vacation"]
POLICY_TOPICS = ["maternity", "paternity", "sick", "annual", "casual", "bereavement", "carryover", "carry forward"]

KEYWORDS_STATUS = [
    "status", "approved", "approval", "pending", "track", "progress",
    "decision", "rejected"
]
KEYWORDS_REQUEST = [
    "apply", "submit", "request", "book", "take off", "take vacation",
    "taking leave", "need leave", "apply for"
]
KEYWORDS_POLICY = [
    "policy", "policies", "rules", "rule", "guidelines", "guideline", "carryover",
    "carry forward", "entitled", "entitlement", "allowance", "maternity", "paternity",
    "bereavement", "benefit", "benefits"
]
KEYWORDS_BALANCE = [
    "balance", "how many", "how much", "remaining", "left", "available",
    "days off", "pto", "paid time off", "vacation days", "leave quota",
    "time off left", "leave allowance"
]
KEYWORDS_GREET = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]
KEYWORDS_BYE = ["bye", "goodbye", "see you", "farewell", "thanks bye"]


class SessionState(BaseModel):
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    slots: Dict[str, Any] = {}


class ConverseRequest(BaseModel):
    sender: str
    message: str
    session: Optional[SessionState] = None


class ConverseResponse(BaseModel):
    intent: Optional[str]
    confidence: float
    entities: Dict[str, Any] = {}
    template_key: Optional[str] = None
    slots: Dict[str, Any] = {}
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None


def classify_message_local(
    text: str, current_form: Optional[str] = None
) -> tuple[str, float, Dict[str, Any]]:
    """
    Deterministic rule-based development mock for HR NLU.
    Emulates Rasa DIETClassifier and FallbackClassifier behaviour for local testing.
    """
    clean = text.strip().lower()

    # Extract employee_id entity
    entities: Dict[str, Any] = {}
    emp_match = EMP_ID_REGEX.search(text)
    if emp_match:
        entities["employee_id"] = emp_match.group(1).upper()

    # Extract leave_type entity
    for lt in LEAVE_TYPES:
        if re.search(rf"\b{lt}\b", clean):
            entities["leave_type"] = lt
            break

    # Extract policy_topic entity
    for topic in POLICY_TOPICS:
        if re.search(rf"\b{topic}\b", clean):
            entities["policy_topic"] = topic
            break

    # 1. Greetings
    if any(clean == g or clean.startswith(g + " ") for g in KEYWORDS_GREET):
        return "greet", 0.96, entities

    # 2. Goodbye
    if any(clean == b or clean.startswith(b + " ") for b in KEYWORDS_BYE):
        return "goodbye", 0.95, entities

    # 3. Check for ambiguous / conflicting utterances
    has_apply = any(kw in clean for kw in KEYWORDS_REQUEST)
    has_status = any(kw in clean for kw in KEYWORDS_STATUS)
    has_balance = any(kw in clean for kw in KEYWORDS_BALANCE) or any(
        kw in clean for kw in ["days left", "days remaining", "time left"]
    )
    has_policy = any(kw in clean for kw in KEYWORDS_POLICY)

    # Conflicting intents in a single utterance (e.g. "apply for leave status balance")
    intent_actions_count = sum([has_apply, has_status, has_balance, has_policy])
    if intent_actions_count > 2:
        return "nlu_fallback", 0.25, entities

    # Vague / ambiguous short utterances without clear action
    if clean in ["leave", "leaves", "time off", "vacation", "pto"] or clean in [
        "help with leave", "leave help", "need leave assistance", "help with my leave"
    ]:
        return "nlu_fallback", 0.25, entities

    # 4. Policy FAQ edge cases (e.g. "What is the maternity policy?", "maternity leave policy")
    # Must evaluate BEFORE balance check so policy queries don't get misclassified as leave balance
    if has_policy or ("policy_topic" in entities and any(w in clean for w in ["policy", "rule", "rules", "guideline", "guidelines", "benefit", "benefits", "how does", "what is"])):
        if not ("balance" in clean and not any(p in clean for p in ["policy", "rule", "guideline"])):
            conf = 0.95 if "policy_topic" in entities else 0.90
            return "ask_policy_faq", conf, entities

    # Check for general leave/time-off context
    is_leave_context = (
        any(
            kw in clean
            for kw in [
                "leave", "leaves", "vacation", "pto", "time off", "day off",
                "days off", "days left", "days remaining", "days"
            ]
        )
        or bool(entities)
        or current_form == "check_leave_balance"
    )

    # 5. Leave request submission (e.g. "apply for leave", "request time off")
    if is_leave_context and has_apply and not (has_balance or has_status):
        return "submit_leave_request", 0.88, entities

    # 6. Leave request status (e.g. "status of my leave request", "has my leave been approved")
    if is_leave_context and has_status and not has_balance:
        return "ask_leave_status", 0.88, entities

    # 7. Check leave balance (e.g. "what's my leave balance", "how many leaves left", "check pto")
    if has_balance and (is_leave_context or "leave_type" in entities or "employee_id" in entities or "balance" in clean):
        confidence = 0.96 if "employee_id" in entities or "leave_type" in entities else 0.95
        return "check_leave_balance", confidence, entities

    # 8. Low-confidence / Out-of-scope fallback (FR-2, ADR-002: threshold 0.4)
    return "nlu_fallback", 0.25, entities


def classify_message(
    text: str, current_form: Optional[str] = None
) -> tuple[str, float, Dict[str, Any]]:
    """
    Classifies the user text into an intent, confidence, and entities.
    Invokes upstream Rasa NLU runtime (/model/parse) when RASA_NLU_URL is configured;
    otherwise falls back to the deterministic local development mock.
    """
    rasa_nlu_url = os.getenv("RASA_NLU_URL")
    if rasa_nlu_url:
        try:
            with httpx.Client(timeout=3.0) as client:
                url = rasa_nlu_url.rstrip("/") + "/model/parse"
                resp = client.post(url, json={"text": text})
                if resp.status_code == 200:
                    data = resp.json()
                    intent_data = data.get("intent") or {}
                    intent_name = intent_data.get("name") or "nlu_fallback"
                    confidence = float(intent_data.get("confidence", 0.0))
                    entities_list = data.get("entities") or []
                    entities: Dict[str, Any] = {}
                    for ent in entities_list:
                        entities[ent["entity"]] = ent.get("value")
                    return intent_name, confidence, entities
        except Exception as e:
            logger.warning("Upstream Rasa NLU invocation failed, using local mock: %s", str(e))

    return classify_message_local(text, current_form=current_form)


@app.get("/health")
@app.get("/")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rasa-hr", "port": 5005}


@app.post("/webhooks/vario/converse", response_model=ConverseResponse)
def converse(req: ConverseRequest) -> ConverseResponse:
    """
    Primary conversation entrypoint consumed by backend dialogue-router.
    Adheres strictly to docs/decisions/ADR-002-rasa-chat-contract.md.
    """
    message = req.message
    sender = req.sender
    session = req.session or SessionState()

    intent, confidence, entities = classify_message(message, current_form=session.current_form)

    # Privacy preservation: NEVER log employee IDs, raw message PII, or sensitive slot values.
    logger.info(
        "Converse request processed: intent=%s confidence=%.2f entity_types=%s has_session_slots=%s",
        intent,
        confidence,
        list(entities.keys()),
        bool(session.slots),
    )

    # Low-confidence or ambiguous fallback
    if confidence < 0.4 or intent == "nlu_fallback":
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots=session.slots,
            current_form=session.current_form,
            current_step=session.current_step,
            response_text="I'm sorry, I didn't quite understand that. You can ask me to check your leave balance (e.g. 'what is my leave balance?'), view leave request status, or ask about HR policies.",
        )

    # Leave balance action
    if intent == "check_leave_balance":
        # Resolve employee context from:
        # 1. Extracted entity in current message
        # 2. Existing session slots from previous turns
        # 3. Authenticated sender ID if matching employee ID pattern
        emp_id = (
            entities.get("employee_id")
            or session.slots.get("employee_id")
            or (sender.upper() if re.match(r"^EMP-\d{4}$", sender.strip(), re.IGNORECASE) else None)
        )
        leave_type = entities.get("leave_type") or session.slots.get("leave_type")

        action_res = action_handler.execute_logic(emp_id, leave_type)

        merged_slots = dict(session.slots)
        merged_slots.update(action_res["slots"])

        # If employee_id is missing, prompt for it rather than returning another employee's data.
        if action_res.get("requires_input"):
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots=merged_slots,
                current_form="check_leave_balance",
                current_step="ask_employee_id",
                response_text=action_res["response_text"],
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res["template_key"],
            slots=merged_slots,
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
        )

    # Greeting / Goodbye / Stubs
    return ConverseResponse(
        intent=intent,
        confidence=confidence,
        entities=entities,
        template_key=None,
        slots=session.slots,
        current_form=None,
        current_step=None,
        response_text=f"Intent '{intent}' acknowledged.",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5005, reload=True)
