import re
import logging
from typing import Dict, Any, Optional, List
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

KEYWORDS_STATUS = [
    "status", "approved", "approval", "pending", "track", "progress",
    "decision", "rejected"
]
KEYWORDS_REQUEST = [
    "apply", "submit", "request", "book", "take off", "take vacation",
    "taking leave", "need leave", "apply for"
]
KEYWORDS_POLICY = [
    "policy", "rules", "rule", "guidelines", "guideline", "carryover",
    "carry forward", "entitled", "allowance", "maternity", "paternity",
    "bereavement"
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


def classify_message(text: str) -> tuple[str, float, Dict[str, Any]]:
    """
    Classifies the user text into an intent, confidence, and entities.
    Emulates Rasa DIETClassifier and FallbackClassifier behaviour for HR.
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

    # 1. Greetings
    if any(clean == g or clean.startswith(g + " ") for g in KEYWORDS_GREET):
        return "greet", 0.96, entities

    # 2. Goodbye
    if any(clean == b or clean.startswith(b + " ") for b in KEYWORDS_BYE):
        return "goodbye", 0.95, entities

    # Check for leave/time-off context
    is_leave_context = any(
        kw in clean
        for kw in ["leave", "leaves", "vacation", "pto", "time off", "day off", "days off"]
    )

    # 3. Leave request submission (e.g. "apply for leave", "request time off")
    if is_leave_context and any(kw in clean for kw in KEYWORDS_REQUEST) and not any(kw in clean for kw in ["balance", "status"]):
        return "submit_leave_request", 0.88, entities

    # 4. Leave request status (e.g. "status of my leave request", "has my leave been approved")
    if is_leave_context and any(kw in clean for kw in KEYWORDS_STATUS):
        return "ask_leave_status", 0.88, entities

    # 5. Policy FAQ (e.g. "what is the leave policy", "rules for sick leave")
    if is_leave_context and any(kw in clean for kw in KEYWORDS_POLICY) and "balance" not in clean:
        return "ask_policy_faq", 0.88, entities

    # 6. Check leave balance (e.g. "what's my leave balance", "how many leaves left", "check pto")
    if is_leave_context or any(kw in clean for kw in ["leave balance", "pto balance"]):
        confidence = 0.96 if "employee_id" in entities or "leave_type" in entities else 0.95
        return "check_leave_balance", confidence, entities

    # Standalone balance query with implicit context
    if "balance" in clean and not any(kw in clean for kw in ["account", "bank", "card"]):
        return "check_leave_balance", 0.90, entities

    # 7. Low-confidence / Out-of-scope fallback (FR-2, ADR-002: threshold 0.4)
    return "nlu_fallback", 0.25, entities


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

    intent, confidence, entities = classify_message(message)

    logger.info(
        "Converse called: sender=%s intent=%s confidence=%.2f entities=%s",
        sender, intent, confidence, entities
    )

    # Low-confidence fallback
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
        emp_id = entities.get("employee_id") or session.slots.get("employee_id")
        leave_type = entities.get("leave_type") or session.slots.get("leave_type")
        action_res = action_handler.execute_logic(emp_id, leave_type)

        merged_slots = dict(session.slots)
        merged_slots.update(action_res["slots"])

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res["template_key"],
            slots=merged_slots,
            current_form=None,
            current_step=None,
            response_text=None,
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
