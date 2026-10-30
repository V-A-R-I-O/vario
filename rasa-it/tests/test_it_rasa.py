from pathlib import Path
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from actions.actions import (
    ActionAskResetPasswordSecurityAnswer,
    ActionCheckTicketStatus,
    ActionSubmitRaiseTicket,
    ValidateResetPasswordForm,
)


class FakeTracker:
    def __init__(self, slots=None, latest_message=None):
        self.slots = slots or {}
        self.latest_message = latest_message or {}

    def get_slot(self, name):
        return self.slots.get(name)


class FakeDispatcher:
    def __init__(self):
        self.messages = []

    def utter_message(self, **kwargs):
        self.messages.append(kwargs)


@pytest.mark.asyncio
async def test_ticket_status_lookup_is_fresh_per_ticket():
    with patch("actions.actions.ITSMAdapter.get_ticket_status", new_callable=AsyncMock,
               side_effect=[
                   {"found": True, "ticket_id": "IT-1001", "status": "In Progress"},
                   {"found": True, "ticket_id": "IT-1002", "status": "Open"},
               ]):
        first = await ActionCheckTicketStatus.lookup("IT-1001")
        second = await ActionCheckTicketStatus.lookup("IT-1002")
    assert first["slots"]["ticket_id"] == "IT-1001"
    assert first["slots"]["status"] == "In Progress"
    assert second["slots"] == {"ticket_id": "IT-1002", "status": "Open", "found": True}
    assert "In Progress" not in str(second)


@pytest.mark.asyncio
async def test_ticket_status_without_id_prompts_for_id():
    result = await ActionCheckTicketStatus.lookup(None)
    assert result["template_key"] is None
    assert result["slots"] == {}
    assert "ticket ID" in result["text"]


@pytest.mark.asyncio
async def test_unknown_ticket_returns_its_own_not_found_card():
    with patch("actions.actions.ITSMAdapter.get_ticket_status", new_callable=AsyncMock,
               return_value={"found": False, "ticket_id": "TKT-9999", "status": "Not Found"}):
        result = await ActionCheckTicketStatus.lookup("TKT-9999")
    assert result["slots"] == {"ticket_id": "TKT-9999", "found": False}
    assert result["card"]["type"] == "not_found"
    assert "TKT-9999" in result["text"]


def test_ticket_creation_uses_trusted_reporter_and_returns_ticket_id():
    tracker = FakeTracker(
        {"category": "network", "description": "VPN drops every hour", "confirmation": True},
        {"metadata": {"auth_context": {"employee_id": "EMP-1042"}}},
    )
    dispatcher = FakeDispatcher()
    with patch("actions.actions.ITSMAdapter.create_ticket", new_callable=AsyncMock,
               return_value={"ticket_id": "IT-1004", "status": "Open"}) as create:
        events = asyncio.run(ActionSubmitRaiseTicket().run(dispatcher, tracker, {}))
    assert create.await_args.args == ("network", "VPN drops every hour", "EMP-1042")
    assert "IT-1004" in dispatcher.messages[0]["text"]
    # Rasa SDK SlotSet events are mappings with "name" and "value" keys.
    assert any(event.get("name") == "last_ticket_id" and event.get("value") == "IT-1004" for event in events)


@pytest.mark.asyncio
async def test_security_answer_is_never_returned_as_a_slot():
    secret = "private security answer"
    tracker = FakeTracker({"employee_id": "EMP-1042"},
                          {"text": secret, "metadata": {"sensitive": True}})
    dispatcher = FakeDispatcher()
    with patch("actions.actions.ITSMAdapter.verify_identity", new_callable=AsyncMock,
               return_value={"verified": False, "locked": False, "attempts_remaining": 2}):
        result = await ValidateResetPasswordForm().validate_security_answer(secret, dispatcher, tracker, {})
    assert secret not in str(result)
    assert result["security_answer"] is None
    assert "attempt(s) remaining" in dispatcher.messages[0]["text"]


def test_security_prompt_marks_next_turn_sensitive():
    dispatcher = FakeDispatcher()
    tracker = FakeTracker({"security_question": "What city were you born in?"})
    ActionAskResetPasswordSecurityAnswer().run(dispatcher, tracker, {})
    assert dispatcher.messages[0]["json_message"]["vario"]["sensitive_next_input"] is True


def test_real_rasa_assets_include_forms_fallback_and_interruptions():
    root = Path(__file__).resolve().parents[1]
    domain = yaml.safe_load((root / "domain.yml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((root / "data" / "rules.yml").read_text(encoding="utf-8"))
    nlu = yaml.safe_load((root / "data" / "nlu.yml").read_text(encoding="utf-8"))
    assert set(domain["forms"]) == {"ticket_status_form", "raise_ticket_form", "reset_password_form"}
    assert domain["forms"]["raise_ticket_form"]["required_slots"] == ["category", "description", "confirmation"]
    assert domain["forms"]["reset_password_form"]["required_slots"] == ["employee_id", "security_answer"]
    rule_text = str(rules)
    assert "Cancel ticket status form" in rule_text
    assert "Reset password interrupts ticket status" in rule_text
    status_examples = next(item["examples"] for item in nlu["nlu"] if item.get("intent") == "check_ticket_status")
    assert "status of the ticket I submitted" in status_examples
    assert any(item.get("regex") == "ticket_id" for item in nlu["nlu"])


def test_ticket_id_entity_mapping_is_not_limited_to_an_active_form():
    root = Path(__file__).resolve().parents[1]
    domain = yaml.safe_load((root / "domain.yml").read_text(encoding="utf-8"))
    mappings = domain["slots"]["ticket_id"]["mappings"]
    assert mappings == [{"type": "from_entity", "entity": "ticket_id"}]


def test_rasa_configuration_has_stable_assistant_id_and_local_action_fallback():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "config.yml").read_text(encoding="utf-8"))
    endpoints = yaml.safe_load((root / "endpoints.yml").read_text(encoding="utf-8"))
    assert config["assistant_id"] == "it_assistant"
    assert endpoints["action_endpoint"]["url"] == "${ACTION_ENDPOINT_URL:-http://localhost:5055/webhook}"
