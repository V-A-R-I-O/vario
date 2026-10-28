import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from server import app, classify_message, action_handler
from actions.itsm_adapter import BackendUnavailableError, ITSMAdapter
from actions.actions import ActionCheckTicketStatus

client = TestClient(app)


def test_health_endpoint_reports_it_service():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "rasa-it", "port": 5006}


def test_ticket_status_variations_extract_ticket_id():
    utterances = [
        "what's the status of my ticket TKT-1234?",
        "check the status of TKT-1234",
        "Can you check my ticket TKT-1234?",
        "track ticket TKT-1234",
        "has my ticket TKT-1234 been resolved?",
        "what is the progress of TKT-1234?",
        "ticket TKT-1234 status",
        "please provide a status update for ticket TKT-1234",
    ]
    for utterance in utterances:
        intent, confidence, entities = classify_message(utterance)
        assert intent == "check_ticket_status", f"Failed for: {utterance}"
        assert confidence >= 0.85
        assert entities["ticket_id"] == "TKT-1234"


def test_ticket_status_without_id_is_classified():
    intent, confidence, _ = classify_message("check my ticket status")
    assert intent == "check_ticket_status"
    assert confidence >= 0.85


def test_raise_ticket_and_password_reset_are_seeded_as_stubs():
    assert classify_message("create a support ticket")[0] == "raise_ticket"
    assert classify_message("I forgot my password")[0] == "reset_password"


def test_off_topic_message_triggers_fallback():
    for message in [
        "what is the weather in Paris?",
        "tell me a funny joke",
        "order a pepperoni pizza",
        "how far is Mars from the sun?",
    ]:
        intent, confidence, _ = classify_message(message)
        assert intent == "nlu_fallback", f"Unexpected intent for: {message}"
        assert confidence < 0.4


def test_action_returns_template_and_slots_without_fabricating_status():
    action = ActionCheckTicketStatus()
    assert action.name() == "action_check_ticket_status"

    result = action.execute_logic("tkt-1234")
    assert result["template_key"] == "check_ticket_status_response"
    assert result["slots"] == {"ticket_id": "TKT-1234"}
    assert "status" not in result["slots"]


def test_action_prompts_when_ticket_id_missing_or_invalid():
    action = ActionCheckTicketStatus()
    for value in [None, "", "not-a-ticket", "TKT-12"]:
        result = action.execute_logic(value)
        assert result["template_key"] is None
        assert result["slots"] == {}
        assert result["missing_slot"] == "ticket_id"
        assert "TKT-1234" in result["response_text"]



def test_action_lookup_logic_returns_ticket_status_slots():
    payload = {
        "found": True,
        "ticket_id": "IT-1001",
        "status": "In Progress",
        "category": "hardware",
        "description": "Laptop battery drains quickly",
        "reporter": "EMP-1042",
        "updated_at": "2026-10-21T12:30:00Z",
    }
    with patch.object(ITSMAdapter, "get_ticket_status", new_callable=AsyncMock, return_value=payload):
        result = asyncio.run(action_handler.lookup_logic("it-1001"))
    assert result["template_key"] == "check_ticket_status_response"
    assert result["slots"]["ticket_id"] == "IT-1001"
    assert result["slots"]["status"] == "In Progress"
    assert result["slots"]["found"] is True


def test_action_lookup_logic_handles_backend_outage_gracefully():
    with patch.object(ITSMAdapter, "get_ticket_status", new_callable=AsyncMock, side_effect=BackendUnavailableError()):
        result = asyncio.run(action_handler.lookup_logic("TKT-1234"))
    assert result["backend_unavailable"] is True
    assert result["template_key"] is None
    assert "try again" in result["response_text"].lower()


def test_action_lookup_logic_returns_not_found_for_unknown_ticket():
    with patch.object(
        ITSMAdapter,
        "get_ticket_status",
        new_callable=AsyncMock,
        return_value={"found": False, "ticket_id": "TKT-9999", "status": "Not Found"},
    ):
        result = asyncio.run(action_handler.lookup_logic("TKT-9999"))
    assert result["slots"]["found"] is False
    assert result["slots"]["status"] == "Not Found"
    assert "couldn't find" in result["response_text"].lower()


def test_converse_endpoint_prompts_for_missing_ticket_id():
    response = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "user-test",
            "message": "what is the status of my ticket?",
            "session": {"current_form": None, "current_step": None, "slots": {}},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "check_ticket_status"
    assert data["current_form"] == "check_ticket_status_form"
    assert data["current_step"] == "await_ticket_id"
    assert data["template_key"] is None
    assert "ticket ID" in data["response_text"]


def test_converse_endpoint_returns_live_ticket_status(monkeypatch):
    async def fake_lookup(ticket_id):
        assert ticket_id == "TKT-1234"
        return {
            "template_key": "check_ticket_status_response",
            "slots": {"ticket_id": "TKT-1234", "status": "In Progress", "found": True, "category": "hardware"},
            "response_text": None,
        }

    monkeypatch.setattr(action_handler, "lookup_logic", fake_lookup)
    response = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "user-test",
            "message": "what is the status of TKT-1234?",
            "session": {"current_form": None, "current_step": None, "slots": {}},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "check_ticket_status"
    assert data["template_key"] == "check_ticket_status_response"
    assert data["slots"]["ticket_id"] == "TKT-1234"
    assert data["slots"]["status"] == "In Progress"
    assert data["entities"]["status"] == "In Progress"
    assert data["response_text"] is None


