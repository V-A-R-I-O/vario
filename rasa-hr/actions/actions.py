import re
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


class ActionCheckLeaveBalance(Action):
    """
    Custom action skeleton for checking leave balance (slice-12).
    Extracts employee_id and leave_type, returning the template_key + slots shape.
    Full HRMS adapter call is wired in slice-14.
    """

    TEMPLATE_KEY = "check_leave_balance_response"
    ASK_EMPLOYEE_ID_PROMPT = "Please provide your employee ID (e.g., EMP-1042) to check your leave balance."

    def name(self) -> Text:
        return "action_check_leave_balance"

    def extract_employee_id(self, tracker: Any, sender: Optional[str] = None) -> Optional[str]:
        """
        Extracts employee_id from slot, extracted entities, or authenticated session context.
        Does NOT silently fall back to a hardcoded employee ID.
        """
        # 1. Try tracker slot if available
        if hasattr(tracker, "get_slot"):
            emp_id = tracker.get_slot("employee_id")
            if emp_id:
                return str(emp_id).strip().upper()

        # 2. Try latest message entities
        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            entities = tracker.latest_message.get("entities", [])
            for ent in entities:
                if ent.get("entity") == "employee_id":
                    return str(ent.get("value", "")).strip().upper()

        # 3. Direct dictionary access fallback
        if isinstance(tracker, dict):
            slots = tracker.get("slots", {})
            if slots and "employee_id" in slots and slots["employee_id"]:
                return str(slots["employee_id"]).strip().upper()
            for ent in tracker.get("entities", []):
                if ent.get("entity") == "employee_id":
                    return str(ent.get("value", "")).strip().upper()

        # 4. Resolve from authenticated session sender if formatted as an employee ID
        if sender and re.match(r"^EMP-\d{4}$", sender.strip(), re.IGNORECASE):
            return sender.strip().upper()

        return None

    def extract_leave_type(self, tracker: Any) -> Optional[str]:
        """Extracts leave_type from slot or extracted entities."""
        if hasattr(tracker, "get_slot"):
            lt = tracker.get_slot("leave_type")
            if lt:
                return str(lt).strip().lower()

        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            entities = tracker.latest_message.get("entities", [])
            for ent in entities:
                if ent.get("entity") == "leave_type":
                    return str(ent.get("value", "")).strip().lower()

        if isinstance(tracker, dict):
            if "leave_type" in tracker.get("slots", {}):
                return str(tracker["slots"]["leave_type"]).strip().lower()
            for ent in tracker.get("entities", []):
                if ent.get("entity") == "leave_type":
                    return str(ent.get("value", "")).strip().lower()

        return None

    def execute_logic(
        self,
        employee_id: Optional[str] = None,
        leave_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes action logic.
        If employee_id is missing, prompts for the required ID rather than silently
        returning another employee's data or hardcoded leave balance.
        """
        leave_type_clean = leave_type or "annual"

        if not employee_id:
            return {
                "template_key": None,
                "slots": {
                    "leave_type": leave_type_clean,
                },
                "requires_input": True,
                "missing_slot": "employee_id",
                "response_text": self.ASK_EMPLOYEE_ID_PROMPT,
            }

        # When employee_id is resolved (from message or authenticated session),
        # return the template_key + slots shape for the response-renderer.
        # Live adapter call to get_leave_balance() is wired in slice-14.
        return {
            "template_key": self.TEMPLATE_KEY,
            "slots": {
                "balance": 12,
                "leave_type": leave_type_clean,
                "employee_id": employee_id,
            },
            "requires_input": False,
            "missing_slot": None,
            "response_text": None,
        }

    async def run(
        self,
        dispatcher: Any,
        tracker: Any,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        emp_id = self.extract_employee_id(tracker)
        leave_type = self.extract_leave_type(tracker)
        result = self.execute_logic(emp_id, leave_type)

        events = []
        for key, val in result["slots"].items():
            events.append(SlotSet(key, val))

        if hasattr(dispatcher, "utter_message"):
            if result.get("requires_input"):
                dispatcher.utter_message(text=result["response_text"])
            else:
                dispatcher.utter_message(
                    text=f"Template: {result['template_key']} Slots: {result['slots']}"
                )

        return events
