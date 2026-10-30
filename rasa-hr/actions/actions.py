import logging
from typing import Any, Dict, List, Optional, Text
from datetime import date

try:
    from rasa_sdk import Action, Tracker, FormValidationAction
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.events import SlotSet, ActiveLoop, EventType
except ImportError:
    # Fallback types for static checking outside rasa-sdk
    class Action:  # type: ignore
        pass

    class FormValidationAction:  # type: ignore
        pass

    class Tracker:  # type: ignore
        pass

    class CollectingDispatcher:  # type: ignore
        pass

    def SlotSet(key: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {"event": "slot", "name": key, "value": value}

    def ActiveLoop(name: Optional[str]) -> Dict[str, Any]:  # type: ignore
        return {"event": "active_loop", "name": name}

import sys
from pathlib import Path

# Ensure rasa-shared is resolvable even when not explicitly on PYTHONPATH
_shared_dir = Path(__file__).resolve().parent.parent.parent / "rasa-shared"
if _shared_dir.exists() and str(_shared_dir) not in sys.path:
    sys.path.insert(0, str(_shared_dir))

try:
    from vario_rasa.contract import vario_payload
except ImportError:
    def vario_payload(template_key: str, card: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"template_key": template_key}
        if card is not None:
            payload["card"] = card
        return payload

try:
    from actions.hrms_adapter import (
        HRMSAdapter,
        BackendUnavailableError,
        EmployeeNotFoundError,
        LeaveApplicationError,
    )
    from actions.date_utils import validate_date_input, parse_date
except ImportError:
    from .hrms_adapter import (
        HRMSAdapter,
        BackendUnavailableError,
        EmployeeNotFoundError,
        LeaveApplicationError,
    )
    from .date_utils import validate_date_input, parse_date

logger = logging.getLogger(__name__)


def _extract_employee_id(tracker: Tracker) -> Optional[str]:
    """
    Extracts the trusted employee ID from message metadata (ADR-006).
    Employee IDs typed in chat are deliberately ignored for balance & submissions.
    """
    latest_msg = tracker.latest_message or {}
    metadata = latest_msg.get("metadata") or {}
    auth_ctx = metadata.get("auth_context") or {}
    emp_id = auth_ctx.get("employee_id")
    if emp_id and isinstance(emp_id, str) and emp_id.strip():
        return emp_id.strip().upper()
    return None


class ActionCheckLeaveBalance(Action):
    """
    Checks leave balance for the authenticated employee via HRMSAdapter.
    Ignores any employee ID typed in chat text (Defect B6, M2a).
    Does NOT preset or pollute leave_type in slots (Defect M1a).
    """

    def name(self) -> Text:
        return "action_check_leave_balance"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        employee_id = _extract_employee_id(tracker)

        if not employee_id:
            msg = "Please log in to your employee account to check your leave balance."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []

        try:
            balance_data = await HRMSAdapter.get_leave_balance(employee_id)
        except BackendUnavailableError:
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []
        except Exception as exc:
            logger.error("Error retrieving leave balance for %s: %s", employee_id, exc)
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []

        if not balance_data.get("found"):
            msg = "I couldn't find your employee record in the HR system. Please contact HR support."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "not_found", "text": msg}
                ),
            )
            return []

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

        response_text = f"You have {total} days of leave remaining: {casual} casual, {sick} sick, {earned} earned."

        dispatcher.utter_message(
            text=response_text,
            json_message=vario_payload(
                template_key="check_leave_balance_response",
                slots={
                    "total": total,
                    "casual": casual,
                    "sick": sick,
                    "earned": earned,
                },
                card=card,
            ),
        )
        return []