def test_converse_endpoint_handles_unknown_ticket(monkeypatch):
    async def fake_lookup(ticket_id):
        return {
            "template_key": None,
            "slots": {"ticket_id": "TKT-9999", "status": "Not Found", "found": False},
            "response_text": "I couldn't find ticket TKT-9999. Please check the ID and try again.",
        }

    monkeypatch.setattr(action_handler, "lookup_logic", fake_lookup)
    response = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "user-test",
            "message": "check ticket TKT-9999",
            "session": {"current_form": None, "current_step": None, "slots": {}},
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["template_key"] is None
    assert data["slots"]["found"] is False
    assert "couldn't find" in data["response_text"]


def test_converse_endpoint_handles_fallback():
    response = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "user-test",
            "message": "tell me a joke",
            "session": {"current_form": None, "current_step": None, "slots": {}},
        },
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "nlu_fallback"
    assert response.json()["confidence"] < 0.4


def _ticket_turn(message, session=None, auth_context=True):
    payload = {"sender": "user-test", "message": message, "session": session or {"current_form": None, "current_step": None, "slots": {}}}
    if auth_context:
        payload["auth_context"] = {"employee_id": "EMP-1042", "full_name": "Demo Employee"}
    return client.post("/webhooks/vario/converse", json=payload)


def test_ticket_creation_collects_details_confirms_and_emits_audit_event():
    created = {"ticket_id": "IT-1004", "category": "network", "description": "VPN is unavailable", "reporter": "EMP-1042", "status": "Open"}
    with patch.object(ITSMAdapter, "create_ticket", new_callable=AsyncMock, return_value=created) as create:
        start = _ticket_turn("create a support ticket").json()
        assert start["current_form"] == "raise_ticket_form"
        assert start["current_step"] == "ask_category"
        assert start["slots"]["requested_slot"] == "category"
        assert create.await_count == 0
        category = _ticket_turn("network", {"current_form": start["current_form"], "current_step": start["current_step"], "slots": start["slots"]}).json()
        assert category["current_step"] == "ask_description"
        description = _ticket_turn("VPN is unavailable", {"current_form": category["current_form"], "current_step": category["current_step"], "slots": category["slots"]}).json()
        assert description["current_step"] == "confirm"
        assert description["slots"]["confirmation_pending"] is True
        assert create.await_count == 0
        result = _ticket_turn("confirm", {"current_form": description["current_form"], "current_step": description["current_step"], "slots": description["slots"]}).json()
    assert result["current_form"] is None
    assert result["slots"]["ticket_id"] == "IT-1004"
    assert result["slots"]["ticket_result"] is True
    assert result["audit_event"]["action_type"] == "ticket_created"
    assert result["audit_event"]["reference_id"] == "IT-1004"
    create.assert_awaited_once_with(category="network", description="VPN is unavailable", reporter="EMP-1042")


def test_ticket_creation_cancel_does_not_call_adapter():
    with patch.object(ITSMAdapter, "create_ticket", new_callable=AsyncMock) as create:
        start = _ticket_turn("create a support ticket").json()
        category = _ticket_turn("hardware", {"current_form": start["current_form"], "current_step": start["current_step"], "slots": start["slots"]}).json()
        description = _ticket_turn("Laptop will not start", {"current_form": category["current_form"], "current_step": category["current_step"], "slots": category["slots"]}).json()
        cancelled = _ticket_turn("cancel", {"current_form": description["current_form"], "current_step": description["current_step"], "slots": description["slots"]}).json()
    create.assert_not_awaited()
    assert cancelled["current_form"] is None
    assert cancelled["slots"]["ticket_id"] is None
    assert "cancelled" in cancelled["response_text"].lower()


def test_identical_immediate_ticket_request_reuses_previous_ticket():
    created = {"ticket_id": "IT-1004", "status": "Open"}
    with patch.object(ITSMAdapter, "create_ticket", new_callable=AsyncMock, return_value=created) as create:
        state = {"current_form": None, "current_step": None, "slots": {}}
        for message in ("create a support ticket", "network", "VPN is unavailable", "confirm"):
            data = _ticket_turn(message, state).json()
            state = {"current_form": data["current_form"], "current_step": data["current_step"], "slots": data["slots"]}
        for message in ("create a support ticket", "network", "VPN is unavailable", "confirm"):
            data = _ticket_turn(message, state).json()
            state = {"current_form": data["current_form"], "current_step": data["current_step"], "slots": data["slots"]}
        assert data["slots"]["ticket_id"] == "IT-1004"
        assert data["slots"]["ticket_reused"] is True
        assert create.await_count == 1


def test_ticket_creation_requires_authenticated_reporter():
    response = _ticket_turn("create a support ticket", auth_context=False)
    assert response.status_code == 200
    assert response.json()["current_form"] is None
    assert "sign in" in response.json()["response_text"].lower()
