import os
import sys
import logging
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from server import app, classify_message
from actions.hrms_adapter import (
    HRMSAdapter,
    BackendUnavailableError,
    EmployeeNotFoundError,
    LeaveApplicationError,
)
from actions.actions import (
    ActionCheckLeaveBalance,
    ActionAskLeaveConfirm,
    ValidateLeaveRequestForm,
    ActionSubmitLeave,
    ActionCancelLeaveRequest,
)

client = TestClient(app)

# Dates for tests
FUTURE_START_DATE = (date.today() + timedelta(days=7)).isoformat()
FUTURE_END_DATE = (date.today() + timedelta(days=9)).isoformat()
EARLIER_DATE = (date.today() + timedelta(days=6)).isoformat()


# ============================================================================
# Basic Health & NLU Classification Tests
# ============================================================================

def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "rasa-hr"
    assert data["port"] == 5005


def test_webhook_health_check():
    res = client.get("/webhooks/vario/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_classify_variations_of_leave_balance_intent():
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
    off_topic = [
        "what is the weather in Paris today?",
        "order a pepperoni pizza",
        "play a rock song on spotify",
        "how far is Mars from the sun?",
        "what is quantum computing?",
        "tell me a funny joke",
    ]
    for msg in off_topic:
        intent, conf, _ = classify_message(msg)
        assert intent == "nlu_fallback"
        assert conf < 0.4, f"Fallback confidence should be below threshold for: {msg}"


def test_ambiguous_intent_classification():
    ambiguous = [
        "leave",
        "leaves",
        "help with leave",
        "need leave assistance",
        "I want to apply for leave status balance",
    ]
    for q in ambiguous:
        intent, conf, _ = classify_message(q)
        assert intent == "nlu_fallback", f"Query '{q}' should be ambiguous but got {intent}"
        assert conf < 0.4


def test_classify_leave_request_intent():
    utterances = [
        "I want to apply for leave",
        "submit a leave request",
        "apply for leave",
        "request time off",
        "I need to take leave",
        "book leave",
        "apply for vacation",
    ]
    for utt in utterances:
        intent, conf, _ = classify_message(utt)
        assert intent == "submit_leave_request", f"Failed on: {utt}"
        assert conf >= 0.85


def test_classify_wfh_policy_intent():
    utterances = [
        "what is the WFH policy?",
        "what's the WFH policy?",
        "what is the work from home policy?",
        "can I work from home?",
        "how many days can I work remotely?",
        "tell me about the remote work policy",
        "work from home policy",
        "are we allowed to work from home?",
    ]
    for utt in utterances:
        intent, conf, _ = classify_message(utt)
        assert intent == "ask_wfh_policy", f"Failed on: {utt}"
        assert conf >= 0.85


def test_policy_query_edge_cases():
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
        assert intent == "ask_policy_faq", f"Query '{text}' misclassified as {intent}"
        assert conf >= 0.85
        if expected_topic:
            assert entities.get("policy_topic") == expected_topic


def test_classify_greet_and_goodbye():
    for g in ["hi", "hello", "hey", "good morning"]:
        intent, conf, _ = classify_message(g)
        assert intent == "greet"
        assert conf >= 0.9

    for b in ["bye", "goodbye", "see you later", "thanks, bye"]:
        intent, conf, _ = classify_message(b)
        assert intent == "goodbye"
        assert conf >= 0.9


# ============================================================================
# Defect B6 & M2a: Logged-in Identity vs Chat Text
# ============================================================================

def test_b6_logged_in_employee_gets_balance_card_without_asking_id():
    """Defect B6: Given EMP-1001 is logged in, balance card is shown without asking for ID."""
    mock_balance = {
        "found": True,
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "total": 28,
        "casual": 6,
        "sick": 8,
        "earned": 14,
    }
    with patch.object(HRMSAdapter, "get_leave_balance", new_callable=AsyncMock, return_value=mock_balance) as mock_get:
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-101",
                "message": "what is my leave balance?",
                "metadata": {
                    "auth_context": {
                        "employee_id": "EMP-1001",
                        "full_name": "Employee One",
                        "role": "end_user",
                    }
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "check_leave_balance"
        assert data["current_form"] is None
        assert data["current_step"] is None
        assert data["card"] is not None
        assert data["card"]["type"] == "data_card"
        assert data["slots"]["total"] == 28
        assert data["slots"]["casual"] == 6
        assert "28 days" in data["response_text"]
        mock_get.assert_awaited_once_with("EMP-1001")


def test_m2a_typed_id_in_chat_is_ignored_for_balance():
    """Defect M2a: EMP-1001 types 'leave balance for EMP-1042'; returns EMP-1001's balance, NEVER EMP-1042's."""
    mock_balance = {
        "found": True,
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "total": 28,
        "casual": 6,
        "sick": 8,
        "earned": 14,
    }
    with patch.object(HRMSAdapter, "get_leave_balance", new_callable=AsyncMock, return_value=mock_balance) as mock_get:
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-102",
                "message": "what is the leave balance for EMP-1042?",
                "metadata": {
                    "auth_context": {
                        "employee_id": "EMP-1001",
                        "full_name": "Employee One",
                        "role": "end_user",
                    }
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "check_leave_balance"
        assert data["slots"]["total"] == 28
        # HRMS queried strictly with EMP-1001
        mock_get.assert_awaited_once_with("EMP-1001")


def test_m2a_leave_submission_uses_logged_in_employee_and_audits():
    """Defect M2a: Leave submission is filed for the logged-in employee and logs employee in audit."""
    mock_sub = {
        "success": True,
        "reference_id": "LEAVE-9999",
        "employee_id": "EMP-1001",
        "days": 2,
    }
    with patch.object(HRMSAdapter, "submit_leave", new_callable=AsyncMock, return_value=mock_sub) as mock_submit:
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-103",
                "message": "confirm",
                "metadata": {
                    "auth_context": {"employee_id": "EMP-1001", "role": "end_user"}
                },
                "session": {
                    "current_form": "submit_leave_request",
                    "current_step": "leave_confirm",
                    "slots": {
                        "leave_type": "casual",
                        "start_date": FUTURE_START_DATE,
                        "end_date": FUTURE_END_DATE,
                        "reason": "Personal work",
                        "confirmation_pending": True,
                    },
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["template_key"] == "submit_leave_result"
        assert data["audit_event"] is not None
        assert data["audit_event"]["action_type"] == "leave_submitted"
        assert data["audit_event"]["reference_id"] == "LEAVE-9999"
        assert data["audit_event"]["details"]["employee_id"] == "EMP-1001"
        mock_submit.assert_awaited_once_with(
            employee_id="EMP-1001",
            leave_type="casual",
            start_date=FUTURE_START_DATE,
            end_date=FUTURE_END_DATE,
            reason="Personal work",
        )


# ============================================================================
# Defect B2a: HRMS Outage & No Hardcoded Data
# ============================================================================

def test_b2a_outage_returns_unavailable_no_hardcoded_data():
    """Defect B2a: Stopped mock-hrms returns clear 'HR system unavailable' reply; NO hardcoded data."""
    with patch.object(HRMSAdapter, "get_leave_balance", new_callable=AsyncMock, side_effect=BackendUnavailableError("Connection refused")):
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-104",
                "message": "what is my leave balance?",
                "metadata": {
                    "auth_context": {"employee_id": "EMP-1001"}
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "unavailable" in data["response_text"].lower()
        assert data["card"]["type"] == "error"
        assert data["slots"] == {}


def test_b2a_submit_outage_returns_unavailable():
    """Defect B2a: Outage during submission reports HR system unavailable."""
    with patch.object(HRMSAdapter, "submit_leave", new_callable=AsyncMock, side_effect=BackendUnavailableError("Service down")):
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-105",
                "message": "confirm",
                "metadata": {
                    "auth_context": {"employee_id": "EMP-1001"}
                },
                "session": {
                    "current_form": "submit_leave_request",
                    "current_step": "leave_confirm",
                    "slots": {
                        "leave_type": "sick",
                        "start_date": FUTURE_START_DATE,
                        "end_date": FUTURE_END_DATE,
                        "reason": "Doctor visit",
                        "confirmation_pending": True,
                    },
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "unavailable" in data["response_text"].lower()
        assert data["card"]["type"] == "error"


# ============================================================================
# Defect B7 & N5: Questions in Words, Annual Type, Date Validations
# ============================================================================

def test_b7_and_n5_full_leave_request_flow_with_annual_and_natural_dates():
    """Defect B7 & N5: Prompts ask in words, accept 'annual', validate natural dates."""
    # Turn 1: Start request
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": "I want to apply for leave",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": None, "current_step": None, "slots": {}},
        },
    )
    assert res.status_code == 200
    d1 = res.json()
    assert d1["current_form"] == "submit_leave_request"
    assert d1["current_step"] == "leave_type"
    assert "What type of leave" in d1["response_text"]
    assert d1["card"]["type"] == "slot_prompt"

    # Turn 2: Provide 'annual' (Defect N5: accepts 'annual')
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": "annual",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d1["current_form"], "current_step": d1["current_step"], "slots": d1["slots"]},
        },
    )
    assert res.status_code == 200
    d2 = res.json()
    assert d2["slots"]["leave_type"] == "annual"
    assert d2["current_step"] == "start_date"
    assert "start date" in d2["response_text"].lower()

    # Turn 2b: Invalid past date guidance (AC 3)
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": "2020-01-01",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d2["current_form"], "current_step": d2["current_step"], "slots": d2["slots"]},
        },
    )
    assert res.status_code == 200
    d2b = res.json()
    assert d2b["current_step"] == "start_date"
    assert "cannot be in the past" in d2b["response_text"].lower()

    # Turn 3: Valid date (Defect N5: natural language 'tomorrow')
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": "tomorrow",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d2b["current_form"], "current_step": d2b["current_step"], "slots": d2b["slots"]},
        },
    )
    assert res.status_code == 200
    d3 = res.json()
    assert d3["slots"]["start_date"] == tomorrow
    assert d3["current_step"] == "end_date"
    assert "end date" in d3["response_text"].lower()

    # Turn 3b: End date before start date guidance
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": date.today().isoformat(),  # today is before tomorrow
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d3["current_form"], "current_step": d3["current_step"], "slots": d3["slots"]},
        },
    )
    assert res.status_code == 200
    d3b = res.json()
    assert d3b["current_step"] == "end_date"
    assert "on or after" in d3b["response_text"].lower()

    # Turn 4: Valid end date
    future_end = (date.today() + timedelta(days=5)).isoformat()
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": future_end,
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d3b["current_form"], "current_step": d3b["current_step"], "slots": d3b["slots"]},
        },
    )
    assert res.status_code == 200
    d4 = res.json()
    assert d4["slots"]["end_date"] == future_end
    assert d4["current_step"] == "reason"

    # Turn 5: Reason
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-flow",
            "message": "Attending annual summit",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {"current_form": d4["current_form"], "current_step": d4["current_step"], "slots": d4["slots"]},
        },
    )
    assert res.status_code == 200
    d5 = res.json()
    assert d5["current_step"] == "leave_confirm"
    assert d5["card"]["type"] == "confirmation"
    assert "Attending annual summit" in d5["response_text"]