class ActionAskLeaveStatus(Action):
    """
    Checks leave request status for the authenticated employee via HRMSAdapter (FR-6, Defect N8).
    Extracts employee ID strictly from auth_context metadata (ADR-006).
    """

    def name(self) -> Text:
        return "action_ask_leave_status"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        employee_id = _extract_employee_id(tracker)

        if not employee_id:
            msg = "Please log in to your employee account to check your leave request status."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []

        ref_filter = tracker.get_slot("reference_id")
        latest_msg = tracker.latest_message or {}
        entities = {e.get("entity"): e.get("value") for e in latest_msg.get("entities", []) if "entity" in e}
        if not ref_filter and entities.get("reference_id"):
            ref_filter = entities["reference_id"]

        try:
            status_data = await HRMSAdapter.get_leave_status(employee_id, reference_id=ref_filter)
        except BackendUnavailableError:
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []
        except Exception as exc:
            logger.error("Error retrieving leave status for %s: %s", employee_id, exc)
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return []

        applications = status_data.get("applications", [])
        if not applications:
            no_req_text = "You do not have any submitted leave applications on record."
            if ref_filter:
                no_req_text = f"Leave request '{ref_filter}' was not found for your account."
            dispatcher.utter_message(
                text=no_req_text,
                json_message=vario_payload(
                    template_key="ask_leave_status_not_found_response",
                    slots={"reference_id": ref_filter or "", "employee_id": employee_id},
                    card={"type": "not_found", "text": no_req_text},
                ),
            )
            return []

        latest_app = applications[-1]
        ref_id = latest_app.get("reference_id", "N/A")
        l_type = latest_app.get("leave_type", "leave").capitalize()
        app_status = latest_app.get("status", "unknown").capitalize()
        s_date = latest_app.get("start_date", "")
        e_date = latest_app.get("end_date", "")
        days = latest_app.get("days", 1)
        reason = latest_app.get("reason", "")

        status_text = f"Your {l_type.lower()} leave request ({ref_id}) from {s_date} to {e_date} is currently {app_status.lower()}."
        card = {
            "type": "data_card",
            "title": f"Leave Request Status: {ref_id}",
            "rows": [
                {"label": "Reference ID", "value": ref_id},
                {"label": "Leave Type", "value": l_type},
                {"label": "Dates", "value": f"{s_date} to {e_date} ({days} days)"},
                {"label": "Status", "value": app_status},
                {"label": "Reason", "value": reason or "N/A"},
            ],
        }

        dispatcher.utter_message(
            text=status_text,
            json_message=vario_payload(
                template_key="ask_leave_status_response",
                slots={
                    "reference_id": ref_id,
                    "leave_type": l_type.lower(),
                    "status": app_status.lower(),
                    "start_date": s_date,
                    "end_date": e_date,
                    "days": days,
                    "employee_id": employee_id,
                },
                card=card,
            ),
        )
        return []


class ActionAskLeaveConfirm(Action):
    """
    Renders the confirmation summary step for leave_request_form.
    Shows details, Confirm / Cancel buttons and confirmation card.
    """

    def name(self) -> Text:
        return "action_ask_leave_confirm"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        leave_type = tracker.get_slot("leave_type") or "leave"
        start_date = tracker.get_slot("start_date") or ""
        end_date = tracker.get_slot("end_date") or ""
        reason = tracker.get_slot("reason") or "None"

        summary_text = (
            f"Please confirm your leave request: {leave_type} leave from "
            f"{start_date} to {end_date}. Reason: {reason}."
        )
        card = {
            "type": "confirmation",
            "title": "Confirm leave request",
            "text": summary_text,
            "options": [
                {"label": "Confirm", "value": "confirm"},
                {"label": "Cancel", "value": "cancel"},
            ],
        }
        dispatcher.utter_message(
            text=summary_text,
            buttons=[
                {"title": "Confirm", "payload": "confirm"},
                {"title": "Cancel", "payload": "cancel"},
            ],
            json_message=vario_payload(
                template_key="submit_leave_confirmation",
                slots={
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "reason": reason,
                    "confirmation_pending": True,
                },
                card=card,
            ),
        )
        return []


