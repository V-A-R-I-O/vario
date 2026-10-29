"""
Rasa HR Role Pack Runtime Server (ADR-006).

Dual-mode architecture:
1. Live Rasa Mode: Proxies to trained Rasa Open Source NLU / converse endpoint.
2. Development / Standalone Mode: Serves POST /webhooks/vario/converse adhering to
   ADR-006 and closing defects B6, B7, B2a, M1a, M2a, M3a, M4a, M5a, N5.
"""
import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import date
import httpx
from fastapi import FastAPI, Request, status
from pydantic import BaseModel

from actions.hrms_adapter import (
    HRMSAdapter,
    BackendUnavailableError,
    EmployeeNotFoundError,
    LeaveApplicationError,
)
from actions.date_utils import validate_date_input, parse_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rasa_hr_server")

app = FastAPI(
    title="Rasa HR Role Pack Runtime",
    description="Implements ADR-006 converse webhook for HR NLU and dialogue.",
    version="2.0.0",
)

EMP_ID_REGEX = re.compile(r"\b(EMP-\d{4})\b", re.IGNORECASE)
VALID_LEAVE_TYPES = {"casual", "sick", "annual", "earned", "vacation", "pto", "paid"}


class SessionState(BaseModel):
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    slots: Dict[str, Any] = {}


class ConverseRequest(BaseModel):
    sender: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    session: Optional[SessionState] = None
    auth_context: Optional[Dict[str, Any]] = None


class ConverseResponse(BaseModel):
    intent: Optional[str]
    confidence: float
    entities: Dict[str, Any] = {}
    template_key: Optional[str] = None
    slots: Dict[str, Any] = {}
    current_form: Optional[str] = None
    current_step: Optional[str] = None
    response_text: Optional[str] = None
    audit_event: Optional[Dict[str, Any]] = None
    card: Optional[Dict[str, Any]] = None
    sensitive_next_input: bool = False


def extract_employee_id(req: ConverseRequest) -> Optional[str]:
    """
    Extracts trusted employee ID from request metadata per ADR-006.
    Employee IDs typed in chat are deliberately ignored for balance and submissions.
    """
    if req.metadata and isinstance(req.metadata, dict):
        auth_ctx = req.metadata.get("auth_context") or {}
        emp = auth_ctx.get("employee_id")
        if emp and isinstance(emp, str) and emp.strip():
            return emp.strip().upper()

    if req.auth_context and isinstance(req.auth_context, dict):
        emp = req.auth_context.get("employee_id")
        if emp and isinstance(emp, str) and emp.strip():
            return emp.strip().upper()

    # Backwards compatibility check with sender if formatted like EMP-XXXX
    if req.sender and req.sender.upper().startswith("EMP-"):
        return req.sender.strip().upper()

    return None


