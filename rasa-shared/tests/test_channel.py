"""Unit tests for the channel's choice of this turn's parse (needs Rasa installed)."""
from rasa.shared.core.conversation import Dialogue
from rasa.shared.core.events import ActionExecuted, ActiveLoop, BotUttered, SlotSet, UserUttered
from rasa.shared.core.trackers import DialogueStateTracker

from vario_rasa.channel import _this_turn


def _form_turns():
    return [
        ActionExecuted("action_listen"),
        UserUttered("I want to apply for leave", intent={"name": "request_leave", "confidence": 0.9}),
        ActionExecuted("leave_form"),
        ActiveLoop("leave_form"),
        SlotSet("requested_slot", "leave_reason"),
        BotUttered("Tell me the reason."),
        ActionExecuted("action_listen"),
        UserUttered("family function", intent={"name": "inform", "confidence": 0.6}),
        SlotSet("leave_reason", "family function"),
        ActionExecuted("leave_form"),
        SlotSet("requested_slot", None),
        ActiveLoop(None),
    ]


def test_reports_the_form_answer_when_the_tracker_is_rebuilt_from_applied_events():
    # This is how the in-memory tracker store (also Rasa's fallback when the SQL store
    # is unreachable) reloads a tracker: it replays only "applied" events.
    tracker = DialogueStateTracker("conv-1", [])
    tracker.recreate_from_dialogue(Dialogue("conv-1", _form_turns()))
    assert tracker.latest_message.text == "I want to apply for leave"  # the Rasa behaviour

    turn = _this_turn(tracker)

    assert turn.text == "family function"
    assert turn.parse_data["intent"]["name"] == "inform"


def test_reports_the_latest_message_when_events_are_applied_in_order():
    tracker = DialogueStateTracker.from_events("conv-1", _form_turns())

    assert _this_turn(tracker).text == "family function"


def test_a_tracker_without_user_turns_has_an_empty_parse():
    assert _this_turn(DialogueStateTracker("conv-1", [])).parse_data["intent"] == {}