# ============================================================================
# Defect M1a: Slots Reset After Submit or Cancel
# ============================================================================

def test_m1a_second_leave_request_asks_every_question_again():
    """Defect M1a: After completing a request, a second request does NOT reuse old dates/reason."""
    mock_sub = {"success": True, "reference_id": "LEAVE-101", "days": 2}
    with patch.object(HRMSAdapter, "submit_leave", new_callable=AsyncMock, return_value=mock_sub):
        # 1. Complete first request
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-fresh",
                "message": "confirm",
                "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
                "session": {
                    "current_form": "submit_leave_request",
                    "current_step": "leave_confirm",
                    "slots": {
                        "leave_type": "sick",
                        "start_date": FUTURE_START_DATE,
                        "end_date": FUTURE_END_DATE,
                        "reason": "Old fever reason",
                        "confirmation_pending": True,
                    },
                },
            },
        )
        assert res.status_code == 200
        completed = res.json()
        assert completed["current_form"] is None

        # 2. Start a second request
        res2 = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-fresh",
                "message": "I want to apply for leave",
                "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
                "session": {"current_form": None, "current_step": None, "slots": {}},
            },
        )
        assert res2.status_code == 200
        d2 = res2.json()
        # Must ask for leave_type again; old dates and reason must NOT be present!
        assert d2["current_step"] == "leave_type"
        assert d2["slots"].get("start_date") is None
        assert d2["slots"].get("reason") is None


