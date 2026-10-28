import re
from typing import Any, Dict, Optional

from actions.itsm_adapter import BackendUnavailableError, ITSMAdapter

try:
    from rasa_sdk import Action, Tracker
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.events import SlotSet
except ImportError:  # Allows the lightweight runtime tests to run without Rasa SDK.
    class Action:  # type: ignore[no-redef]
        pass

    class Tracker:  # type: ignore[no-redef]
        pass

    class CollectingDispatcher:  # type: ignore[no-redef]
        pass

    def SlotSet(key: str, value: Any) -> Dict[str, Any]:  # type: ignore[no-redef]
        return {"event": "slot", "name": key, "value": value}


TICKET_ID_REGEX = re.compile(r"\b((?:TKT|IT)-\d{4})\b", re.IGNORECASE)


class ActionCheckTicketStatus(Action):
    """Look up ticket status through the ITSM adapter and return chat slots."""

    TEMPLATE_KEY = "check_ticket_status_response"

    def name(self) -> str:
        return "action_check_ticket_status"

    @staticmethod
    def extract_ticket_id(tracker: Any) -> Optional[str]:
        if hasattr(tracker, "get_slot"):
            value = tracker.get_slot("ticket_id")
            if value:
                match = TICKET_ID_REGEX.search(str(value))
                if match:
                    return match.group(1).upper()

        if hasattr(tracker, "latest_message") and isinstance(tracker.latest_message, dict):
            for entity in tracker.latest_message.get("entities", []):
                if entity.get("entity") == "ticket_id":
                    match = TICKET_ID_REGEX.search(str(entity.get("value", "")))
                    if match:
                        return match.group(1).upper()

        if isinstance(tracker, dict):
            value = tracker.get("slots", {}).get("ticket_id")
            if value:
                match = TICKET_ID_REGEX.search(str(value))
                if match:
                    return match.group(1).upper()
            for entity in tracker.get("entities", []):
                if entity.get("entity") == "ticket_id":
                    match = TICKET_ID_REGEX.search(str(entity.get("value", "")))
                    if match:
                        return match.group(1).upper()
        return None

    def execute_logic(self, ticket_id: Optional[str]) -> Dict[str, Any]:
        """Return the stable template/slot contract without fabricating a ticket status."""
        match = TICKET_ID_REGEX.search((ticket_id or "").strip())
        if not match:
            return {
                "template_key": None,
                "slots": {},
                "missing_slot": "ticket_id",
                "response_text": "Please provide your ticket ID (for example, TKT-1234) so I can check its status.",
            }
        return {
            "template_key": self.TEMPLATE_KEY,
            "slots": {"ticket_id": match.group(1).upper()},
            "response_text": None,
        }

    async def lookup_logic(self, ticket_id: Optional[str]) -> Dict[str, Any]:
        """Resolve the ticket ID against ITSM; never invent a status."""
        result = await self.lookup_logic(ticket_id)
        if result.get("missing_slot"):
            return result

        clean_id = result["slots"]["ticket_id"]
        try:
            ticket = await ITSMAdapter.get_ticket_status(clean_id)
        except BackendUnavailableError:
            return {
                "template_key": None,
                "slots": {"ticket_id": clean_id},
                "backend_unavailable": True,
                "response_text": "I can't reach the IT ticket system right now. Please try again shortly.",
            }

        if not ticket.get("found"):
            return {
                "template_key": None,
                "slots": {"ticket_id": clean_id, "status": "Not Found", "found": False},
                "response_text": (
                    f"I couldn't find ticket {clean_id}. Please check the ID and try again. "
                    "You can use the ticket ID shown in your support confirmation."
                ),
            }

        slots = {
            "ticket_id": ticket.get("ticket_id", clean_id),
            "status": ticket.get("status") or "Unknown",
            "found": True,
        }
        for key in ("category", "description", "reporter", "updated_at"):
            if ticket.get(key):
                slots[key] = str(ticket[key])
        return {"template_key": self.TEMPLATE_KEY, "slots": slots, "response_text": None}

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> list:
        ticket_id = self.extract_ticket_id(tracker)
        result = self.execute_logic(ticket_id)
        if result.get("missing_slot"):
            dispatcher.utter_message(text=result["response_text"])
            return []
        if result.get("backend_unavailable") or result.get("slots", {}).get("found") is False:
            dispatcher.utter_message(text=result["response_text"])
            return [SlotSet(key, value) for key, value in result.get("slots", {}).items()]
        slots = result["slots"]
        dispatcher.utter_message(text=f"Ticket {slots['ticket_id']} is currently {slots['status']}.")
        return [SlotSet(key, value) for key, value in slots.items()]


class ActionDefaultFallback(Action):
    def name(self) -> str:
        return "action_default_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> list:
        dispatcher.utter_message(
            text="I'm sorry, I didn't understand that. You can ask me to check an IT ticket, raise a support ticket, or get password-reset help."
        )
        return []
