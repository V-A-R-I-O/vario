import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import yaml
from fastapi import FastAPI, Request, status
from pydantic import BaseModel

from actions.actions import ActionCheckApplicationStatus, ActionGetDocumentChecklist, ActionAskFeeDeadline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_admissions_server")

app = FastAPI(
    title="Rasa Admissions Role Pack Runtime",
    description="Implements ADR-002 converse webhook for Admissions NLU and dialogue.",
    version="1.0.0",
)

action_handler = ActionCheckApplicationStatus()
checklist_action_handler = ActionGetDocumentChecklist()
fee_deadline_action_handler = ActionAskFeeDeadline()

# Regex for application IDs (e.g. APP-1001)
APP_ID_REGEX = re.compile(r"\b(APP-\d{4})\b", re.IGNORECASE)
PROGRAM_REGEX = re.compile(r"\b(b\.?tech|m\.?tech|mba|computer science|data science)\b", re.IGNORECASE)

# Stopwords for lightweight tokenizer featurization
STOPWORDS = {
    "what", "is", "the", "in", "today", "for", "to", "of", "a", "an", "can",
    "you", "i", "my", "me", "do", "does", "tell", "about", "please", "with",
    "would", "could", "like", "and", "or", "also", "any", "some"
}

# Configured FallbackClassifier thresholds from config.yml
FALLBACK_THRESHOLD = 0.4
AMBIGUITY_THRESHOLD = 0.10


def load_nlu_training_examples() -> Dict[str, List[str]]:
    """Loads NLU training phrases from data/nlu.yml to emulate DIET featurization."""
    nlu_file = Path(__file__).parent / "data" / "nlu.yml"
    training_data: Dict[str, List[str]] = {}
    if nlu_file.exists():
        try:
            content = yaml.safe_load(nlu_file.read_text(encoding="utf-8"))
            for item in content.get("nlu", []):
                intent = item.get("intent")
                examples = []
                for line in item.get("examples", "").splitlines():
                    line = line.strip()
                    if line.startswith("- "):
                        clean_line = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", line[2:]).strip().lower()
                        if clean_line:
                            examples.append(clean_line)
                if intent:
                    training_data[intent] = examples
        except Exception as e:
            logger.warning("Could not parse nlu.yml: %s. Using default examples.", e)

    if not training_data:
        training_data = {
            "check_application_status": [
                "what is the status of application app-1001",
                "check status of app-1002",
                "track application app-1003",
                "application status app-1004",
                "check application status",
                "i want to check my application status",
            ],
            "get_document_checklist": [
                "what documents do i need for btech",
                "document checklist for computer science",
                "list of documents needed for admission",
            ],
            "ask_fee_deadline": [
                "when is the last date to pay fees",
                "what are the admission deadlines",
                "how much is the tuition fee for b.tech",
                "what is the last date to submit the application",
                "admission fee structure and payment dates",
                "when does the merit list come out",
                "what is the refund policy for admission fees",
                "when is the document verification deadline",
                "tuition fee for mba program",
                "what is the application fee",
                "how much is the hostel fee",
                "tuition fee for data science mtech",
                "what are the fee deadlines",
                "last date for admission application",
                "important dates and fees for admission",
                "what is the fee refund policy",
                "when do classes commence",
                "orientation date and admission timeline",
                "what is the second merit list deadline",
                "how much is the caution deposit",
            ],
            "greet": ["hello", "hi", "hey", "good morning"],
            "goodbye": ["bye", "goodbye", "see you later"],
        }
    return training_data


TRAINING_DATA = load_nlu_training_examples()


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


def _tokenize(text: str, filter_stops: bool = True) -> set[str]:
    toks = set(re.findall(r"\b\w+\b", text.lower()))
    if filter_stops and len(toks) > 1:
        content_toks = toks - STOPWORDS
        return content_toks if content_toks else toks
    return toks


