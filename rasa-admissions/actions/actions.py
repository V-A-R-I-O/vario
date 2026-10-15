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

# Attempt importing AdmissionsAdapter from backend
try:
    backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from app.services.admissions_adapter import (
        AdmissionsAdapter,
        ApplicationNotFoundError,
        ProgramNotFoundError,
        BackendUnavailableError,
    )
    HAS_ADAPTER = True
except ImportError:
    HAS_ADAPTER = False
    AdmissionsAdapter = None  # type: ignore

# Offline fallback application records (SRS §7: graceful degradation when mock service is offline)
OFFLINE_APPLICATIONS = {
    "APP-1001": {
        "found": True,
        "application_id": "APP-1001",
        "applicant_name": "Aarav Sharma",
        "program": "B.Tech Computer Science",
        "status": "Under Review",
        "next_step": "Document verification in progress. Decision expected by Nov 15.",
        "fee_status": "Paid",
    },
    "APP-1002": {
        "found": True,
        "application_id": "APP-1002",
        "applicant_name": "Diya Patel",
        "program": "M.Tech AI & Data Science",
        "status": "Documents Pending",
        "next_step": "Submit official B.Tech degree certificate and transcripts.",
        "fee_status": "Paid",
    },
    "APP-1003": {
        "found": True,
        "application_id": "APP-1003",
        "applicant_name": "Rohan Gupta",
        "program": "MBA",
        "status": "Admitted",
        "next_step": "Pay acceptance fee of ₹50,000 before Oct 25 to confirm seat.",
        "fee_status": "Pending",
    },
    "APP-1004": {
        "found": True,
        "application_id": "APP-1004",
        "applicant_name": "Sneha Reddy",
        "program": "B.Tech Electronics",
        "status": "Rejected",
        "next_step": "Contact admissions office if you wish to appeal or reapply for next cycle.",
        "fee_status": "N/A",
    },
}


class ActionCheckApplicationStatus(Action):
    """
    Custom action for checking application status (slice-24).
    Extracts the application_id entity, calls AdmissionsAdapter.get_application_status,
    and returns template_key + slots shape.
    """

    TEMPLATE_KEY = "check_application_status_response"
    TEMPLATE_KEY_NOT_FOUND = "check_application_status_not_found_response"

    def name(self) -> Text:
        return "action_check_application_status"

    def extract_application_id(self, tracker: Any) -> Optional[str]:
        """Extracts application_id from slot or extracted entities."""
        # 1. Try tracker slot if available
        if hasattr(tracker, "get_slot"):
            app_id = tracker.get_slot("application_id")
            if app_id:
                return str(app_id).strip().upper()

        # 2. Try latest message entities
        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            entities = tracker.latest_message.get("entities", [])
            for ent in entities:
                if ent.get("entity") == "application_id":
                    return str(ent.get("value", "")).strip().upper()

        # 3. Direct dictionary access fallback
        if isinstance(tracker, dict):
            if "application_id" in tracker.get("slots", {}):
                return str(tracker["slots"]["application_id"]).strip().upper()
            for ent in tracker.get("entities", []):
                if ent.get("entity") == "application_id":
                    return str(ent.get("value", "")).strip().upper()

        return None

    async def execute_logic_async(self, application_id: Optional[str]) -> Dict[str, Any]:
        """
        Asynchronously fetches application status using AdmissionsAdapter.
        Returns template_key, slots, and optional response_text.
        """
        app_id_clean = (application_id or "").strip().upper()
        if not app_id_clean:
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "application_id",
                "response_text": "Please provide your application ID (e.g. APP-1001) so I can check your status.",
            }

        data: Optional[Dict[str, Any]] = None

        if HAS_ADAPTER and AdmissionsAdapter is not None:
            try:
                data = await AdmissionsAdapter.get_application_status(
                    app_id_clean, raise_for_not_found=False
                )
            except Exception as e:
                logger.warning(
                    "AdmissionsAdapter call failed for %s (%s). Falling back to offline data.",
                    app_id_clean, e
                )

        if data is None:
            if app_id_clean in OFFLINE_APPLICATIONS:
                data = OFFLINE_APPLICATIONS[app_id_clean]
            else:
                data = {
                    "found": False,
                    "application_id": app_id_clean,
                    "status": "Not Found",
                    "suggested_next_step": "Please verify your application ID or contact admissions@org.example.com.",
                    "detail": f"Application '{app_id_clean}' not found.",
                }

        if data.get("found", True) and data.get("status") != "Not Found":
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
                "response_text": None,
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
            }

    def execute_logic(self, application_id: Optional[str]) -> Dict[str, Any]:
        """
        Synchronous execution entrypoint.
        Safely bridges to execute_logic_async across sync or running-event-loop contexts.
        """
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
            else:
                dispatcher.utter_message(
                    text=f"Template: {result.get('template_key')} Slots: {result.get('slots')}"
                )

        return events


