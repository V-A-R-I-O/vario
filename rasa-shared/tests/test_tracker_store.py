"""Unit tests for redact_sensitive_turns (needs Rasa installed)."""
from rasa.shared.core.events import SlotSet, UserUttered
from rasa.shared.core.trackers import DialogueStateTracker

from vario_rasa.contract import REDACTED_TEXT
from vario_rasa.tracker_store import redact_sensitive_turns

SECRET = "sunrise primary school"


def _tracker(*events):
    return DialogueStateTracker.from_events("conv-1", list(events))


def test_sensitive_turn_and_slot_filled_from_it_are_redacted():
    tracker = _tracker(
        UserUttered("reset my password", intent={"name": "reset_password", "confidence": 0.9}),
        UserUttered(SECRET, intent={"name": "inform", "confidence": 0.5},
                    entities=[{"entity": "school", "value": SECRET}], metadata={"sensitive": True}),
        SlotSet("security_answer", SECRET),
    )
    redact_sensitive_turns(tracker)

    serialized = str([e.as_dict() for e in tracker.events])
    assert SECRET not in serialized
    sensitive = list(tracker.events)[1]
    assert sensitive.text == REDACTED_TEXT and sensitive.entities == []
    assert sensitive.parse_data["intent"]["name"] == "inform"  # classification is kept


def test_normal_turns_are_untouched():
    tracker = _tracker(
        UserUttered("I want sick leave", intent={"name": "submit_leave_request", "confidence": 0.9}),
        SlotSet("leave_type", "sick"),
    )
    redact_sensitive_turns(tracker)
    events = list(tracker.events)
    assert events[0].text == "I want sick leave"
    assert events[1].value == "sick"


def test_slots_after_the_next_user_turn_are_not_redacted():
    tracker = _tracker(
        UserUttered(SECRET, metadata={"sensitive": True}),
        UserUttered("my reason is sunrise primary school trip"),
        SlotSet("reason", "sunrise primary school trip"),
    )
    redact_sensitive_turns(tracker)
    assert list(tracker.events)[2].value == "sunrise primary school trip"
