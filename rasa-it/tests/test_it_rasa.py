from fastapi.testclient import TestClient

from server import app, classify_message, action_handler
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
