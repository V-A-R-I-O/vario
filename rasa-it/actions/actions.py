"""Rasa actions for the VARIO IT role pack."""
import hashlib
import re
from typing import Any, Dict, List, Optional, Text

from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import ActiveLoop, SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.itsm_adapter import BackendUnavailableError, IdentityVerificationError, ITSMAdapter, TicketCreationRejectedError
from vario_rasa.contract import vario_payload

TICKET_ID_REGEX = re.compile(r"\b(IT-\d{4})\b", re.IGNORECASE)
EMPLOYEE_ID_REGEX = re.compile(r"\bEMP-\d{4}\b", re.IGNORECASE)
REPORTER_ID_REGEX = re.compile(r"\b(?:EMP-\d{4}|APP-\d{4}-\d{3})\b", re.IGNORECASE)
VALID_CATEGORIES = {"hardware", "software", "network", "access", "email", "other"}


def _auth_context(tracker: Tracker) -> Dict[str, Any]:
    metadata = (tracker.latest_message or {}).get("metadata") or {}
    context = metadata.get("auth_context") or {}
    return context if isinstance(context, dict) else {}


def _clear(*names: str) -> List[SlotSet]:
    return [SlotSet(name, None) for name in names]


class ValidateTicketStatusForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_ticket_status_form"

    def validate_ticket_id(self, slot_value: Any, dispatcher: CollectingDispatcher,
                           tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        match = TICKET_ID_REGEX.search(str(slot_value or ""))
        if not match:
            dispatcher.utter_message(text="That ticket ID doesn't look right. Please enter an ID such as IT-1001.")
            return {"ticket_id": None}
        return {"ticket_id": match.group(1).upper()}


class ActionCheckTicketStatus(Action):
    """Resolve one ticket and emit only that ticket's current result."""
    def name(self) -> Text:
        return "action_check_ticket_status"

    @staticmethod
    async def lookup(ticket_id: Optional[str]) -> Dict[str, Any]:
        match = TICKET_ID_REGEX.search(str(ticket_id or ""))
        if not match:
            return {"text": "Please provide your ticket ID (for example, IT-1001).",
                    "template_key": None, "slots": {}, "card": None}
        clean_id = match.group(1).upper()
        try:
            ticket = await ITSMAdapter.get_ticket_status(clean_id)
        except BackendUnavailableError:
            return {"text": "I can't reach the IT ticket system right now. Please try again shortly.",
                    "template_key": None, "slots": {"ticket_id": clean_id},
                    "card": {"type": "error", "title": "IT system unavailable", "message": "Please try again shortly."}}
        if not ticket.get("found"):
            return {"text": f"I couldn't find ticket {clean_id}. Please check the ID and try again.",
                    "template_key": None, "slots": {"ticket_id": clean_id, "found": False},
                    "card": {"type": "not_found", "title": "Ticket not found",
                             "message": f"No ticket was found for {clean_id}.", "ticket_id": clean_id}}
        slots = {"ticket_id": str(ticket.get("ticket_id") or clean_id).upper(),
                 "status": str(ticket.get("status") or "Unknown"), "found": True}
        for key in ("category", "description", "updated_at"):
            if ticket.get(key):
                slots[key] = str(ticket[key])
        rows = [{"label": "Status", "value": slots["status"]}]
        for key in ("category", "description"):
            if slots.get(key):
                rows.append({"label": key.title(), "value": slots[key]})
        return {"text": f"Ticket {slots['ticket_id']} is currently {slots['status']}.",
                "template_key": "check_ticket_status_response", "slots": slots,
                "card": {"type": "data_card", "title": f"Ticket {slots['ticket_id']}", "rows": rows}}

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        result = await self.lookup(tracker.get_slot("ticket_id"))
        dispatcher.utter_message(text=result["text"], json_message=vario_payload(
            template_key=result["template_key"], slots=result["slots"], card=result["card"]))
        return _clear("ticket_id", "status")


class ValidateRaiseTicketForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_raise_ticket_form"

    def validate_category(self, slot_value: Any, dispatcher: CollectingDispatcher,
                          tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        value = str(slot_value or "").strip().lower()
        if value not in VALID_CATEGORIES:
            dispatcher.utter_message(text="Choose hardware, software, network, access, email, or other.")
            return {"category": None}
        return {"category": value}

    def validate_description(self, slot_value: Any, dispatcher: CollectingDispatcher,
                             tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        value = str(slot_value or "").strip()
        if len(value) < 5 or len(value) > 2000:
            dispatcher.utter_message(text="Please describe the issue in 5–2,000 characters, without passwords or other secrets.")
            return {"description": None}
        return {"description": value}

    def validate_confirmation(self, slot_value: Any, dispatcher: CollectingDispatcher,
                              tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        if slot_value is True or slot_value is False:
            return {"confirmation": slot_value}
        dispatcher.utter_message(text="Please confirm or cancel the ticket request.")
        return {"confirmation": None}


class ActionSubmitRaiseTicket(Action):
    """Create tickets using trusted identity and the FR-13 immediate dedupe signature."""
    def name(self) -> Text:
        return "action_submit_raise_ticket"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        category = str(tracker.get_slot("category") or "").strip()
        description = str(tracker.get_slot("description") or "").strip()
        reporter = str(_auth_context(tracker).get("employee_id") or "").strip().upper()
        reset = _clear("category", "description", "confirmation")
        if tracker.get_slot("confirmation") is not True:
            dispatcher.utter_message(text="Okay, I cancelled the ticket request.")
            return reset
        if not REPORTER_ID_REGEX.fullmatch(reporter):
            dispatcher.utter_message(text="I couldn't verify your signed-in employee identity. Please sign in again.")
            return reset
        signature = hashlib.sha256(
            f"{reporter}|{category.casefold()}|{' '.join(description.casefold().split())}".encode()
        ).hexdigest()
        old_id = tracker.get_slot("last_ticket_id")
        if tracker.get_slot("last_ticket_signature") == signature and old_id:
            ticket_id = str(old_id).upper()
            dispatcher.utter_message(
                text=f"That request was already submitted as ticket {ticket_id}; I haven't created a duplicate.",
                json_message=vario_payload(template_key="raise_ticket_result",
                    slots={"ticket_id": ticket_id, "deduplicated": True},
                    card={"type": "result", "title": "Existing ticket", "ticket_id": ticket_id,
                          "message": "This identical request was already submitted."}))
            return reset
        try:
            ticket = await ITSMAdapter.create_ticket(category, description, reporter)
        except TicketCreationRejectedError as exc:
            dispatcher.utter_message(text=f"The IT system rejected this ticket: {exc}. Please correct the details or cancel.")
            return [
                SlotSet("category", None), SlotSet("description", None),
                SlotSet("confirmation", None), SlotSet("last_ticket_signature", None),
                SlotSet("last_ticket_id", None), ActiveLoop("raise_ticket_form"),
                SlotSet("requested_slot", "category"),
            ]
        except BackendUnavailableError:
            dispatcher.utter_message(text="I can't reach the IT ticket system. Your request was not submitted; please try again shortly.")
            return [SlotSet("confirmation", None), ActiveLoop("raise_ticket_form"),
                    SlotSet("requested_slot", "confirmation")]
        ticket_id = str(ticket["ticket_id"]).strip().upper()
        dispatcher.utter_message(
            text=f"Your support ticket {ticket_id} has been created.",
            json_message=vario_payload(template_key="raise_ticket_result",
                slots={"ticket_id": ticket_id, "status": ticket.get("status", "Open")},
                card={"type": "result", "title": "Ticket created", "ticket_id": ticket_id,
                      "message": f"Your support ticket {ticket_id} has been created."},
                audit_event={"type": "ticket_created", "ticket_id": ticket_id, "reporter": reporter}))
        return reset + [SlotSet("last_ticket_signature", signature), SlotSet("last_ticket_id", ticket_id)]


class ValidateResetPasswordForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_reset_password_form"

    async def validate_employee_id(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                   tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        typed = str(slot_value or "").strip().upper()
        trusted = str(_auth_context(tracker).get("employee_id") or "").strip().upper()
        employee_id = trusted or typed
        if not EMPLOYEE_ID_REGEX.fullmatch(employee_id):
            dispatcher.utter_message(text="Please enter a valid employee ID such as EMP-1001.")
            return {"employee_id": None}
        if trusted and typed and trusted != typed:
            dispatcher.utter_message(text="For your security, password reset is only available for your signed-in employee account.")
            return {"employee_id": None}
        try:
            question = await ITSMAdapter.get_security_question(employee_id)
        except BackendUnavailableError:
            dispatcher.utter_message(text="I can't reach the identity service right now. Please try again shortly.")
            return {"employee_id": None}
        if not question.get("found"):
            dispatcher.utter_message(text="I couldn't find that employee account. Please check the ID.")
            return {"employee_id": None}
        if question.get("locked"):
            dispatcher.utter_message(text="This account has reached the maximum number of verification attempts. Please contact IT Support.")
            return {"employee_id": employee_id, "security_question": question["security_question"],
                    "security_answer": "[locked]", "identity_verified": False,
                    "reset_attempts": 3, "reset_error": "locked"}
        return {"employee_id": employee_id, "security_question": question["security_question"],
                "identity_verified": False, "reset_attempts": 0, "reset_error": None}

    async def validate_security_answer(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                       tracker: Tracker, domain: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = str(tracker.get_slot("employee_id") or "").strip().upper()
        answer = str((tracker.latest_message or {}).get("text") or "")
        if not employee_id or not answer.strip():
            return {"security_answer": None}
        try:
            result = await ITSMAdapter.verify_identity(employee_id, answer)
        except BackendUnavailableError:
            dispatcher.utter_message(text="The identity service is unavailable. No password reset was requested.")
            return {"security_answer": "[unavailable]", "identity_verified": False, "reset_error": "unavailable"}
        if result.get("verified"):
            return {"security_answer": "[verified]", "identity_verified": True,
                    "reset_attempts": 0, "reset_error": None}
        remaining = int(result.get("attempts_remaining", 0))
        if result.get("locked") or remaining <= 0:
            dispatcher.utter_message(text="This account has reached the maximum number of verification attempts. Please contact IT Support.")
            return {"security_answer": "[locked]", "identity_verified": False,
                    "reset_attempts": 3, "reset_error": "locked"}
        dispatcher.utter_message(text=f"That answer didn't match. You have {remaining} attempt(s) remaining.")
        return {"security_answer": None, "identity_verified": False,
                "reset_attempts": 3 - remaining, "reset_error": None}


class ActionAskResetPasswordSecurityAnswer(Action):
    def name(self) -> Text:
        return "action_ask_reset_password_form_security_answer"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        question = str(tracker.get_slot("security_question") or "your configured security question")
        dispatcher.utter_message(text=f"To verify your identity, please answer: {question}",
                                 json_message=vario_payload(sensitive_next_input=True))
        return []


class ActionSubmitResetPassword(Action):
    def name(self) -> Text:
        return "action_submit_reset_password"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        employee_id = str(tracker.get_slot("employee_id") or "").strip().upper()
        error = tracker.get_slot("reset_error")
        if error == "unavailable":
            dispatcher.utter_message(text="The identity service is unavailable, so no password reset was requested.")
        elif error == "locked" or int(tracker.get_slot("reset_attempts") or 0) >= 3:
            dispatcher.utter_message(text="Password reset is locked after three failed verification attempts. Please contact IT Support.")
        elif tracker.get_slot("identity_verified") is not True:
            dispatcher.utter_message(text="Identity verification wasn't completed, so no password reset was requested.")
        else:
            try:
                result = await ITSMAdapter.reset_password(employee_id)
            except (BackendUnavailableError, IdentityVerificationError):
                dispatcher.utter_message(text="I couldn't complete the password reset. Please contact IT Support or try again later.")
            else:
                dispatcher.utter_message(
                    text=f"Password reset has been initiated for {employee_id}.",
                    json_message=vario_payload(template_key="reset_password_result",
                        slots={"employee_id": employee_id, "success": bool(result.get("success"))},
                        card={"type": "result", "title": "Password reset initiated",
                              "message": "Identity verified. Follow your organization's normal sign-in recovery steps."},
                        audit_event={"type": "password_reset_initiated", "employee_id": employee_id}))
        return _clear("employee_id", "security_question", "security_answer", "identity_verified",
                      "reset_attempts", "reset_error")


class ActionCancelForm(Action):
    def name(self) -> Text:
        return "action_cancel_form"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Okay, I've cancelled that request.")
        return [ActiveLoop(None)] + _clear(
            "ticket_id", "status", "category", "description", "confirmation",
            "employee_id", "security_question", "security_answer", "identity_verified",
            "reset_attempts", "reset_error")


class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="I'm sorry, I didn't understand that. You can check a ticket status, raise a support ticket, or get password-reset help.")
        return []
