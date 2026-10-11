import re
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, status
from pydantic import BaseModel

from actions.actions import ActionCheckApplicationStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_admissions_server")

app = FastAPI(
    title="Rasa Admissions Role Pack Runtime",
    description="Implements ADR-002 converse webhook for Admissions NLU and dialogue.",
    version="1.0.0",
)

action_handler = ActionCheckApplicationStatus()

# Regex for application IDs (e.g. APP-1001)
APP_ID_REGEX = re.compile(r"\b(APP-\d{4})\b", re.IGNORECASE)

KEYWORDS_STATUS = [
    "status", "application", "app-", "track", "progress",
    "decision", "review", "result", "admitted", "accept", "accepted"
]
KEYWORDS_CHECKLIST = [
    "document", "documents", "checklist", "certificate", "marksheet",
    "transcripts", "requirements", "papers"
]
KEYWORDS_CALENDAR = [
    "fee", "fees", "tuition", "deadline", "deadlines",
    "last date", "merit list", "refund", "cost"
]
KEYWORDS_GREET = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]
KEYWORDS_BYE = ["bye", "goodbye", "see you", "farewell"]


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
    Emulates Rasa DIETClassifier and FallbackClassifier behaviour.
    """
    clean = text.strip().lower()

    # Extract application_id entity
    entities: Dict[str, Any] = {}
    match = APP_ID_REGEX.search(text)
    if match:
        entities["application_id"] = match.group(1).upper()

    # 1. Greetings
    if any(clean == g or clean.startswith(g + " ") for g in KEYWORDS_GREET):
        return "greet", 0.96, entities

    # 2. Goodbye
    if any(clean == b or clean.startswith(b + " ") for b in KEYWORDS_BYE):
        return "goodbye", 0.95, entities

    # 3. Check application status
    if "application_id" in entities or any(kw in clean for kw in KEYWORDS_STATUS):
        confidence = 0.95 if "application_id" in entities else 0.88
        return "check_application_status", confidence, entities

    # 4. Document checklist
    if any(kw in clean for kw in KEYWORDS_CHECKLIST):
        return "get_document_checklist", 0.85, entities

    # 5. Fee / Deadline
    if any(kw in clean for kw in KEYWORDS_CALENDAR):
        return "ask_fee_deadline", 0.85, entities

    # 6. Low-confidence / Out-of-scope fallback (FR-2, ADR-002: threshold 0.4)
    return "nlu_fallback", 0.25, entities


@app.get("/health")
@app.get("/")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rasa-admissions", "port": 5007}


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
            response_text="I'm sorry, I didn't quite understand that. You can ask me to check your application status (e.g. 'status of APP-1001'), view required documents, or check fee deadlines.",
        )

    # Application status action
    if intent == "check_application_status":
        app_id = entities.get("application_id") or session.slots.get("application_id")
        action_res = action_handler.execute_logic(app_id)
        
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
    uvicorn.run("server:app", host="0.0.0.0", port=5007, reload=True)