class ValidateLeaveRequestForm(FormValidationAction):
    """
    Validates slots for leave_request_form:
    - leave_type: accepts casual, sick, annual, earned (N5)
    - start_date: validates format, no past dates (N5)
    - end_date: validates format, end >= start
    - reason: requires non-empty text
    - leave_confirm: handles confirm, cancel, and re-asks off-script replies (M3a)
    """

    def name(self) -> Text:
        return "validate_leave_request_form"

    async def validate_leave_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not isinstance(slot_value, str):
            dispatcher.utter_message(
                text="Please choose a valid leave type: casual, sick, or annual.",
                json_message=vario_payload(
                    template_key="submit_leave_slot_prompt",
                    card={
                        "type": "slot_prompt",
                        "text": "Please choose a valid leave type: casual, sick, or annual.",
                        "options": [
                            {"label": "Casual", "value": "casual"},
                            {"label": "Sick", "value": "sick"},
                            {"label": "Annual", "value": "annual"},
                        ],
                    },
                ),
            )
            return {"leave_type": None}

        clean = slot_value.strip().lower()
        if clean in ("casual", "sick", "annual", "earned", "vacation", "pto", "paid"):
            norm = "annual" if clean in ("annual", "earned", "vacation", "pto", "paid") else clean
            return {"leave_type": norm}

        dispatcher.utter_message(
            text="Please choose a valid leave type: casual, sick, or annual.",
            json_message=vario_payload(
                template_key="submit_leave_slot_prompt",
                card={
                    "type": "slot_prompt",
                    "text": "Please choose a valid leave type: casual, sick, or annual.",
                    "options": [
                        {"label": "Casual", "value": "casual"},
                        {"label": "Sick", "value": "sick"},
                        {"label": "Annual", "value": "annual"},
                    ],
                },
            ),
        )
        return {"leave_type": None}

    async def validate_start_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        iso_date, error = validate_date_input(str(slot_value))
        if error or not iso_date:
            dispatcher.utter_message(
                text=error or "Please provide a valid start date (e.g. 'YYYY-MM-DD' or 'tomorrow').",
                json_message=vario_payload(
                    template_key="submit_leave_slot_prompt",
                    card={
                        "type": "slot_prompt",
                        "text": error or "Please provide a valid start date (e.g. 'YYYY-MM-DD' or 'tomorrow').",
                    },
                ),
            )
            return {"start_date": None}

        current_end = tracker.get_slot("end_date")
        if current_end:
            end_parsed = parse_date(str(current_end))
            start_parsed = parse_date(iso_date)
            if end_parsed and start_parsed and end_parsed < start_parsed:
                dispatcher.utter_message(
                    text="End date cannot be earlier than the new start date. Please re-enter dates.",
                    json_message=vario_payload(template_key="submit_leave_slot_prompt"),
                )
                return {"start_date": iso_date, "end_date": None}

        return {"start_date": iso_date}

    async def validate_end_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        start_date_str = tracker.get_slot("start_date")
        start_ref = parse_date(start_date_str) if start_date_str else None

        iso_date, error = validate_date_input(str(slot_value), reference_date=start_ref)
        if error or not iso_date:
            dispatcher.utter_message(
                text=error or "Please provide a valid end date (e.g. 'YYYY-MM-DD' or 'next friday').",
                json_message=vario_payload(
                    template_key="submit_leave_slot_prompt",
                    card={
                        "type": "slot_prompt",
                        "text": error or "Please provide a valid end date (e.g. 'YYYY-MM-DD' or 'next friday').",
                    },
                ),
            )
            return {"end_date": None}

        return {"end_date": iso_date}

    async def validate_reason(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            dispatcher.utter_message(
                text="Please provide a brief reason for your leave request.",
                json_message=vario_payload(
                    template_key="submit_leave_slot_prompt",
                    card={
                        "type": "slot_prompt",
                        "text": "Please provide a brief reason for your leave request.",
                    },
                ),
            )
            return {"reason": None}

        return {"reason": str(slot_value).strip()}

    async def validate_leave_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        intent = tracker.latest_message.get("intent", {}).get("name")
        text = (tracker.latest_message.get("text") or "").strip().lower()

        if intent == "affirm" or slot_value is True or text in ("confirm", "yes", "y", "sure", "ok"):
            return {"leave_confirm": True}

        if intent in ("deny", "cancel") or slot_value is False or text in ("cancel", "no", "n", "stop", "abort"):
            dispatcher.utter_message(
                text="Leave request cancelled. Your request has not been submitted.",
                json_message=vario_payload(template_key="submit_leave_cancelled"),
            )
            return {
                "leave_confirm": False,
                "leave_type": None,
                "start_date": None,
                "end_date": None,
                "reason": None,
            }

        # Off-script reply at confirmation step (Defect M3a)
        leave_type = tracker.get_slot("leave_type") or "leave"
        start_date = tracker.get_slot("start_date") or ""
        end_date = tracker.get_slot("end_date") or ""
        reason = tracker.get_slot("reason") or "None"
        summary_text = (
            f"Please confirm your leave request: {leave_type} leave from "
            f"{start_date} to {end_date}. Reason: {reason}.\n"
            "Please reply 'confirm' to submit or 'cancel' to exit."
        )
        card = {
            "type": "confirmation",
            "title": "Confirm leave request",
            "text": summary_text,
            "options": [
                {"label": "Confirm", "value": "confirm"},
                {"label": "Cancel", "value": "cancel"},
            ],
        }
        dispatcher.utter_message(
            text=summary_text,
            buttons=[
                {"title": "Confirm", "payload": "confirm"},
                {"title": "Cancel", "payload": "cancel"},
            ],
            json_message=vario_payload(
                template_key="submit_leave_confirmation",
                slots={
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "reason": reason,
                    "confirmation_pending": True,
                },
                card=card,
            ),
        )
        return {"leave_confirm": None}


class ActionSubmitLeave(Action):
    """
    Submits the confirmed leave request via HRMSAdapter.
    Emits result card and audit_event with logged-in employee ID.
    Resets all form slots on completion or cancellation (Defect M1a).
    """

    def name(self) -> Text:
        return "action_submit_leave"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # If user cancelled during confirmation
        if tracker.get_slot("leave_confirm") is False:
            return [
                SlotSet("leave_type", None),
                SlotSet("start_date", None),
                SlotSet("end_date", None),
                SlotSet("reason", None),
                SlotSet("leave_confirm", None),
                ActiveLoop(None),
            ]

        employee_id = _extract_employee_id(tracker)
        leave_type = tracker.get_slot("leave_type") or "casual"
        start_date = tracker.get_slot("start_date")
        end_date = tracker.get_slot("end_date")
        reason = tracker.get_slot("reason") or ""

        if not employee_id:
            msg = "Unable to submit leave request: employee ID not found in session context."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return [
                SlotSet("leave_type", None),
                SlotSet("start_date", None),
                SlotSet("end_date", None),
                SlotSet("reason", None),
                SlotSet("leave_confirm", None),
                ActiveLoop(None),
            ]

        try:
            res = await HRMSAdapter.submit_leave(
                employee_id=employee_id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
            )
        except BackendUnavailableError:
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return [
                SlotSet("leave_type", None),
                SlotSet("start_date", None),
                SlotSet("end_date", None),
                SlotSet("reason", None),
                SlotSet("leave_confirm", None),
                ActiveLoop(None),
            ]
        except LeaveApplicationError as lae:
            msg = f"Leave application failed: {lae.message}"
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return [
                SlotSet("leave_type", None),
                SlotSet("start_date", None),
                SlotSet("end_date", None),
                SlotSet("reason", None),
                SlotSet("leave_confirm", None),
                ActiveLoop(None),
            ]
        except Exception as exc:
            logger.error("Unexpected error submitting leave: %s", exc)
            msg = "The HR system is currently unavailable. Please try again in a moment."
            dispatcher.utter_message(
                text=msg,
                json_message=vario_payload(
                    card={"type": "error", "text": msg}
                ),
            )
            return [
                SlotSet("leave_type", None),
                SlotSet("start_date", None),
                SlotSet("end_date", None),
                SlotSet("reason", None),
                SlotSet("leave_confirm", None),
                ActiveLoop(None),
            ]

        ref_id = res.get("reference_id", "LEAVE-CONFIRMED")
        days = res.get("days", 1)

        result_text = f"Your leave request has been submitted successfully. Reference ID: {ref_id}."
        card = {
            "type": "result",
            "title": "Leave request submitted",
            "text": result_text,
            "status": "success",
        }
        audit_event = {
            "action_type": "leave_submitted",
            "reference_id": ref_id,
            "details": {
                "employee_id": employee_id,
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "days": days,
            },
        }

        dispatcher.utter_message(
            text=result_text,
            json_message=vario_payload(
                template_key="submit_leave_result",
                slots={
                    "reference_id": ref_id,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days,
                },
                card=card,
                audit_event=audit_event,
            ),
        )

        return [
            SlotSet("leave_type", None),
            SlotSet("start_date", None),
            SlotSet("end_date", None),
            SlotSet("reason", None),
            SlotSet("leave_confirm", None),
            ActiveLoop(None),
        ]


class ActionCancelLeaveRequest(Action):
    """
    Handles user cancellation at any step of the leave request form.
    Clears all form slots and deactivates the form.
    """

    def name(self) -> Text:
        return "action_cancel_leave_request"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text="Leave request cancelled. All details have been cleared.",
            json_message=vario_payload(template_key="submit_leave_cancelled"),
        )
        return [
            SlotSet("leave_type", None),
            SlotSet("start_date", None),
            SlotSet("end_date", None),
            SlotSet("reason", None),
            SlotSet("leave_confirm", None),
            ActiveLoop(None),
        ]