def classify_message(text: str) -> tuple[str, float, Dict[str, Any]]:
    """
    Classifies the user text into intent, confidence, and entities.
    Emulates the configured Rasa pipeline (WhitespaceTokenizer, CountVectorsFeaturizer,
    DIETClassifier, and FallbackClassifier) from config.yml using data/nlu.yml.
    """
    clean = text.strip().lower()

    # Entity extraction (RegexFeaturizer / DIET)
    entities: Dict[str, Any] = {}
    app_id_match = APP_ID_REGEX.search(text)
    if app_id_match:
        entities["application_id"] = app_id_match.group(1).upper()

    prog_match = PROGRAM_REGEX.search(text)
    if prog_match:
        entities["program"] = prog_match.group(1).strip()
    else:
        # Check for phrase after "for", "in", or "program" when related to documents/checklist/admission
        doc_prog_match = re.search(
            r"(?:for|in)\s+([a-zA-Z0-9\.\(\)\s-]+?)(?:\s+admission|\s+program|\s+checklist|\?|$)",
            text,
            re.IGNORECASE,
        )
        if doc_prog_match:
            candidate = doc_prog_match.group(1).strip()
            if candidate and candidate.lower() not in {"admission", "admissions", "the", "a", "my", "this", "fees", "documents"}:
                entities["program"] = candidate

    user_toks = _tokenize(clean)
    scores: Dict[str, float] = {}

    for intent, examples in TRAINING_DATA.items():
        if intent == "nlu_fallback":
            continue
        max_s = 0.0
        for ex in examples:
            ex_toks = _tokenize(ex)
            if not ex_toks or not user_toks:
                continue
            common = user_toks & ex_toks
            if not common:
                continue
            jaccard = len(common) / len(user_toks | ex_toks)
            overlap = len(common) / len(user_toks)
            s = 0.3 * jaccard + 0.7 * overlap
            if ex == clean or clean.startswith(ex):
                s = 0.98
            elif ex in clean or clean in ex:
                s = max(s, 0.92)
            if s > max_s:
                max_s = s
        scores[intent] = max_s

    # Domain prior: Presence of application_id strongly signals check_application_status
    if "application_id" in entities:
        scores["check_application_status"] = max(scores.get("check_application_status", 0.0), 0.95)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if not ranked or ranked[0][1] == 0.0:
        return "nlu_fallback", 0.15, entities

    top_intent, top_score = ranked[0]
    second_intent, second_score = ranked[1] if len(ranked) > 1 else ("nlu_fallback", 0.0)

    # 1. FallbackClassifier threshold check (threshold: 0.4)
    if top_score < FALLBACK_THRESHOLD:
        return "nlu_fallback", round(top_score, 2), entities

    # 2. FallbackClassifier ambiguity check (ambiguity_threshold: 0.1)
    if second_score >= 0.25 and (top_score - second_score) < AMBIGUITY_THRESHOLD:
        return "nlu_fallback", round(top_score, 2), entities

    # Calibrate confidence score for confident matches
    final_conf = min(0.96, max(top_score, 0.85)) if top_score >= 0.4 else top_score
    return top_intent, round(final_conf, 2), entities


@app.get("/health")
@app.get("/")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rasa-admissions", "port": 5007}


@app.post("/webhooks/vario/converse", response_model=ConverseResponse)
async def converse(req: ConverseRequest) -> ConverseResponse:
    """
    Primary conversation entrypoint consumed by backend dialogue-router.
    Adheres strictly to docs/decisions/ADR-002-rasa-chat-contract.md.
    """
    message = req.message
    sender = req.sender
    session = req.session or SessionState()

    # Multi-turn slot filling if session is currently waiting for a slot in an active form
    if session.current_step == "await_program" or session.current_form == "get_document_checklist_form":
        prog_match = PROGRAM_REGEX.search(message)
        prog_val = prog_match.group(1).strip() if prog_match else message.strip()
        intent = "get_document_checklist"
        confidence = 0.95
        entities = {"program": prog_val}
    elif session.current_step == "await_application_id" or session.current_form == "check_application_status_form":
        app_match = APP_ID_REGEX.search(message)
        app_val = app_match.group(1).upper() if app_match else message.strip().upper()
        intent = "check_application_status"
        confidence = 0.95
        entities = {"application_id": app_val}
    else:
        intent, confidence, entities = classify_message(message)

    logger.info(
        "Converse called: sender=%s intent=%s confidence=%.2f entities=%s",
        sender, intent, confidence, entities
    )

    # Low-confidence fallback / Ambiguity fallback (FallbackClassifier)
    if confidence < FALLBACK_THRESHOLD or intent == "nlu_fallback":
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
        action_res = await action_handler.execute_logic_async(app_id)

        merged_slots = dict(session.slots)
        merged_slots.update(action_res.get("slots", {}))

        # If application ID is missing, prompt for it instead of assuming another user's ID
        if action_res.get("missing_slot") == "application_id":
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots=merged_slots,
                current_form="check_application_status_form",
                current_step="await_application_id",
                response_text=action_res.get("response_text"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
            slots=merged_slots,
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
        )

    # Document checklist action (slice-25)
    if intent == "get_document_checklist":
        prog = entities.get("program") or session.slots.get("program")
        action_res = await checklist_action_handler.execute_logic_async(prog)

        merged_slots = dict(session.slots)
        merged_slots.update(action_res.get("slots", {}))

        # If program is missing, prompt for it (slot prompt)
        if action_res.get("missing_slot") == "program":
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots=merged_slots,
                current_form="get_document_checklist_form",
                current_step="await_program",
                response_text=action_res.get("response_text"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
            slots=merged_slots,
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
        )

    # Fee and deadline inquiry (slice-26)
    if intent == "ask_fee_deadline":
        action_res = await fee_deadline_action_handler.execute_logic_async(message)
        merged_slots = dict(session.slots)
        merged_slots.update(action_res.get("slots", {}))

        # If clarification is requested (AC-4)
        if action_res.get("needs_clarification"):
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots=merged_slots,
                current_form=None,
                current_step=None,
                response_text=action_res.get("response_text"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
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
    uvicorn.run("server:app", host="0.0.0.0", port=5007, reload=True)
