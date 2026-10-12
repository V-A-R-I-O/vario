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
        for key, val in result["slots"].items():
            events.append(SlotSet(key, val))

        if hasattr(dispatcher, "utter_message"):
            if result.get("response_text"):
                dispatcher.utter_message(text=result["response_text"])
            else:
                dispatcher.utter_message(
                    text=f"Template: {result['template_key']} Slots: {result['slots']}"
                )

        return events