# Offline fallback document checklists (SRS §7: graceful degradation when mock service is offline)
OFFLINE_CHECKLISTS = {
    "btech": {
        "program": "Computer Science (B.Tech)",
        "aliases": ["btech", "b.tech", "computer science", "cs"],
        "required_documents": [
            "Class 10 Grade Sheet / Birth Certificate",
            "Class 12 / Higher Secondary Marksheet",
            "National/State Entrance Exam Scorecard (JEE / CET)",
            "Transfer Certificate & Conduct Certificate",
            "Valid Government Photo ID (Passport or Aadhaar)",
        ],
    },
    "mtech": {
        "program": "Data Science (M.Tech)",
        "aliases": ["mtech", "m.tech", "data science", "ds"],
        "required_documents": [
            "Undergraduate Degree Certificate & Consolidated Transcripts",
            "GATE / PGCET Scorecard",
            "Curriculum Vitae (CV) / Resume",
            "Statement of Purpose (SOP)",
            "Two Letters of Recommendation (Academic or Professional)",
        ],
    },
    "mba": {
        "program": "MBA",
        "aliases": ["mba", "business administration", "management"],
        "required_documents": [
            "Bachelor's Degree Certificate with Minimum 50% Aggregate",
            "Management Entrance Exam Scorecard (CAT / GMAT / MAT / XAT)",
            "Statement of Purpose (SOP)",
            "Work Experience Certificate (if applicable)",
            "Government Identity Proof",
        ],
    },
}


class ActionGetDocumentChecklist(Action):
    """
    Custom action for retrieving document checklist by degree program (slice-25).
    Extracts program entity/slot, queries AdmissionsAdapter, and returns template_key + list.
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
        Asynchronously fetches document checklist using AdmissionsAdapter.
        If program is missing, prompts for the program.
        If program is not recognized, returns graceful not found.
        """
        prog_clean = (program or "").strip().lower()
        if not prog_clean:
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "program",
                "current_form": "get_document_checklist_form",
                "current_step": "await_program",
                "response_text": "Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)",
            }

        data: Optional[Dict[str, Any]] = None

        if HAS_ADAPTER and AdmissionsAdapter is not None:
            try:
                data = await AdmissionsAdapter.get_document_checklist(
                    prog_clean, raise_for_not_found=False
                )
            except Exception as e:
                logger.warning(
                    "AdmissionsAdapter.get_document_checklist failed for %s (%s). Falling back to offline data.",
                    prog_clean, e
                )

        if data is None:
            # Fallback to offline checklist data
            matched = None
            if prog_clean in OFFLINE_CHECKLISTS:
                matched = OFFLINE_CHECKLISTS[prog_clean]
            else:
                for entry in OFFLINE_CHECKLISTS.values():
                    if prog_clean == entry["program"].lower() or any(
                        alias == prog_clean for alias in entry.get("aliases", [])
                    ):
                        matched = entry
                        break
            if matched:
                data = {
                    "found": True,
                    "program": matched["program"],
                    "required_documents": matched["required_documents"],
                }
            else:
                data = {
                    "found": False,
                    "program": prog_clean,
                    "available_programs": [e["program"] for e in OFFLINE_CHECKLISTS.values()],
                    "detail": f"No checklist found for program '{program}'.",
                }

        if data.get("found", True) and data.get("required_documents"):
            docs = data["required_documents"]
            summary = ", ".join(docs)
            return {
                "template_key": self.TEMPLATE_KEY,
                "slots": {
                    "program": data.get("program", prog_clean),
                    "required_documents": docs,
                    "items_summary": summary,
                    "found": True,
                },
                "missing_slot": None,
                "response_text": f"Here are the required documents for {data.get('program', prog_clean)}: {summary}",
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
            }

    def execute_logic(self, program: Optional[str]) -> Dict[str, Any]:
        """
        Synchronous execution entrypoint.
        Safely bridges to execute_logic_async across sync or running-event-loop contexts.
        """
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
            else:
                dispatcher.utter_message(
                    text=f"Template: {result.get('template_key')} Slots: {result.get('slots')}"
                )

        return events


