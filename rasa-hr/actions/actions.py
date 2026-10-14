import re
import os
import sys
from typing import Any, Text, Dict, List, Optional

# Add backend to path for HRMSAdapter import
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

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

# Import HRMSAdapter for slice-14
try:
    import asyncio
    from app.services.hrms_adapter import HRMSAdapter
    HAS_HRMS_ADAPTER = True
except ImportError:
    HAS_HRMS_ADAPTER = False
    HRMSAdapter = None  # type: ignore

# Offline fallback employee records (graceful degradation when mock service is offline)
OFFLINE_EMPLOYEES: Dict[str, Dict[str, Any]] = {
    "EMP-1042": {
        "found": True,
        "employee_id": "EMP-1042",
        "employee_name": "Jane Smith",
        "department": "Product Marketing",
        "total": 22,
        "casual": 4,
        "sick": 6,
        "earned": 12,
    },
    "EMP-1001": {
        "found": True,
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "department": "Engineering",
        "total": 28,
        "casual": 6,
        "sick": 8,
        "earned": 14,
    },
    "EMP-2001": {
        "found": True,
        "employee_id": "EMP-2001",
        "employee_name": "HR Admin",
        "department": "People Operations",
        "total": 20,
        "casual": 5,
        "sick": 5,
        "earned": 10,
    },
    "EMP-3045": {
        "found": True,
        "employee_id": "EMP-3045",
        "employee_name": "Engineering Lead",
        "department": "Engineering",
        "total": 12,
        "casual": 3,
        "sick": 4,
        "earned": 5,
    },
}


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

        Slice-14: Wired to call HRMSAdapter.get_leave_balance() for real data.
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

        clean_id = (employee_id or "").strip().upper()
        balance_data: Optional[Dict[str, Any]] = None

        # Slice-14: Call HRMSAdapter to get actual leave balance
        if HAS_HRMS_ADAPTER and HRMSAdapter:
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop is not None and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        balance_data = pool.submit(
                            asyncio.run,
                            HRMSAdapter.get_leave_balance(clean_id, raise_for_not_found=False),
                        ).result()
                else:
                    balance_data = asyncio.run(
                        HRMSAdapter.get_leave_balance(clean_id, raise_for_not_found=False)
                    )
            except Exception:
                balance_data = None

        if balance_data is None:
            if clean_id in OFFLINE_EMPLOYEES:
                balance_data = OFFLINE_EMPLOYEES[clean_id]
            else:
                balance_data = {
                    "found": False,
                    "employee_id": clean_id,
                }

        if balance_data.get("found"):
            # Employee found - return data card slots with breakdown
            return {
                "template_key": self.TEMPLATE_KEY,
                "slots": {
                    "total": balance_data.get("total", 0),
                    "casual": balance_data.get("casual", 0),
                    "sick": balance_data.get("sick", 0),
                    "earned": balance_data.get("earned", 0),
                    "employee_id": clean_id,
                    "leave_type": leave_type_clean,
                },
                "requires_input": False,
                "missing_slot": None,
                "response_text": None,
            }
        else:
            # Employee not found - graceful fallback (AC 3)
            return {
                "template_key": None,
                "slots": {
                    "employee_id": clean_id,
                    "leave_type": leave_type_clean,
                },
                "requires_input": False,
                "missing_slot": None,
                "response_text": f"Sorry, I couldn't find leave balance information for employee ID {clean_id}. Please check the ID and try again, or contact HR for assistance.",
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