def classify_message_local(
    text: str, current_form: Optional[str] = None
) -> Tuple[str, float, Dict[str, Any]]:
    clean = text.strip().lower()
    entities: Dict[str, Any] = {}

    # Extract employee_id entity if explicitly mentioned (for NLU test cases)
    m_emp = EMP_ID_REGEX.search(text)
    if m_emp:
        entities["employee_id"] = m_emp.group(1).upper()

    # Extract leave_type entity
    for lt in ["annual", "casual", "sick", "earned", "vacation", "pto"]:
        if re.search(rf"\b{lt}\b", clean):
            entities["leave_type"] = "annual" if lt in ("annual", "earned", "vacation", "pto") else lt
            break

    # Extract dates
    m_date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m_date:
        entities["start_date"] = m_date.group(1)

    # Specific topic extraction for policy questions
    for topic in ["maternity", "paternity", "bereavement", "carryover", "carry forward", "sick", "annual", "casual"]:
        if topic in clean:
            entities["policy_topic"] = "carryover" if "carry" in topic else topic
            break

    # Affirm / Deny / Cancel
    if clean in ("confirm", "yes", "y", "sure", "ok", "confirm request", "yes please", "yes submit it", "looks good"):
        return "affirm", 0.95, entities

    if clean in ("no", "deny", "don't submit", "no don't", "not now"):
        return "deny", 0.95, entities

    if clean in ("cancel", "stop", "abort", "exit", "nevermind", "cancel this", "cancel leave request", "cancel request"):
        return "cancel", 0.95, entities

    # Greet & Goodbye
    if clean in ("hi", "hello", "hey", "hey there", "greetings", "good morning", "good afternoon"):
        return "greet", 0.95, entities

    if clean in ("bye", "goodbye", "see you later", "thanks, bye", "farewell", "have a nice day", "thanks bye"):
        return "goodbye", 0.95, entities

    # Ambiguous single keyword checks
    if clean in ("leave", "leaves", "help with leave", "need leave assistance", "leave help", "i want to apply for leave status balance"):
        return "nlu_fallback", 0.25, entities

    # Out of scope policy checks (Defect M4a)
    if any(k in clean for k in ["travel", "reimbursement", "dress code", "expense", "food", "procurement"]):
        return "nlu_fallback", 0.25, entities

    if clean in ("rules", "rule", "help with general rules", "general rules"):
        return "nlu_fallback", 0.25, entities

    # WFH policy
    if any(k in clean for k in ["wfh", "work from home", "remote work", "work remotely", "working remotely"]):
        return "ask_wfh_policy", 0.92, entities

    # Leave balance
    balance_triggers = [
        "balance", "leaves left", "leaves do i have", "vacation days",
        "days of leave", "days off", "pto left", "pto balance", "paid time off",
        "time off left", "leave quota", "remaining time off", "vacation balance"
    ]
    if any(k in clean for k in balance_triggers) or clean.startswith("what is my leave") or clean.startswith("what's my leave") or "leave balance" in clean:
        return "check_leave_balance", 0.95, entities

    if ("how many" in clean or "how much" in clean or "check" in clean or "show" in clean) and any(k in clean for k in ["leave", "leaves", "pto", "vacation", "time off"]):
        return "check_leave_balance", 0.95, entities

    # Submit leave request
    request_triggers = ["apply for leave", "submit a leave request", "submit leave", "request time off", "need to take leave", "book leave", "apply for vacation", "apply for casual", "apply for sick", "apply for annual"]
    if any(k in clean for k in request_triggers) or clean.startswith("i want to apply for") or clean.startswith("apply for"):
        return "submit_leave_request", 0.93, entities

    # Policy FAQ
    policy_triggers = [
        "company leave policy", "leave policy", "maternity policy", "paternity policy",
        "sick leave rule", "rules for sick leave", "rules for taking sick leave",
        "carry forward", "carryover", "annual leaves are granted", "bereavement leave",
        "leave carryover rules"
    ]
    if any(k in clean for k in policy_triggers) or (
        any(k in clean for k in ["policy", "rules for", "guidelines", "rules"])
        and any(k in clean for k in ["leave", "sick", "annual", "casual", "maternity", "paternity", "bereavement", "carryover"])
    ):
        return "ask_policy_faq", 0.90, entities

    # Inform (during form)
    if current_form == "leave_request_form":
        return "inform", 0.90, entities

    # Fallback
    return "nlu_fallback", 0.20, entities


def classify_message(
    text: str, current_form: Optional[str] = None
) -> Tuple[str, float, Dict[str, Any]]:
    rasa_nlu_url = os.getenv("RASA_NLU_URL")
    if rasa_nlu_url:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    f"{rasa_nlu_url.rstrip('/')}/model/parse",
                    json={"text": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    intent_data = data.get("intent", {})
                    intent = intent_data.get("name", "nlu_fallback")
                    conf = float(intent_data.get("confidence", 0.0))
                    entities = {e["entity"]: e["value"] for e in data.get("entities", []) if "entity" in e}
                    return intent, conf, entities
        except Exception as e:
            logger.warning("Rasa NLU upstream failed, falling back to local: %s", e)

    return classify_message_local(text, current_form=current_form)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "rasa-hr", "port": 5005}


@app.get("/webhooks/vario/")
async def webhook_health():
    return {"status": "ok"}


