from typing import Any, Text, Dict, List, Optional

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


class ActionCheckApplicationStatus(Action):
    """
    Custom action skeleton for checking application status (slice-22).
    Extracts the application_id and returns the template_key + slots shape.
    Full adapter call is wired in slice-24.
    """

    TEMPLATE_KEY = "check_application_status_response"

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

    def execute_logic(self, application_id: Optional[str]) -> Dict[str, Any]:
        """
        Executes the action logic and returns the template_key + slots shape.
        If application_id is missing, requests the missing ID instead of silently defaulting.
        In slice-22, this is the skeleton returning template_key + slots shape.
        In slice-24, this connects to AdmissionsAdapter.
        """
        if not application_id or not str(application_id).strip():
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "application_id",
                "response_text": "Please provide your application ID (e.g. APP-1001) so I can check your status.",
            }

        app_id_clean = str(application_id).strip().upper()
        return {
            "template_key": self.TEMPLATE_KEY,
            "slots": {
                "application_id": app_id_clean,
                "status": "Under Review",
                "next_step": "Application is being reviewed by the admissions committee.",
            },
            "missing_slot": None,
            "response_text": None,
        }

    async def run(
        self,
        dispatcher: Any,
        tracker: Any,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        app_id = self.extract_application_id(tracker)
        result = self.execute_logic(app_id)

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
