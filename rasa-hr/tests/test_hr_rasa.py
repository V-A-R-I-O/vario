import pytest
from fastapi.testclient import TestClient

from server import app, classify_message
from actions.actions import ActionCheckLeaveBalance

client = TestClient(app)


def test_health_check_endpoint():
    # AC 1: Service is reachable at RASA_HR_URL
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "rasa-hr"
    assert data["port"] == 5005


def test_classify_variations_of_leave_balance_intent():
    # AC 2: Variations of "what's my leave balance" classify check_leave_balance with high confidence
    utterances = [
        "what's my leave balance",
        "what is my leave balance?",
        "check my leave balance",
        "how many leaves do I have left?",
        "how many vacation days do I have remaining?",
        "can you tell me my leave balance?",
        "show me my leave balance",
        "I want to check my leave balance",
        "how many days of leave do I have?",
        "how much PTO do I have left?",
        "check my PTO balance",
        "what is my remaining paid time off?",
        "how many days off do I have available?",
        "leave balance inquiry",
        "can I check my remaining time off?",
    ]

    for utt in utterances:
        intent, conf, _ = classify_message(utt)
        assert intent == "check_leave_balance", f"Failed on: {utt}"
        assert conf >= 0.85, f"Confidence too low ({conf}) for: {utt}"


def test_classify_leave_type_and_employee_id():
    test_cases = [
        ("how many annual leave days do I have left?", "annual", None),
        ("check sick leave balance", "sick", None),
        ("what is the casual leave balance for EMP-1042?", "casual", "EMP-1042"),
        ("what's my leave balance for EMP-1042", None, "EMP-1042"),
    ]

    for text, expected_lt, expected_emp in test_cases:
        intent, conf, entities = classify_message(text)
        assert intent == "check_leave_balance"
        assert conf >= 0.85
        if expected_lt:
            assert entities.get("leave_type") == expected_lt
        if expected_emp:
            assert entities.get("employee_id") == expected_emp


def test_off_topic_triggers_nlu_fallback():
    # AC 3: Given an off-topic message, then nlu_fallback fires (confidence < 0.4)
    off_topic_messages = [
        "what is the weather in Paris today?",
        "order a pepperoni pizza",
        "play a rock song on spotify",
        "how far is Mars from the sun?",
        "what is quantum computing?",
        "tell me a funny joke",
    ]

    for msg in off_topic_messages:
        intent, conf, _ = classify_message(msg)
        assert intent == "nlu_fallback"
        assert conf < 0.4, f"Fallback confidence should be below threshold for: {msg}"


def test_action_check_leave_balance_skeleton():
    # AC 5: Given action_check_leave_balance, then it exists and returns a template_key + slots shape
    action = ActionCheckLeaveBalance()
    assert action.name() == "action_check_leave_balance"

    result = action.execute_logic(employee_id="EMP-1042", leave_type="annual")
    assert result["template_key"] == "check_leave_balance_response"
    assert "slots" in result
    assert result["slots"]["balance"] == 12
    assert result["slots"]["leave_type"] == "annual"
    assert result["slots"]["employee_id"] == "EMP-1042"


def test_converse_webhook_success_roundtrip():
    # ADR-002 converse contract verification
    payload = {
        "sender": "user-test-123",
        "message": "What is my leave balance?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["confidence"] >= 0.85
    assert data["template_key"] == "check_leave_balance_response"
    assert "balance" in data["slots"]
    assert data["slots"]["balance"] == 12
    assert data["current_form"] is None
    assert data["current_step"] is None
    assert data["response_text"] is None


def test_converse_webhook_fallback_roundtrip():
    # Low confidence fallback in converse endpoint
    payload = {
        "sender": "user-test-123",
        "message": "tell me a funny joke",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "nlu_fallback"
    assert data["confidence"] < 0.4
    assert data["template_key"] is None
    assert data["response_text"] is not None
    assert "didn't quite understand" in data["response_text"]


@pytest.mark.asyncio
async def test_dialogue_router_routes_to_hr_converse():
    # End-to-end integration test with backend dialogue_router
    import httpx
    from unittest.mock import patch
    import sys
    from pathlib import Path

    # Ensure backend is on sys.path
    backend_path = str(Path(__file__).resolve().parent.parent.parent / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app.services.dialogue_router import route
    from app.models.session import Session

    session = Session(session_id="sess-1", conversation_id="conv-1", slots={})
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:5005") as ac:
        async def mock_post(url, payload):
            resp = await ac.post("/webhooks/vario/converse", json=payload)
            return resp.json()

        with patch("app.services.dialogue_router._post_to_rasa", side_effect=mock_post):
            res = await route("hr", "user-101", "What is my leave balance?", session)
            assert res.intent == "check_leave_balance"
            assert res.confidence >= 0.85
            assert res.template_key == "check_leave_balance_response"
            assert res.slots.get("balance") == 12

