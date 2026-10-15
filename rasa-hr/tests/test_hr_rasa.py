import os
import logging
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from server import app, classify_message
from actions.actions import ActionCheckLeaveBalance, ActionSubmitLeaveRequest

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
    result = action.execute_logic(employee_id="EMP-1042", leave_type="sick")
    assert result["requires_input"] is False
    assert result["template_key"] == "check_leave_balance_response"
    assert result["slots"]["employee_id"] == "EMP-1042"
    # Slice-14: Now returns breakdown instead of just balance
    assert result["slots"]["total"] == 22
    assert result["slots"]["casual"] == 4
    assert result["slots"]["sick"] == 6
    assert result["slots"]["earned"] == 12
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
    # Slice-14: Now returns breakdown from HRMS
    assert data["slots"]["total"] == 22
    assert data["slots"]["casual"] == 4
    assert data["slots"]["sick"] == 6
    assert data["slots"]["earned"] == 12
    assert data["current_form"] is None


def test_converse_webhook_resolves_employee_id_from_authenticated_sender():
    # Issue 2: Resolves employee context from authenticated session sender
    # Slice-14: EMP-9081 not in mock HRMS, so should return graceful error
    payload = {
        "sender": "EMP-9081",
        "message": "What is my leave balance?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    # Employee not found, so template_key is None and response_text has error message
    assert data["template_key"] is None
    assert "couldn't find" in data["response_text"].lower() or "could not find" in data["response_text"].lower()
    assert data["slots"]["employee_id"] == "EMP-9081"


def test_converse_webhook_resolves_employee_id_from_session_slots():
    # Issue 2: Resolves employee context from existing session slots
    # Slice-14: Use EMP-1042 (exists in mock HRMS) instead of EMP-3045
    payload = {
        "sender": "user-turn-2",
        "message": "How many days left?",
        "session": {
            "current_form": "check_leave_balance",
            "current_step": "ask_employee_id",
            "slots": {"employee_id": "EMP-1042"},
        },
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_leave_balance"
    assert data["template_key"] == "check_leave_balance_response"
    assert data["slots"]["employee_id"] == "EMP-1042"
    assert data["slots"]["total"] == 22
    assert data["slots"]["casual"] == 4


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


def test_action_check_leave_balance_employee_not_found():
    # Slice-14 AC 3: Given an employee with no HRMS record, return graceful message
    action = ActionCheckLeaveBalance()
    result = action.execute_logic(employee_id="EMP-9999", leave_type="annual")

    assert result["requires_input"] is False
    assert result["template_key"] is None
    assert "couldn't find" in result["response_text"].lower() or "could not find" in result["response_text"].lower()
    assert result["slots"]["employee_id"] == "EMP-9999"


def test_action_check_leave_balance_with_real_employee():
    # Slice-14 AC 1: Given EMP-1042 (seeded in mock HRMS), return data card with breakdown
    action = ActionCheckLeaveBalance()
    result = action.execute_logic(employee_id="EMP-1042", leave_type="annual")

    assert result["requires_input"] is False
    assert result["template_key"] == "check_leave_balance_response"
    assert result["slots"]["employee_id"] == "EMP-1042"
    assert result["slots"]["total"] == 22
    assert result["slots"]["casual"] == 4
    assert result["slots"]["sick"] == 6
    assert result["slots"]["earned"] == 12
    assert result["response_text"] is None


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


def test_dialogue_router_routes_to_hr_converse():
    # End-to-end integration test with backend dialogue_router
    import httpx
    import sys
    import asyncio
    from pathlib import Path

    backend_path = str(Path(__file__).resolve().parent.parent.parent / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app.services.dialogue_router import route
    from app.models.session import Session

    async def _run():
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
                assert res.slots.get("total") == 22
                assert res.slots.get("casual") == 4

    asyncio.run(_run())


# ============================================================================
# Slice 15: HR Leave Request Workflow Tests
# ============================================================================

def test_classify_leave_request_intent():
    """AC 1: Leave request phrases classify as submit_leave_request"""
    utterances = [
        "I want to apply for leave",
        "submit a leave request",
        "apply for leave",
        "request time off",
        "I need to take leave",
        "book leave",
        "submit leave application",
        "apply for vacation",
    ]

    for utt in utterances:
        intent, conf, _ = classify_message(utt)
        assert intent == "submit_leave_request", f"Failed on: {utt}"
        assert conf >= 0.85, f"Confidence too low ({conf}) for: {utt}"


def test_action_submit_leave_collects_leave_type():
    """AC 1: Workflow prompts for leave_type when missing"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(employee_id="EMP-1042")

    assert result["requires_input"] is True
    assert result["missing_slot"] == "leave_type"
    assert result["slots"]["requested_slot"] == "leave_type"


def test_action_submit_leave_collects_start_date():
    """AC 1: Workflow prompts for start_date after leave_type"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(employee_id="EMP-1042", leave_type="casual")

    assert result["requires_input"] is True
    assert result["missing_slot"] == "start_date"
    assert result["slots"]["requested_slot"] == "start_date"


def test_action_submit_leave_validates_start_date():
    """AC 1: Workflow validates start_date format and not in past"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()

    # Invalid format
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="10/20/2026"
    )
    assert result["requires_input"] is True
    assert result["slots"]["start_date"] is None
    assert "valid start date" in result["response_text"].lower()

    # Valid future date
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20"
    )
    assert result["missing_slot"] == "end_date"


def test_action_submit_leave_collects_end_date():
    """AC 1: Workflow prompts for end_date after start_date"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20"
    )

    assert result["requires_input"] is True
    assert result["missing_slot"] == "end_date"


def test_action_submit_leave_validates_date_range():
    """AC 1: Workflow validates end_date >= start_date"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()

    # End before start
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20",
        end_date="2026-10-19"
    )
    assert result["requires_input"] is True
    assert result["slots"]["end_date"] is None
    assert "on or after the start date" in result["response_text"].lower()


def test_action_submit_leave_collects_reason():
    """AC 1: Workflow prompts for reason after dates"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20",
        end_date="2026-10-22"
    )

    assert result["requires_input"] is True
    assert result["missing_slot"] == "reason"


def test_action_submit_leave_shows_confirmation():
    """AC 2: Confirmation summary shown before submission"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20",
        end_date="2026-10-22",
        reason="Family event"
    )

    assert result["template_key"] == "submit_leave_confirmation"
    assert result["slots"]["confirmation_pending"] is True
    assert result["requires_input"] is True


def test_action_submit_leave_submits_on_confirm():
    """AC 3: Leave submitted via adapter on Confirm"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()

    # Mock successful submission
    mock_response = {
        "success": True,
        "reference_id": "LEAVE-2045",
        "days": 3,
    }

    with patch("actions.actions.HRMSAdapter.submit_leave", return_value=mock_response):
        result = action.execute_logic(
            employee_id="EMP-1042",
            leave_type="casual",
            start_date="2026-10-20",
            end_date="2026-10-22",
            reason="Family event",
            confirmation_pending=True,
            user_action="confirm"
        )

    assert result["template_key"] == "submit_leave_result"
    assert result["slots"]["reference_id"] == "LEAVE-2045"
    assert result["slots"]["confirmation_pending"] is False
    assert result["audit_event"] is not None
    assert result["audit_event"]["action_type"] == "leave_submitted"
    assert result["audit_event"]["reference_id"] == "LEAVE-2045"


def test_action_submit_leave_cancels_gracefully():
    """AC 4: Nothing submitted on Cancel"""
    from actions.actions import ActionSubmitLeaveRequest

    action = ActionSubmitLeaveRequest()
    result = action.execute_logic(
        employee_id="EMP-1042",
        leave_type="casual",
        start_date="2026-10-20",
        end_date="2026-10-22",
        reason="Family event",
        confirmation_pending=True,
        user_action="cancel"
    )

    assert result["template_key"] == "submit_leave_cancelled"
    assert "cancelled" in result["response_text"].lower()
    assert result["slots"]["leave_type"] is None
    assert result["slots"]["confirmation_pending"] is False


def test_converse_webhook_leave_request_multi_turn():
    """AC 1-4: Full multi-turn leave request flow via converse webhook"""
    # Turn 1: Initiate leave request
    payload = {
        "sender": "EMP-1042",
        "message": "I want to apply for leave",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }
    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "submit_leave_request"
    assert data["current_form"] == "submit_leave_request"
    assert data["slots"]["requested_slot"] == "leave_type"

    # Turn 2: Provide leave type
    payload["message"] = "casual"
    payload["session"]["slots"] = data["slots"]
    payload["session"]["current_form"] = data["current_form"]
    res = client.post("/webhooks/vario/converse", json=payload)
    data = res.json()
    assert data["slots"]["leave_type"] == "casual"
    assert data["slots"]["requested_slot"] == "start_date"

    # Turn 3: Provide start date
    payload["message"] = "2026-10-20"
    payload["session"]["slots"] = data["slots"]
    res = client.post("/webhooks/vario/converse", json=payload)
    data = res.json()
    assert data["slots"]["start_date"] == "2026-10-20"
    assert data["slots"]["requested_slot"] == "end_date"

    # Turn 4: Provide end date
    payload["message"] = "2026-10-22"
    payload["session"]["slots"] = data["slots"]
    res = client.post("/webhooks/vario/converse", json=payload)
    data = res.json()
    assert data["slots"]["end_date"] == "2026-10-22"
    assert data["slots"]["requested_slot"] == "reason"

    # Turn 5: Provide reason
    payload["message"] = "Family event"
    payload["session"]["slots"] = data["slots"]
    res = client.post("/webhooks/vario/converse", json=payload)
    data = res.json()
    assert data["slots"]["reason"] == "Family event"
    assert data["slots"]["confirmation_pending"] is True
    assert data["template_key"] == "submit_leave_confirmation"

    # Turn 6: Confirm
    payload["message"] = "confirm"
    payload["session"]["slots"] = data["slots"]

    mock_response = {
        "success": True,
        "reference_id": "LEAVE-2045",
        "days": 3,
    }

    # Mock HRMSAdapter at the correct import path for Rasa HR server
    with patch("actions.actions.HRMSAdapter.submit_leave", return_value=mock_response):
        res = client.post("/webhooks/vario/converse", json=payload)
        data = res.json()

    assert data["template_key"] == "submit_leave_result"
    assert data["slots"]["reference_id"] == "LEAVE-2045"
    assert data["audit_event"] is not None
    assert data["audit_event"]["action_type"] == "leave_submitted"

