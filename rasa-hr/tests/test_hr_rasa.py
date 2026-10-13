import os
import logging
from unittest.mock import patch, MagicMock
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


def test_action_check_leave_balance_requires_employee_id_when_missing():
    # AC 5 & Issue 2: Action must NOT return EMP-1042 or hardcoded balance when employee ID is missing
    action = ActionCheckLeaveBalance()
    assert action.name() == "action_check_leave_balance"

    result = action.execute_logic(employee_id=None, leave_type="annual")
    assert result["requires_input"] is True
    assert result["missing_slot"] == "employee_id"
    assert result["template_key"] is None
    assert "balance" not in result["slots"]
    assert "employee_id" not in result["slots"]
    assert "Please provide your employee ID" in result["response_text"]


def test_action_check_leave_balance_returns_template_when_id_present():
    action = ActionCheckLeaveBalance()
    result = action.execute_logic(employee_id="EMP-2048", leave_type="sick")
    assert result["requires_input"] is False
    assert result["template_key"] == "check_leave_balance_response"
    assert result["slots"]["employee_id"] == "EMP-2048"
    assert result["slots"]["balance"] == 12
    assert result["slots"]["leave_type"] == "sick"


def test_converse_webhook_missing_employee_id_prompts_user():
    # Issue 2: Without employee context, do NOT silently return EMP-1042 data
    payload = {
        "sender": "anonymous-user",
        "message": "What is my leave balance?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["template_key"] is None
    assert "balance" not in data["slots"]
    assert data["current_form"] == "check_leave_balance"
    assert data["current_step"] == "ask_employee_id"
    assert "Please provide your employee ID" in data["response_text"]


def test_converse_webhook_resolves_employee_id_from_message():
    payload = {
        "sender": "anonymous-user",
        "message": "What is the leave balance for EMP-1042?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["template_key"] == "check_leave_balance_response"
    assert data["slots"]["employee_id"] == "EMP-1042"
    assert data["slots"]["balance"] == 12
    assert data["current_form"] is None


def test_converse_webhook_resolves_employee_id_from_authenticated_sender():
    # Issue 2: Resolves employee context from authenticated session sender
    payload = {
        "sender": "EMP-9081",
        "message": "What is my leave balance?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["template_key"] == "check_leave_balance_response"
    assert data["slots"]["employee_id"] == "EMP-9081"
    assert data["slots"]["balance"] == 12


def test_converse_webhook_resolves_employee_id_from_session_slots():
    # Issue 2: Resolves employee context from existing session slots
    payload = {
        "sender": "user-turn-2",
        "message": "How many days left?",
        "session": {
            "current_form": "check_leave_balance",
            "current_step": "ask_employee_id",
            "slots": {"employee_id": "EMP-3045"},
        },
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["template_key"] == "check_leave_balance_response"
    assert data["slots"]["employee_id"] == "EMP-3045"
    assert data["slots"]["balance"] == 12


def test_ambiguous_intent_classification():
    # Issue 3: Ambiguous queries and isolated single keywords trigger nlu_fallback
    ambiguous_queries = [
        "leave",
        "leaves",
        "help with leave",
        "need leave assistance",
        "I want to apply for leave status balance",
    ]

    for q in ambiguous_queries:
        intent, conf, _ = classify_message(q)
        assert intent == "nlu_fallback", f"Query '{q}' should be ambiguous but classified as {intent}"
        assert conf < 0.4, f"Ambiguous query '{q}' confidence should be < 0.4, got {conf}"


def test_policy_query_edge_cases():
    # Issue 3: Policy-query edge cases like "What is the maternity policy?"
    # must classify as ask_policy_faq (never check_leave_balance)
    policy_queries = [
        ("What is the maternity policy?", "maternity"),
        ("maternity leave policy", "maternity"),
        ("what is the paternity policy?", "paternity"),
        ("what are the rules for sick leave?", "sick"),
        ("tell me about the leave carryover rules", "carryover"),
        ("bereavement leave policy", "bereavement"),
        ("what is the company leave policy?", None),
    ]

    for text, expected_topic in policy_queries:
        intent, conf, entities = classify_message(text)
        assert intent == "ask_policy_faq", f"Query '{text}' was misclassified as {intent}"
        assert conf >= 0.85
        if expected_topic:
            assert entities.get("policy_topic") == expected_topic, (
                f"Expected topic '{expected_topic}' for '{text}', got '{entities.get('policy_topic')}'"
            )


def test_no_sensitive_hr_data_logged(caplog):
    # Issue 4: Sensitive employee identifiers and raw message PII must NOT be logged
    caplog.set_level(logging.INFO, logger="rasa_hr_server")

    payload = {
        "sender": "EMP-7777",
        "message": "Sensitive medical leave details for EMP-7777",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    client.post("/webhooks/vario/converse", json=payload)

    for record in caplog.records:
        if record.name == "rasa_hr_server":
            assert "EMP-7777" not in record.message, f"Sensitive employee ID found in log: {record.message}"
            assert "Sensitive medical leave" not in record.message, f"Raw user message PII found in log: {record.message}"


def test_upstream_rasa_runtime_proxy():
    # Issue 1: Invokes actual upstream Rasa NLU runtime when RASA_NLU_URL is configured
    fake_rasa_response = {
        "text": "what is my leave balance",
        "intent": {"name": "check_leave_balance", "confidence": 0.982},
        "entities": [{"entity": "leave_type", "value": "annual"}],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_rasa_response

    with patch.dict(os.environ, {"RASA_NLU_URL": "http://mock-rasa-upstream:5005"}):
        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            intent, conf, entities = classify_message("what is my leave balance")

            assert intent == "check_leave_balance"
            assert conf == 0.982
            assert entities.get("leave_type") == "annual"
            mock_post.assert_called_once_with(
                "http://mock-rasa-upstream:5005/model/parse",
                json={"text": "what is my leave balance"}
            )


@pytest.mark.asyncio
async def test_dialogue_router_routes_to_hr_converse():
    # End-to-end integration test with backend dialogue_router
    import httpx
    import sys
    from pathlib import Path

    backend_path = str(Path(__file__).resolve().parent.parent.parent / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app.services.dialogue_router import route
    from app.models.session import Session

    # With resolved employee ID in session
    session = Session(session_id="sess-1", conversation_id="conv-1", slots={"employee_id": "EMP-1042"})
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
            assert res.slots.get("employee_id") == "EMP-1042"