# Offline fallback calendar (SRS §7: graceful degradation when mock service is offline)
OFFLINE_CALENDAR: Dict[str, Any] = {
    "academic_year": "2026-2027",
    "deadlines": [
        {"milestone": "Regular Application Submission Deadline", "date": "November 30, 2026"},
        {"milestone": "Document Verification Deadline", "date": "December 10, 2026"},
        {"milestone": "First Merit List & Deposit Payment", "date": "December 18, 2026"},
        {"milestone": "Second Merit List & Deposit Payment", "date": "December 28, 2026"},
        {"milestone": "Orientation & Commencement of Classes", "date": "January 15, 2027"},
    ],
    "fees": [
        {"item": "Application Fee (All Programs)", "amount": "₹1,500 (Non-refundable)"},
        {"item": "Computer Science (B.Tech) Annual Tuition", "amount": "₹3,20,000"},
        {"item": "Data Science (M.Tech) Annual Tuition", "amount": "₹2,80,000"},
        {"item": "MBA Annual Tuition", "amount": "₹4,50,000"},
        {"item": "Hostel Fee & Caution Deposit", "amount": "₹75,000 (includes ₹10,000 refundable caution deposit)"},
    ],
    "refund_policy": "100% refund (minus ₹1,000 processing fee) if withdrawal request is submitted at least 15 days before classes begin. 50% refund within 7 days before classes begin.",
    "contact": {
        "email": "admissions@org.example.com",
        "phone": "+91-80-2672-1983",
        "office_hours": "Monday to Friday, 9:00 AM - 5:00 PM IST",
    },
}


class ActionAskFeeDeadline(Action):
    """
    Custom action for admissions calendar fees and deadlines (slice-26, FR-16).
    Queries AdmissionsAdapter.get_calendar() (mock-admissions-service /calendar),
    filters relevant fees, deadlines, or refund policies based on user inquiry,
    and returns template_key + structured slots.
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
        Asynchronously fetches calendar data and filters relevant fee/deadline information.
        Adheres to AC-1 (fees), AC-2 (deadlines), AC-3 (dynamic calendar updates), and AC-4 (clarification for vague queries).
        """
        q = (query or "").strip().lower()

        # Handle very vague queries needing clarification (AC-4)
        if q in ["when?", "how much?", "fees?", "deadline?", "when", "how much", "fee", "cost?"]:
            return {
                "template_key": None,
                "needs_clarification": True,
                "slots": {},
                "response_text": "Could you please clarify whether you are asking about tuition fees, application fees, or application and payment deadlines?",
            }

        calendar_data: Optional[Dict[str, Any]] = None
        if HAS_ADAPTER and AdmissionsAdapter is not None:
            try:
                calendar_data = await AdmissionsAdapter.get_calendar()
            except Exception as e:
                logger.warning("AdmissionsAdapter.get_calendar failed (%s). Using offline calendar.", e)

        if not calendar_data:
            calendar_data = OFFLINE_CALENDAR

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

        if matched_fees and not matched_deadlines:
            topic = "fee"
            details = "; ".join(f"{f['item']}: {f['amount']}" for f in matched_fees)
        elif matched_deadlines and not matched_fees:
            topic = "deadline"
            details = "; ".join(f"{d['milestone']}: {d['date']}" for d in matched_deadlines)
        else:
            topic = "general"
            fee_str = "; ".join(f"{f['item']}: {f['amount']}" for f in matched_fees[:3])
            dl_str = "; ".join(f"{d['milestone']}: {d['date']}" for d in matched_deadlines[:3])
            details = f"Important Deadlines: {dl_str}. Fees: {fee_str}"

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
        }

    def execute_logic(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous execution entrypoint bridging to execute_logic_async.
        """
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
            else:
                dispatcher.utter_message(
                    text=f"Template: {result.get('template_key')} Slots: {result.get('slots')}"
                )

        return events

