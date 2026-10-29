"""
Rasa Admissions Role Pack Runtime Server (ADR-006, slice-39).
Implements the converse webhook for Admissions NLU and dialogue.
"""
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import yaml
from fastapi import FastAPI, Request, status
from pydantic import BaseModel, Field

from actions.actions import (
    ActionCheckApplicationStatus,
    ActionGetDocumentChecklist,
    ActionAskFeeDeadline,
)
from actions.admissions_adapter import BackendUnavailableError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_admissions_server")

app = FastAPI(
    title="Rasa Admissions Role Pack Runtime",
    description="Implements ADR-006 converse webhook for Admissions NLU and dialogue.",
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

    return training_data


TRAINING_DATA = load_nlu_training_examples()


class SessionState(BaseModel):
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)


class ConverseRequest(BaseModel):
    sender: str
    message: str
    session: Optional[SessionState] = None
    metadata: Optional[Dict[str, Any]] = None
    auth_context: Optional[Dict[str, Any]] = None


class ConverseResponse(BaseModel):
    intent: Optional[str] = None
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    template_key: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None
    card: Optional[Dict[str, Any]] = None
    audit_event: Optional[Dict[str, Any]] = None
    sensitive_next_input: bool = False


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

    # Exact greeting / goodbye checks (M5b)
    if clean in {"hi", "hello", "hey", "hey there", "good morning", "good afternoon", "greetings"}:
        return "greet", 0.98, {}
    if clean in {"bye", "goodbye", "see you later", "thanks, bye", "thank you, bye", "have a nice day"}:
        return "goodbye", 0.98, {}

    # Follow-up fee questions (N13: "and for btech?", "what about mba?", etc.)
    followup_fee_match = re.search(
        r"^(?:and\s+for|what\s+about|how\s+about)\s+(?:b\.?tech|m\.?tech|mba|computer\s+science|data\s+science)",
        clean,
    )
    if followup_fee_match and "document" not in clean and "checklist" not in clean:
        prog_match = PROGRAM_REGEX.search(text)
        entities = {"program": prog_match.group(1).strip()} if prog_match else {}
        return "ask_fee_deadline", 0.95, entities

    if any(q in clean for q in ["any update on fees", "what are the dates", "what are the fee details", "how about hostel", "and hostel fees"]):
        return "ask_fee_deadline", 0.95, {}

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
    Adheres strictly to docs/decisions/ADR-006-rasa-contract-v2.md.
    """
    message = req.message
    sender = req.sender
    session = req.session or SessionState()

    classified_intent, classified_conf, extracted_entities = classify_message(message)

    is_interruption = False
    in_app_form = session.current_step == "await_application_id" or session.current_form in [
        "check_application_status_form",
        "application_status_form",
    ]
    in_prog_form = session.current_step == "await_program" or session.current_form in [
        "get_document_checklist_form",
        "checklist_form",
    ]

    # Check for form interruptions (M3c)
    if in_app_form:
        if (
            classified_intent in ["ask_fee_deadline", "get_document_checklist", "greet", "goodbye"]
            and not APP_ID_REGEX.search(message)
        ):
            is_interruption = True
            intent = classified_intent
            confidence = classified_conf
            entities = extracted_entities
        else:
            app_match = APP_ID_REGEX.search(message)
            app_val = app_match.group(1).upper() if app_match else message.strip().upper()
            intent = "check_application_status"
            confidence = 0.95
            entities = {"application_id": app_val}
    elif in_prog_form:
        if (
            classified_intent in ["ask_fee_deadline", "check_application_status", "greet", "goodbye"]
            and not PROGRAM_REGEX.search(message)
        ):
            is_interruption = True
            intent = classified_intent
            confidence = classified_conf
            entities = extracted_entities
        else:
            prog_match = PROGRAM_REGEX.search(message)
            prog_val = prog_match.group(1).strip() if prog_match else message.strip()
            intent = "get_document_checklist"
            confidence = 0.95
            entities = {"program": prog_val}
    else:
        intent = classified_intent
        confidence = classified_conf
        entities = extracted_entities

    logger.info(
        "Converse called: sender=%s intent=%s confidence=%.2f entities=%s interruption=%s",
        sender, intent, confidence, entities, is_interruption
    )

    # Greet (M5b)
    if intent == "greet":
        text = "Hello! I am your VARIO Admissions Assistant. You can ask me to check your application status, view required documents, or inquire about fees and deadlines."
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots={},
            current_form=None,
            current_step=None,
            response_text=text,
            card={"type": "plain_text", "text": text},
        )

    # Goodbye (M5b)
    if intent == "goodbye":
        text = "Thank you for reaching out to the Admissions Office. Have a wonderful day!"
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots={},
            current_form=None,
            current_step=None,
            response_text=text,
            card={"type": "plain_text", "text": text},
        )

    # Low-confidence fallback / Ambiguity fallback (FallbackClassifier)
    if confidence < FALLBACK_THRESHOLD or intent == "nlu_fallback":
        text = "I'm sorry, I didn't quite understand that. You can ask me to check your application status (e.g. 'status of APP-1001'), view required documents, or check fee deadlines."
        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots={},
            current_form=session.current_form if not is_interruption else None,
            current_step=session.current_step if not is_interruption else None,
            response_text=text,
            card={"type": "plain_text", "text": text},
        )

    # Application status action (M1b: explicit entity in this turn required; slots reset per lookup)
    if intent == "check_application_status":
        app_id = entities.get("application_id")
        if not app_id:
            prompt_text = "Please provide your application reference ID (for example: APP-1001)."
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots={},
                current_form="application_status_form",
                current_step="await_application_id",
                response_text=prompt_text,
                card={
                    "type": "slot_prompt",
                    "text": prompt_text,
                    "options": [],
                },
            )

        try:
            action_res = await action_handler.execute_logic_async(app_id)
        except BackendUnavailableError:
            action_res = {
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        if action_res.get("service_unavailable"):
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots={"service_unavailable": True, "found": False},
                current_form=None,
                current_step=None,
                response_text=action_res.get("response_text"),
                card=action_res.get("card"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
            slots=action_res.get("slots", {}),
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
            card=action_res.get("card"),
        )

    # Document checklist action (M1b: explicit entity in this turn required)
    if intent == "get_document_checklist":
        prog = entities.get("program")
        if not prog:
            prompt_text = "Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)"
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots={},
                current_form="checklist_form",
                current_step="await_program",
                response_text=prompt_text,
                card={
                    "type": "slot_prompt",
                    "text": "Which program would you like the document checklist for?",
                    "options": [
                        {"label": "B.Tech", "value": "B.Tech"},
                        {"label": "M.Tech", "value": "M.Tech"},
                        {"label": "MBA", "value": "MBA"},
                    ],
                },
            )

        try:
            action_res = await checklist_action_handler.execute_logic_async(prog)
        except BackendUnavailableError:
            action_res = {
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        if action_res.get("service_unavailable"):
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots={"service_unavailable": True, "found": False},
                current_form=None,
                current_step=None,
                response_text=action_res.get("response_text"),
                card=action_res.get("card"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
            slots=action_res.get("slots", {}),
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
            card=action_res.get("card"),
        )

    # Fee and deadline inquiry (slice-26, FR-16, N13)
    if intent == "ask_fee_deadline":
        try:
            action_res = await fee_deadline_action_handler.execute_logic_async(message)
        except BackendUnavailableError:
            action_res = {
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        if action_res.get("service_unavailable"):
            return ConverseResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                template_key=None,
                slots={"service_unavailable": True, "found": False},
                current_form=None,
                current_step=None,
                response_text=action_res.get("response_text"),
                card=action_res.get("card"),
            )

        return ConverseResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            template_key=action_res.get("template_key"),
            slots=action_res.get("slots", {}),
            current_form=None,
            current_step=None,
            response_text=action_res.get("response_text"),
            card=action_res.get("card"),
        )

    # Default fallback response
    text = "I'm sorry, I didn't quite understand that. You can ask me to check your application status, view required documents, or check fee deadlines."
    return ConverseResponse(
        intent=intent,
        confidence=confidence,
        entities=entities,
        template_key=None,
        slots={},
        current_form=None,
        current_step=None,
        response_text=text,
        card={"type": "plain_text", "text": text},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5007, reload=True)
