import os
import sys
import asyncio
import logging
from typing import Any, Text, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger("rasa_admissions_actions")

try:
    from rasa_sdk import Action, Tracker
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.events import SlotSet
    HAS_RASA_SDK = True
except ImportError:
    HAS_RASA_SDK = False

    class Action:  # type: ignore
        pass

    class Tracker:  # type: ignore
        pass

    class CollectingDispatcher:  # type: ignore
        pass

    def SlotSet(key: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {"event": "slot", "name": key, "value": value}

# Import AdmissionsAdapter from inside the pack (slice-39, B2b)
try:
    from actions.admissions_adapter import (
        AdmissionsAdapter,
        ApplicationNotFoundError,
        ProgramNotFoundError,
        BackendUnavailableError,
    )
except ImportError:
    try:
        from admissions_adapter import (
            AdmissionsAdapter,
            ApplicationNotFoundError,
            ProgramNotFoundError,
            BackendUnavailableError,
        )
    except ImportError:
        # Fallback if running from root
        from rasa_admissions.actions.admissions_adapter import (
            AdmissionsAdapter,
            ApplicationNotFoundError,
            ProgramNotFoundError,
            BackendUnavailableError,
        )


class ActionCheckApplicationStatus(Action):
    """
    Custom action for checking application status (slice-24, slice-39).
    Extracts the application_id entity, calls AdmissionsAdapter.get_application_status,
    and returns template_key, slots, and ADR-006 card payload.
    """

    TEMPLATE_KEY = "check_application_status_response"
    TEMPLATE_KEY_NOT_FOUND = "check_application_status_not_found_response"

    def name(self) -> Text:
        return "action_check_application_status"

    def extract_application_id(self, tracker: Any) -> Optional[str]:
        """Extracts application_id from slot or extracted entities."""
        if hasattr(tracker, "get_slot"):
            app_id = tracker.get_slot("application_id")
            if app_id:
                return str(app_id).strip().upper()

        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            entities = tracker.latest_message.get("entities", [])
            for ent in entities:
                if ent.get("entity") == "application_id":
                    return str(ent.get("value", "")).strip().upper()

        if isinstance(tracker, dict):
            if "application_id" in tracker.get("slots", {}):
                return str(tracker["slots"]["application_id"]).strip().upper()
            for ent in tracker.get("entities", []):
                if ent.get("entity") == "application_id":
                    return str(ent.get("value", "")).strip().upper()

        return None

    async def execute_logic_async(self, application_id: Optional[str]) -> Dict[str, Any]:
        """
        Asynchronously fetches application status from mock-admissions service.
        Returns template_key, slots, response_text, and card.
        """
        app_id_clean = (application_id or "").strip().upper()
        if not app_id_clean:
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "application_id",
                "response_text": "Please provide your application ID (e.g. APP-1001) so I can check your status.",
                "card": {
                    "type": "slot_prompt",
                    "text": "Please provide your application ID (e.g. APP-1001) so I can check your status.",
                    "options": [],
                },
            }

        try:
            data = await AdmissionsAdapter.get_application_status(
                app_id_clean, raise_for_not_found=False
            )
        except BackendUnavailableError:
            return {
                "template_key": None,
                "slots": {"application_id": app_id_clean, "found": False, "service_unavailable": True},
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        if data.get("found", True) and data.get("status") != "Not Found":
            card_rows = [
                {"label": "Application ID", "value": data.get("application_id", app_id_clean)},
                {"label": "Status", "value": data.get("status", "Under Review")},
                {"label": "Next Step", "value": data.get("next_step", "")},
            ]
            if data.get("applicant_name"):
                card_rows.append({"label": "Applicant", "value": data["applicant_name"]})
            if data.get("program"):
                card_rows.append({"label": "Program", "value": data["program"]})
            if data.get("fee_status"):
                card_rows.append({"label": "Fee Status", "value": data["fee_status"]})

            return {
                "template_key": self.TEMPLATE_KEY,
                "slots": {
                    "application_id": data.get("application_id", app_id_clean),
                    "status": data.get("status", "Under Review"),
                    "next_step": data.get("next_step", "Application is being reviewed."),
                    "applicant_name": data.get("applicant_name", ""),
                    "program": data.get("program", ""),
                    "fee_status": data.get("fee_status", ""),
                    "found": True,
                },
                "response_text": f"Application {data.get('application_id', app_id_clean)} for {data.get('applicant_name', 'Applicant')} ({data.get('program', 'Program')}) is currently {data.get('status', 'Under Review')}. Next step: {data.get('next_step', '')}",
                "card": {
                    "type": "data_card",
                    "title": f"Application {data.get('application_id', app_id_clean)} Status",
                    "rows": card_rows,
                },
            }
        else:
            suggested = data.get(
                "suggested_next_step",
                "Please verify your application ID or contact admissions@org.example.com.",
            )
            return {
                "template_key": self.TEMPLATE_KEY_NOT_FOUND,
                "slots": {
                    "application_id": app_id_clean,
                    "status": "Not Found",
                    "suggested_next_step": suggested,
                    "found": False,
                },
                "response_text": f"Application {app_id_clean} was not found. Suggested next step: {suggested}",
                "card": {
                    "type": "not_found",
                    "title": f"Application {app_id_clean} Not Found",
                    "text": f"Application {app_id_clean} was not found.",
                    "suggested_action": suggested,
                },
            }

    def execute_logic(self, application_id: Optional[str]) -> Dict[str, Any]:
        """Synchronous entrypoint bridging to execute_logic_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.execute_logic_async(application_id)).result()
        return asyncio.run(self.execute_logic_async(application_id))

    async def run(
        self,
        dispatcher: Any,
        tracker: Any,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        app_id = self.extract_application_id(tracker)
        result = await self.execute_logic_async(app_id)

        events = []
        for key, val in result.get("slots", {}).items():
            events.append(SlotSet(key, val))

        if hasattr(dispatcher, "utter_message"):
            if result.get("response_text"):
                dispatcher.utter_message(text=result["response_text"])
            vario_json = {
                "vario": {
                    "template_key": result.get("template_key"),
                    "slots": result.get("slots") or {},
                    "card": result.get("card"),
                }
            }
            dispatcher.utter_message(json_message=vario_json)

        return events


class ActionGetDocumentChecklist(Action):
    """
    Custom action for retrieving document checklist by degree program (slice-25, slice-39).
    Extracts program entity/slot, queries AdmissionsAdapter, and returns template_key + list card.
    """

    TEMPLATE_KEY = "get_document_checklist_response"
    TEMPLATE_KEY_NOT_FOUND = "get_document_checklist_not_found_response"

    def name(self) -> Text:
        return "action_get_document_checklist"

    def extract_program(self, tracker: Any) -> Optional[str]:
        """Extracts program from slot or extracted entities."""
        if hasattr(tracker, "get_slot"):
            prog = tracker.get_slot("program")
            if prog:
                return str(prog).strip()

        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            entities = tracker.latest_message.get("entities", [])
            for ent in entities:
                if ent.get("entity") == "program":
                    return str(ent.get("value", "")).strip()

        if isinstance(tracker, dict):
            if "program" in tracker.get("slots", {}):
                return str(tracker["slots"]["program"]).strip()
            for ent in tracker.get("entities", []):
                if ent.get("entity") == "program":
                    return str(ent.get("value", "")).strip()

        return None

    async def execute_logic_async(self, program: Optional[str]) -> Dict[str, Any]:
        """
        Asynchronously fetches document checklist from mock-admissions service.
        """
        prog_clean = (program or "").strip().lower()
        if not prog_clean:
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "program",
                "current_form": "checklist_form",
                "current_step": "await_program",
                "response_text": "Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)",
                "card": {
                    "type": "slot_prompt",
                    "text": "Which program would you like the document checklist for?",
                    "options": [
                        {"label": "B.Tech", "value": "B.Tech"},
                        {"label": "M.Tech", "value": "M.Tech"},
                        {"label": "MBA", "value": "MBA"},
                    ],
                },
            }

        try:
            data = await AdmissionsAdapter.get_document_checklist(
                prog_clean, raise_for_not_found=False
            )
        except BackendUnavailableError:
            return {
                "template_key": None,
                "slots": {"program": prog_clean, "found": False, "service_unavailable": True},
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        if data.get("found", True) and data.get("required_documents"):
            docs = data["required_documents"]
            summary = ", ".join(docs)
            prog_name = data.get("program", prog_clean)
            return {
                "template_key": self.TEMPLATE_KEY,
                "slots": {
                    "program": prog_name,
                    "required_documents": docs,
                    "items_summary": summary,
                    "found": True,
                },
                "missing_slot": None,
                "response_text": f"Here are the required documents for {prog_name}: {summary}",
                "card": {
                    "type": "list",
                    "title": f"Required Documents — {prog_name}",
                    "items": docs,
                },
            }
        else:
            avail = data.get(
                "available_programs",
                ["Computer Science (B.Tech)", "Data Science (M.Tech)", "MBA"],
            )
            avail_str = ", ".join(avail)
            return {
                "template_key": self.TEMPLATE_KEY_NOT_FOUND,
                "slots": {
                    "program": prog_clean,
                    "available_programs": avail,
                    "found": False,
                },
                "missing_slot": None,
                "response_text": f"No document checklist found for program '{program}'. Available programs: {avail_str}.",
                "card": {
                    "type": "not_found",
                    "title": f"Checklist Not Found",
                    "text": f"No document checklist found for program '{program}'.",
                    "suggested_action": f"Available programs: {avail_str}.",
                },
            }

    def execute_logic(self, program: Optional[str]) -> Dict[str, Any]:
        """Synchronous entrypoint bridging to execute_logic_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.execute_logic_async(program)).result()
        return asyncio.run(self.execute_logic_async(program))

    async def run(
        self,
        dispatcher: Any,
        tracker: Any,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        prog = self.extract_program(tracker)
        result = await self.execute_logic_async(prog)

        events = []
        for key, val in result.get("slots", {}).items():
            events.append(SlotSet(key, val))

        if hasattr(dispatcher, "utter_message"):
            if result.get("response_text"):
                dispatcher.utter_message(text=result["response_text"])
            vario_json = {
                "vario": {
                    "template_key": result.get("template_key"),
                    "slots": result.get("slots") or {},
                    "card": result.get("card"),
                }
            }
            dispatcher.utter_message(json_message=vario_json)

        return events


class ActionAskFeeDeadline(Action):
    """
    Custom action for admissions calendar fees and deadlines (slice-26, slice-39, FR-16).
    Queries AdmissionsAdapter.get_calendar() directly on each invocation.
    Dynamic updates via PUT /calendar show up immediately without restart.
    """

    TEMPLATE_KEY = "ask_fee_deadline_response"

    def name(self) -> Text:
        return "action_ask_fee_deadline"

    def extract_query(self, tracker: Any) -> str:
        """Extracts user message from tracker."""
        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            return str(tracker.latest_message.get("text", "")).strip()
        if isinstance(tracker, dict):
            return str(tracker.get("message", tracker.get("text", ""))).strip()
        return ""

    async def execute_logic_async(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronously fetches calendar data from mock-admissions service.
        """
        q = (query or "").strip().lower()

        # Handle very vague queries needing clarification (AC-4)
        if q in ["when?", "how much?", "fees?", "deadline?", "when", "how much", "fee", "cost?"]:
            return {
                "template_key": None,
                "needs_clarification": True,
                "slots": {},
                "response_text": "Could you please clarify whether you are asking about tuition fees, application fees, or application and payment deadlines?",
                "card": {
                    "type": "slot_prompt",
                    "text": "Could you please clarify whether you are asking about tuition fees, application fees, or application and payment deadlines?",
                    "options": [
                        {"label": "Tuition Fees", "value": "tuition fee"},
                        {"label": "Application Fee", "value": "application fee"},
                        {"label": "Deadlines", "value": "application deadline"},
                    ],
                },
            }

        try:
            calendar_data = await AdmissionsAdapter.get_calendar()
        except BackendUnavailableError:
            return {
                "template_key": None,
                "slots": {"found": False, "service_unavailable": True},
                "service_unavailable": True,
                "response_text": "The admissions system is unavailable, please try again later.",
                "card": {
                    "type": "error",
                    "text": "The admissions system is unavailable, please try again later.",
                },
            }

        academic_year = calendar_data.get("academic_year", "2026-2027")
        all_fees = calendar_data.get("fees", [])
        all_deadlines = calendar_data.get("deadlines", [])
        refund_policy = calendar_data.get("refund_policy", "")
        contact = calendar_data.get("contact", {})

        is_refund = any(k in q for k in ["refund", "cancellation", "withdraw"])
        is_fee = any(k in q for k in ["fee", "tuition", "cost", "how much", "deposit", "hostel", "caution", "payment", "pay"])
        is_deadline = any(k in q for k in ["deadline", "last date", "when", "date", "dates", "merit", "commence", "orientation", "timeline", "schedule"])

        matched_fees = []
        matched_deadlines = []

        if is_refund and not is_deadline and not ("fee" in q and "tuition" in q):
            details = f"Refund Policy: {refund_policy}"
            return {
                "template_key": self.TEMPLATE_KEY,
                "slots": {
                    "academic_year": academic_year,
                    "topic": "refund",
                    "details": details,
                    "refund_policy": refund_policy,
                    "contact": contact,
                    "found": True,
                },
                "response_text": f"According to the {academic_year} admissions calendar: {details}",
                "card": {
                    "type": "data_card",
                    "title": f"Admissions Refund Policy ({academic_year})",
                    "rows": [
                        {"label": "Refund Policy", "value": refund_policy},
                    ],
                },
            }

        # Match specific fees
        if "btech" in q or "b.tech" in q or "computer science" in q:
            matched_fees = [f for f in all_fees if "Computer Science" in f.get("item", "")]
        elif "mtech" in q or "m.tech" in q or "data science" in q:
            matched_fees = [f for f in all_fees if "Data Science" in f.get("item", "")]
        elif "mba" in q:
            matched_fees = [f for f in all_fees if "MBA" in f.get("item", "")]
        elif "hostel" in q or "caution" in q:
            matched_fees = [f for f in all_fees if "Hostel" in f.get("item", "")]
        elif "application fee" in q or ("application" in q and "fee" in q and not is_deadline):
            matched_fees = [f for f in all_fees if "Application Fee" in f.get("item", "")]
        elif is_fee and not is_deadline:
            matched_fees = list(all_fees)

        # Match specific deadlines
        if "second merit" in q:
            matched_deadlines = [d for d in all_deadlines if "Second Merit" in d.get("milestone", "")]
        elif "first merit" in q or "merit list" in q:
            matched_deadlines = [d for d in all_deadlines if "Merit List" in d.get("milestone", "")]
        elif "verification" in q or "document" in q:
            matched_deadlines = [d for d in all_deadlines if "Document Verification" in d.get("milestone", "")]
        elif "orientation" in q or "classes" in q or "commence" in q or "commencement" in q:
            matched_deadlines = [d for d in all_deadlines if "Orientation" in d.get("milestone", "")]
        elif "spot round" in q:
            matched_deadlines = [d for d in all_deadlines if "Spot Round" in d.get("milestone", "")]
        elif "submit" in q or "submission" in q or "application deadline" in q or "last date to submit" in q or "last date for admission application" in q:
            matched_deadlines = [d for d in all_deadlines if "Submission Deadline" in d.get("milestone", "")]
        elif is_deadline and not is_fee:
            matched_deadlines = list(all_deadlines)

        # Fallback for general inquiries
        if not matched_fees and not matched_deadlines:
            if is_fee:
                matched_fees = list(all_fees)
            if is_deadline:
                matched_deadlines = list(all_deadlines)
            if not is_fee and not is_deadline:
                matched_fees = list(all_fees)
                matched_deadlines = list(all_deadlines)

        rows = []
        if matched_fees and not matched_deadlines:
            topic = "fee"
            details = "; ".join(f"{f['item']}: {f['amount']}" for f in matched_fees)
            rows = [{"label": f["item"], "value": f["amount"]} for f in matched_fees]
        elif matched_deadlines and not matched_fees:
            topic = "deadline"
            details = "; ".join(f"{d['milestone']}: {d['date']}" for d in matched_deadlines)
            rows = [{"label": d["milestone"], "value": d["date"]} for d in matched_deadlines]
        else:
            topic = "general"
            fee_str = "; ".join(f"{f['item']}: {f['amount']}" for f in matched_fees[:3])
            dl_str = "; ".join(f"{d['milestone']}: {d['date']}" for d in matched_deadlines[:3])
            details = f"Important Deadlines: {dl_str}. Fees: {fee_str}"
            rows = [{"label": d["milestone"], "value": d["date"]} for d in matched_deadlines[:3]] + [
                {"label": f["item"], "value": f["amount"]} for f in matched_fees[:3]
            ]

        slots_payload: Dict[str, Any] = {
            "academic_year": academic_year,
            "topic": topic,
            "details": details,
            "found": True,
            "contact": contact,
        }
        if matched_fees:
            slots_payload["fees"] = matched_fees
        if matched_deadlines:
            slots_payload["deadlines"] = matched_deadlines
        if is_refund:
            slots_payload["refund_policy"] = refund_policy

        return {
            "template_key": self.TEMPLATE_KEY,
            "slots": slots_payload,
            "response_text": f"According to the {academic_year} admissions calendar: {details}",
            "card": {
                "type": "data_card",
                "title": f"Admissions Calendar ({academic_year})",
                "rows": rows,
            },
        }

    def execute_logic(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous entrypoint bridging to execute_logic_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.execute_logic_async(query)).result()
        return asyncio.run(self.execute_logic_async(query))

    async def run(
        self,
        dispatcher: Any,
        tracker: Any,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        query = self.extract_query(tracker)
        result = await self.execute_logic_async(query)

        events = []
        for key, val in result.get("slots", {}).items():
            events.append(SlotSet(key, val))

        if hasattr(dispatcher, "utter_message"):
            if result.get("response_text"):
                dispatcher.utter_message(text=result["response_text"])
            vario_json = {
                "vario": {
                    "template_key": result.get("template_key"),
                    "slots": result.get("slots") or {},
                    "card": result.get("card"),
                }
            }
            dispatcher.utter_message(json_message=vario_json)

        return events