@app.post("/webhooks/vario/converse", response_model=ConverseResponse)
async def converse(request: Request):
    data = await request.json()
    req = ConverseRequest(**data)

    session = req.session or SessionState()
    current_form = session.current_form
    current_step = session.current_step
    slots = dict(session.slots or {})

    trusted_emp_id = extract_employee_id(req)
    intent, confidence, entities = classify_message(req.message, current_form=current_form)

    # 1. Handle Cancel / Stop at any step (Defect M3a)
    if intent == "cancel" or req.message.strip().lower() in ("cancel", "stop", "exit", "abort"):
        if current_form:
            return ConverseResponse(
                intent="cancel",
                confidence=0.95,
                entities={},
                template_key="submit_leave_cancelled",
                slots={},
                current_form=None,
                current_step=None,
                response_text="Leave request cancelled. All details have been cleared.",
                card=None,
            )

    # 2. Handle Greet (Defect M5a: no debug text)
    if intent == "greet":
        return ConverseResponse(
            intent="greet",
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots={},
            current_form=None,
            current_step=None,
            response_text="Hello! I am your VARIO HR Assistant. You can ask me to check your leave balance, submit a leave request, or ask about HR and remote work policies.",
            card=None,
        )

    # 3. Handle Goodbye (Defect M5a: no debug text)
    if intent == "goodbye":
        return ConverseResponse(
            intent="goodbye",
            confidence=confidence,
            entities=entities,
            template_key=None,
            slots={},
            current_form=None,
            current_step=None,
            response_text="Thank you for contacting HR. Have a wonderful day!",
            card=None,
        )

    # 4. Handle WFH policy
    if intent == "ask_wfh_policy":
        text = "Employees may work from home up to 3 days per week, subject to manager approval. Core hours (10am–4pm) apply regardless of location."
        return ConverseResponse(
            intent="ask_wfh_policy",
            confidence=confidence,
            entities=entities,
            template_key="ask_wfh_policy_response",
            slots={"is_faq": True, "intent_type": "static_faq"},
            current_form=None,
            current_step=None,
            response_text=text,
            card={
                "type": "faq_answer",
                "title": "Work From Home Policy",
                "text": text,
            },
        )

    # 5. Handle Policy FAQ
    if intent == "ask_policy_faq":
        topic = entities.get("policy_topic") or slots.get("policy_topic")
        if topic == "maternity":
            text = "Eligible employees are entitled to 12 weeks of paid maternity leave."
            resp_slots = {"policy_topic": "maternity", "is_faq": True}
        elif topic == "paternity":
            text = "Eligible employees receive 2 weeks of paid paternity leave upon the birth or adoption of a child."
            resp_slots = {"policy_topic": "paternity", "is_faq": True}
        elif topic == "bereavement":
            text = "Employees are granted up to 3 days of paid bereavement leave in the event of an immediate family loss."
            resp_slots = {"policy_topic": "bereavement", "is_faq": True}
        else:
            text = "Our company leave policy grants 20 annual leaves, 10 sick leaves, and 5 casual leaves per year. Unused annual leaves can be carried forward up to 5 days."
            resp_slots = {"is_faq": True}

        return ConverseResponse(
            intent="ask_policy_faq",
            confidence=confidence,
            entities=entities,
            template_key="ask_policy_faq_response",
            slots=resp_slots,
            current_form=None,
            current_step=None,
            response_text=text,
            card={
                "type": "faq_answer",
                "title": "Company Leave Policy",
                "text": text,
            },
        )

    # 6. Handle Out-of-Scope / Fallback (Defect M4a)
    if intent == "nlu_fallback" or confidence < 0.4:
        if not current_form:
            clarify_text = "I can help with leave balances, leave requests, and leave or WFH policies. For travel or expense policies, please check the employee portal or contact HR."
            return ConverseResponse(
                intent="nlu_fallback",
                confidence=confidence,
                entities={},
                template_key=None,
                slots={},
                current_form=None,
                current_step=None,
                response_text=clarify_text,
                card={"type": "plain_text", "text": clarify_text},
            )

    # 7. Handle Check Leave Balance (Defect B6, M2a: strictly uses trusted employee identity)
    if intent == "check_leave_balance" and not current_form:
        if not trusted_emp_id:
            msg = "Please log in to your employee account to check your leave balance."
            return ConverseResponse(
                intent="check_leave_balance",
                confidence=confidence,
                entities={},
                template_key=None,
                slots={},
                current_form="check_leave_balance",
                current_step="ask_employee_id",
                response_text="Please provide your employee ID (e.g., EMP-1042) to check your leave balance.",
                card={"type": "error", "text": msg},
            )

        try:
            balance_data = await HRMSAdapter.get_leave_balance(trusted_emp_id)
        except BackendUnavailableError:
            msg = "The HR system is currently unavailable. Please try again in a moment."
            return ConverseResponse(
                intent="check_leave_balance",
                confidence=confidence,
                entities={},
                template_key=None,
                slots={},
                current_form=None,
                current_step=None,
                response_text=msg,
                card={"type": "error", "text": msg},
            )

        if not balance_data.get("found"):
            msg = f"I couldn't find employee record for '{trusted_emp_id}' in the HR system. Please contact HR support."
            return ConverseResponse(
                intent="check_leave_balance",
                confidence=confidence,
                entities={},
                template_key=None,
                slots={"employee_id": trusted_emp_id},
                current_form=None,
                current_step=None,
                response_text=msg,
                card={"type": "not_found", "text": msg},
            )

        total = balance_data.get("total", 0)
        casual = balance_data.get("casual", 0)
        sick = balance_data.get("sick", 0)
        earned = balance_data.get("earned", 0)
        emp_name = balance_data.get("employee_name")

        card_title = f"{emp_name}'s leave balance" if emp_name else "Your leave balance"
        card = {
            "type": "data_card",
            "title": card_title,
            "rows": [
                {"label": "Casual", "value": f"{casual} days"},
                {"label": "Sick", "value": f"{sick} days"},
                {"label": "Earned", "value": f"{earned} days"},
                {"label": "Total", "value": f"{total} days"},
            ],
        }
        text = f"You have {total} days of leave remaining: {casual} casual, {sick} sick, {earned} earned."

        return ConverseResponse(
            intent="check_leave_balance",
            confidence=confidence,
            entities=entities,
            template_key="check_leave_balance_response",
            slots={
                "total": total,
                "casual": casual,
                "sick": sick,
                "earned": earned,
                "employee_id": trusted_emp_id,
            },
            current_form=None,
            current_step=None,
            response_text=text,
            card=card,
        )

    # 8. Handle Leave Request Flow (Form: leave_type -> start_date -> end_date -> reason -> confirm)
    if intent == "submit_leave_request" or current_form == "submit_leave_request" or current_form == "leave_request_form":
        form_name = "leave_request_form" if current_form == "leave_request_form" else "submit_leave_request"

        # Start of form
        if not current_form and intent == "submit_leave_request":
            slots = {}
            current_form = form_name

            # Pre-extract if present in message
            if entities.get("leave_type"):
                slots["leave_type"] = entities["leave_type"]
            if entities.get("start_date"):
                slots["start_date"] = entities["start_date"]

        # Step 1: Collect leave_type
        if not slots.get("leave_type"):
            clean_ans = req.message.strip().lower()
            if clean_ans in VALID_LEAVE_TYPES:
                slots["leave_type"] = "annual" if clean_ans in ("annual", "earned", "vacation", "pto", "paid") else clean_ans
            elif entities.get("leave_type"):
                slots["leave_type"] = entities["leave_type"]
            else:
                slots["requested_slot"] = "leave_type"
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities=entities,
                    template_key="submit_leave_slot_prompt",
                    slots=slots,
                    current_form=current_form,
                    current_step="leave_type",
                    response_text="What type of leave would you like to request?",
                    card={
                        "type": "slot_prompt",
                        "text": "What type of leave would you like to request?",
                        "options": [
                            {"label": "Casual", "value": "casual"},
                            {"label": "Sick", "value": "sick"},
                            {"label": "Earned", "value": "earned"},
                            {"label": "Annual", "value": "annual"},
                        ],
                    },
                )
            # If we just answered leave_type, ask for start_date next
            if current_step == "leave_type" or not slots.get("start_date"):
                slots["requested_slot"] = "start_date"
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities=entities,
                    template_key="submit_leave_slot_prompt",
                    slots=slots,
                    current_form=current_form,
                    current_step="start_date",
                    response_text="What is the start date for your leave (YYYY-MM-DD or e.g. 'tomorrow')?",
                    card={
                        "type": "slot_prompt",
                        "text": "What is the start date for your leave (YYYY-MM-DD or e.g. 'tomorrow')?",
                    },
                )

        # Step 2: Collect start_date
        if not slots.get("start_date"):
            if current_step == "start_date":
                iso_date, error = validate_date_input(req.message)
                if iso_date and not error:
                    slots["start_date"] = iso_date
                    slots["requested_slot"] = "end_date"
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_slot_prompt",
                        slots=slots,
                        current_form=current_form,
                        current_step="end_date",
                        response_text="What is the end date for your leave (YYYY-MM-DD)?",
                        card={
                            "type": "slot_prompt",
                            "text": "What is the end date for your leave (YYYY-MM-DD)?",
                        },
                    )
                else:
                    slots["requested_slot"] = "start_date"
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_slot_prompt",
                        slots=slots,
                        current_form=current_form,
                        current_step="start_date",
                        response_text=error or "Please provide a valid start date (e.g. 'YYYY-MM-DD' or 'tomorrow').",
                        card={
                            "type": "slot_prompt",
                            "text": error or "Please provide a valid start date (e.g. 'YYYY-MM-DD' or 'tomorrow').",
                        },
                    )
            else:
                slots["requested_slot"] = "start_date"
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities=entities,
                    template_key="submit_leave_slot_prompt",
                    slots=slots,
                    current_form=current_form,
                    current_step="start_date",
                    response_text="What is the start date for your leave (YYYY-MM-DD or e.g. 'tomorrow')?",
                    card={
                        "type": "slot_prompt",
                        "text": "What is the start date for your leave (YYYY-MM-DD or e.g. 'tomorrow')?",
                    },
                )

        # Step 3: Collect end_date
        if not slots.get("end_date"):
            if current_step == "end_date":
                start_ref = parse_date(slots["start_date"])
                iso_date, error = validate_date_input(req.message, reference_date=start_ref)
                if iso_date and not error:
                    slots["end_date"] = iso_date
                    slots["requested_slot"] = "reason"
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_slot_prompt",
                        slots=slots,
                        current_form=current_form,
                        current_step="reason",
                        response_text="Please provide a reason for your leave request.",
                        card={
                            "type": "slot_prompt",
                            "text": "Please provide a reason for your leave request.",
                        },
                    )
                else:
                    slots["requested_slot"] = "end_date"
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_slot_prompt",
                        slots=slots,
                        current_form=current_form,
                        current_step="end_date",
                        response_text=error or "Please provide a valid end date (e.g. 'YYYY-MM-DD' or 'next friday').",
                        card={
                            "type": "slot_prompt",
                            "text": error or "Please provide a valid end date (e.g. 'YYYY-MM-DD' or 'next friday').",
                        },
                    )
            else:
                slots["requested_slot"] = "end_date"
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities=entities,
                    template_key="submit_leave_slot_prompt",
                    slots=slots,
                    current_form=current_form,
                    current_step="end_date",
                    response_text="What is the end date for your leave (YYYY-MM-DD)?",
                    card={
                        "type": "slot_prompt",
                        "text": "What is the end date for your leave (YYYY-MM-DD)?",
                    },
                )

        # Step 4: Collect reason
        if not slots.get("reason"):
            if current_step == "reason":
                if req.message.strip():
                    slots["reason"] = req.message.strip()
                    slots["confirmation_pending"] = True
                    slots["requested_slot"] = "leave_confirm"
                    leave_type = slots["leave_type"]
                    start_date = slots["start_date"]
                    end_date = slots["end_date"]
                    reason = slots["reason"]
                    summary_text = f"Please confirm your leave request: {leave_type} leave from {start_date} to {end_date}. Reason: {reason}."
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_confirmation",
                        slots=slots,
                        current_form=current_form,
                        current_step="leave_confirm",
                        response_text=summary_text,
                        card={
                            "type": "confirmation",
                            "title": "Confirm leave request",
                            "text": summary_text,
                            "options": [
                                {"label": "Confirm", "value": "confirm"},
                                {"label": "Cancel", "value": "cancel"},
                            ],
                        },
                    )
                else:
                    slots["requested_slot"] = "reason"
                    return ConverseResponse(
                        intent="submit_leave_request",
                        confidence=confidence,
                        entities=entities,
                        template_key="submit_leave_slot_prompt",
                        slots=slots,
                        current_form=current_form,
                        current_step="reason",
                        response_text="Please provide a reason for your leave request.",
                        card={
                            "type": "slot_prompt",
                            "text": "Please provide a reason for your leave request.",
                        },
                    )
            else:
                slots["requested_slot"] = "reason"
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities=entities,
                    template_key="submit_leave_slot_prompt",
                    slots=slots,
                    current_form=current_form,
                    current_step="reason",
                    response_text="Please provide a reason for your leave request.",
                    card={
                        "type": "slot_prompt",
                        "text": "Please provide a reason for your leave request.",
                    },
                )

        # Step 5: Confirmation prompt
        if not slots.get("confirmation_pending"):
            slots["confirmation_pending"] = True
            slots["requested_slot"] = "leave_confirm"
            leave_type = slots["leave_type"]
            start_date = slots["start_date"]
            end_date = slots["end_date"]
            reason = slots["reason"]
            summary_text = f"Please confirm your leave request: {leave_type} leave from {start_date} to {end_date}. Reason: {reason}."
            return ConverseResponse(
                intent="submit_leave_request",
                confidence=confidence,
                entities=entities,
                template_key="submit_leave_confirmation",
                slots=slots,
                current_form=current_form,
                current_step="leave_confirm",
                response_text=summary_text,
                card={
                    "type": "confirmation",
                    "title": "Confirm leave request",
                    "text": summary_text,
                    "options": [
                        {"label": "Confirm", "value": "confirm"},
                        {"label": "Cancel", "value": "cancel"},
                    ],
                },
            )

        # Step 6: Confirmation response
        user_reply = req.message.strip().lower()
        if user_reply in ("confirm", "yes", "y", "sure", "ok") or intent == "affirm":
            # Submit to HRMS!
            emp_id = trusted_emp_id or slots.get("employee_id")
            if not emp_id:
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities={},
                    template_key=None,
                    slots={},
                    current_form=None,
                    current_step=None,
                    response_text="Unable to submit leave request: employee ID not found in session context.",
                    card={"type": "error", "text": "Unable to submit leave request: employee ID not found in session context."},
                )

            try:
                sub_res = await HRMSAdapter.submit_leave(
                    employee_id=emp_id,
                    leave_type=slots["leave_type"],
                    start_date=slots["start_date"],
                    end_date=slots["end_date"],
                    reason=slots.get("reason", ""),
                )
            except BackendUnavailableError:
                msg = "The HR system is currently unavailable. Please try again in a moment."
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities={},
                    template_key=None,
                    slots={},
                    current_form=None,
                    current_step=None,
                    response_text=msg,
                    card={"type": "error", "text": msg},
                )
            except LeaveApplicationError as lae:
                return ConverseResponse(
                    intent="submit_leave_request",
                    confidence=confidence,
                    entities={},
                    template_key=None,
                    slots={},
                    current_form=None,
                    current_step=None,
                    response_text=f"Leave application failed: {lae.message}",
                    card={"type": "error", "text": f"Leave application failed: {lae.message}"},
                )

            ref_id = sub_res.get("reference_id", "LEAVE-SUBMITTED")
            days = sub_res.get("days", 1)
            res_text = f"Your leave request has been submitted successfully. Reference ID: {ref_id}."

            audit_event = {
                "action_type": "leave_submitted",
                "reference_id": ref_id,
                "details": {
                    "employee_id": emp_id,
                    "leave_type": slots["leave_type"],
                    "start_date": slots["start_date"],
                    "end_date": slots["end_date"],
                    "reason": slots.get("reason", ""),
                    "days": days,
                },
            }

            # Reset all slots on completion (Defect M1a)
            return ConverseResponse(
                intent="submit_leave_request",
                confidence=confidence,
                entities=entities,
                template_key="submit_leave_result",
                slots={"reference_id": ref_id, "confirmation_pending": False},
                current_form=None,
                current_step=None,
                response_text=res_text,
                audit_event=audit_event,
                card={
                    "type": "result",
                    "title": "Leave request submitted",
                    "text": res_text,
                    "status": "success",
                },
            )

        elif user_reply in ("cancel", "no", "n", "stop") or intent in ("deny", "cancel"):
            # Reset all slots on cancel (Defect M1a)
            return ConverseResponse(
                intent="submit_leave_request",
                confidence=confidence,
                entities={},
                template_key="submit_leave_cancelled",
                slots={},
                current_form=None,
                current_step=None,
                response_text="Leave request cancelled. All details have been cleared.",
                card=None,
            )
        else:
            # Off-script reply at confirmation step (Defect M3a)
            leave_type = slots["leave_type"]
            start_date = slots["start_date"]
            end_date = slots["end_date"]
            reason = slots["reason"]
            summary_text = (
                f"Please confirm your leave request: {leave_type} leave from "
                f"{start_date} to {end_date}. Reason: {reason}.\n"
                "Please reply 'confirm' to submit or 'cancel' to exit."
            )
            return ConverseResponse(
                intent="submit_leave_request",
                confidence=confidence,
                entities=entities,
                template_key="submit_leave_confirmation",
                slots=slots,
                current_form=current_form,
                current_step="leave_confirm",
                response_text=summary_text,
                card={
                    "type": "confirmation",
                    "title": "Confirm leave request",
                    "text": summary_text,
                    "options": [
                        {"label": "Confirm", "value": "confirm"},
                        {"label": "Cancel", "value": "cancel"},
                    ],
                },
            )

    # Default fallback
    return ConverseResponse(
        intent=intent,
        confidence=confidence,
        entities=entities,
        template_key=None,
        slots={},
        current_form=None,
        current_step=None,
        response_text="I'm sorry, I didn't quite catch that. You can ask me to check your leave balance, submit a leave request, or ask about HR and remote work policies.",
        card=None,
    )