def test_m1a_cancel_resets_slots():
    """Defect M1a: Cancelling resets slots completely."""
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-cancel",
            "message": "cancel",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {
                "current_form": "submit_leave_request",
                "current_step": "start_date",
                "slots": {"leave_type": "casual"},
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_form"] is None
    assert data["slots"] == {}
    assert "cancelled" in data["response_text"].lower()


# ============================================================================
# Defect M3a: Off-script Confirmation Reply & Mid-Form Cancel
# ============================================================================

def test_m3a_off_script_reply_at_confirmation_re_asks_cleanly():
    """Defect M3a: Off-script reply at confirmation re-asks instead of trapping user."""
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-offscript",
            "message": "hmm wait",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {
                "current_form": "submit_leave_request",
                "current_step": "leave_confirm",
                "slots": {
                    "leave_type": "casual",
                    "start_date": FUTURE_START_DATE,
                    "end_date": FUTURE_END_DATE,
                    "reason": "Family trip",
                    "confirmation_pending": True,
                },
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_form"] == "submit_leave_request"
    assert data["current_step"] == "leave_confirm"
    assert "Please reply 'confirm' to submit or 'cancel' to exit" in data["response_text"]
    assert data["card"]["type"] == "confirmation"


def test_m3a_cancel_exits_from_confirmation_step():
    """Defect M3a: Sending 'cancel' at confirmation step cleanly exits."""
    res = client.post(
        "/webhooks/vario/converse",
        json={
            "sender": "conv-cancel-step",
            "message": "cancel",
            "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            "session": {
                "current_form": "submit_leave_request",
                "current_step": "leave_confirm",
                "slots": {
                    "leave_type": "casual",
                    "start_date": FUTURE_START_DATE,
                    "end_date": FUTURE_END_DATE,
                    "reason": "Family trip",
                    "confirmation_pending": True,
                },
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_form"] is None
    assert data["slots"] == {}
    assert "cancelled" in data["response_text"].lower()


# ============================================================================
# Defect M4a: Off-topic Policy Questions
# ============================================================================

def test_m4a_travel_policy_triggers_clarification():
    """Defect M4a: 'what is the travel reimbursement policy?' clarifies, NOT generic leave policy."""
    for query in ["what is the travel reimbursement policy?", "dress code policy", "rules"]:
        res = client.post(
            "/webhooks/vario/converse",
            json={
                "sender": "conv-travel",
                "message": query,
                "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "nlu_fallback"
        assert "20 annual leaves" not in data["response_text"]
        assert "I can help with leave" in data["response_text"]


# ============================================================================
# Defect M5a: Greet and Goodbye Responses
# ============================================================================

def test_m5a_greet_and_goodbye_no_debug_text():
    """Defect M5a: HR replies with friendly greeting and goodbye without debug text."""
    res_greet = client.post(
        "/webhooks/vario/converse",
        json={"sender": "user-1", "message": "hi"},
    )
    assert res_greet.status_code == 200
    data_g = res_greet.json()
    assert "Intent 'greet' acknowledged" not in data_g["response_text"]
    assert "Hello! I am your VARIO HR Assistant" in data_g["response_text"]

    res_bye = client.post(
        "/webhooks/vario/converse",
        json={"sender": "user-1", "message": "bye"},
    )
    assert res_bye.status_code == 200
    data_b = res_bye.json()
    assert "Intent 'goodbye' acknowledged" not in data_b["response_text"]
    assert "Thank you for contacting HR" in data_b["response_text"]


# ============================================================================
# Action Classes & Date Utils Direct Tests
# ============================================================================

@pytest.mark.anyio
async def test_action_check_leave_balance_direct():
    action = ActionCheckLeaveBalance()
    assert action.name() == "action_check_leave_balance"

    dispatcher = MagicMock()
    tracker = MagicMock()
    tracker.latest_message = {
        "text": "what is my leave balance?",
        "metadata": {"auth_context": {"employee_id": "EMP-1001"}},
    }

    mock_balance = {
        "found": True,
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "total": 28,
        "casual": 6,
        "sick": 8,
        "earned": 14,
    }
    with patch.object(HRMSAdapter, "get_leave_balance", new_callable=AsyncMock, return_value=mock_balance):
        events = await action.run(dispatcher, tracker, {})
        assert events == []
        dispatcher.utter_message.assert_called_once()
        _, kwargs = dispatcher.utter_message.call_args
        assert "28 days" in kwargs["text"]
        vario = kwargs["json_message"]["vario"]
        assert vario["template_key"] == "check_leave_balance_response"
        assert vario["slots"]["total"] == 28


@pytest.mark.anyio
async def test_validate_leave_request_form_direct():
    validator = ValidateLeaveRequestForm()
    assert validator.name() == "validate_leave_request_form"

    dispatcher = MagicMock()
    tracker = MagicMock()

    # Validate leave type 'annual'
    res_lt = await validator.validate_leave_type("annual", dispatcher, tracker, {})
    assert res_lt == {"leave_type": "annual"}

    # Validate relative date 'tomorrow'
    res_sd = await validator.validate_start_date("tomorrow", dispatcher, tracker, {})
    expected_start = (date.today() + timedelta(days=1)).isoformat()
    assert res_sd == {"start_date": expected_start}

    # Validate past date returns None
    res_past = await validator.validate_start_date("2020-01-01", dispatcher, tracker, {})
    assert res_past == {"start_date": None}
