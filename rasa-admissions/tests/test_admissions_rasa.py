import pytest
from fastapi.testclient import TestClient

from server import app, classify_message
from actions.actions import ActionCheckApplicationStatus, ActionGetDocumentChecklist, ActionAskFeeDeadline

client = TestClient(app)


def test_health_check_endpoint():
    # AC 1: Service is reachable at RASA_ADMISSIONS_URL
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "rasa-admissions"
    assert data["port"] == 5007


def test_classify_variations_of_status_intent():
    # AC 2: Variations of "what's the status of application APP-1001" classify check_application_status and extract application_id
    utterances = [
        "what's the status of application APP-1001",
        "check the status of APP-1001",
        "Can you check APP-1001 for me?",
        "what is happening with application APP-1001?",
        "status of APP-1001",
        "APP-1001 status update please",
    ]

    for utt in utterances:
        intent, conf, entities = classify_message(utt)
        assert intent == "check_application_status", f"Failed on: {utt}"
        assert conf >= 0.85
        assert entities.get("application_id") == "APP-1001"


def test_classify_different_application_ids():
    test_cases = [
        ("track my application APP-1002", "APP-1002"),
        ("please check APP-1003 decision", "APP-1003"),
        ("is APP-1004 accepted or rejected?", "APP-1004"),
    ]

    for text, expected_id in test_cases:
        intent, conf, entities = classify_message(text)
        assert intent == "check_application_status"
        assert entities.get("application_id") == expected_id


def test_off_topic_triggers_nlu_fallback():
    # AC 3: Given an off-topic message, then nlu_fallback fires (confidence < 0.4)
    off_topic_messages = [
        "what is the weather in Paris today?",
        "order a pepperoni pizza",
        "play a rock song on spotify",
        "how far is Mars from the sun?",
    ]

    for msg in off_topic_messages:
        intent, conf, _ = classify_message(msg)
        assert intent == "nlu_fallback"
        assert conf < 0.4, f"Fallback confidence should be below threshold for: {msg}"


def test_action_check_application_status_skeleton():
    # AC 5: Given action_check_application_status, then it exists and returns a template_key + slots shape
    action = ActionCheckApplicationStatus()
    assert action.name() == "action_check_application_status"

    result = action.execute_logic("APP-1001")
    assert result["template_key"] == "check_application_status_response"
    assert "slots" in result
    assert result["slots"]["application_id"] == "APP-1001"
    assert result["slots"]["status"] == "Under Review"
    assert "next_step" in result["slots"]


def test_converse_webhook_success_roundtrip():
    # ADR-002 converse contract verification
    payload = {
        "sender": "user-test-123",
        "message": "What is the status of application APP-1001?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_application_status"
    assert data["confidence"] >= 0.85
    assert data["entities"]["application_id"] == "APP-1001"
    assert data["template_key"] == "check_application_status_response"
    assert data["slots"]["application_id"] == "APP-1001"
    assert data["slots"]["status"] == "Under Review"
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


def test_action_check_application_status_missing_id():
    # Regression test: missing ID must not default to APP-1001
    action = ActionCheckApplicationStatus()
    for empty_id in [None, "", "   "]:
        result = action.execute_logic(empty_id)
        assert result["template_key"] is None
        assert "application_id" not in result["slots"]
        assert result["missing_slot"] == "application_id"
        assert "Please provide your application ID" in result["response_text"]


def test_converse_webhook_missing_id_requests_application_id():
    # Regression test: user asking for status without ID must be prompted for ID
    payload = {
        "sender": "user-test-no-id",
        "message": "what is the status of my application?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_application_status"
    assert data["template_key"] is None
    assert data["current_form"] == "check_application_status_form"
    assert data["current_step"] == "await_application_id"
    assert "Please provide your application ID" in data["response_text"]
    assert data["slots"].get("application_id") is None


def test_converse_webhook_unknown_application_id_graceful_not_found():
    # FR-17: Graceful "not found" with suggested next step when application ID is unknown
    payload = {
        "sender": "user-test-456",
        "message": "Can you check status of APP-9999?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "check_application_status"
    assert data["confidence"] >= 0.85
    assert data["entities"]["application_id"] == "APP-9999"
    assert data["template_key"] == "check_application_status_not_found_response"
    assert data["slots"]["application_id"] == "APP-9999"
    assert data["slots"]["status"] == "Not Found"
    assert data["slots"]["found"] is False
    assert "suggested_next_step" in data["slots"]
    assert "admissions@org.example.com" in data["slots"]["suggested_next_step"]
    assert data["response_text"] is not None
    assert "APP-9999 was not found" in data["response_text"]


def test_action_check_application_status_not_found():
    # Verify execute_logic directly with an unknown application ID
    action = ActionCheckApplicationStatus()
    result = action.execute_logic("APP-8888")

    assert result["template_key"] == "check_application_status_not_found_response"
    assert result["slots"]["status"] == "Not Found"
    assert result["slots"]["found"] is False
    assert "suggested_next_step" in result["slots"]
    assert "APP-8888" in result["response_text"]


def test_ambiguous_classification_triggers_fallback():
    # Regression test: FallbackClassifier triggers nlu_fallback when confidences are within ambiguity_threshold
    ambiguous_queries = [
        "what about documents and fees?",
        "can you tell me about documents and fees?",
        "tuition fees and required documents checklist",
        "document checklist and fee deadline",
    ]

    for q in ambiguous_queries:
        intent, conf, _ = classify_message(q)
        assert intent == "nlu_fallback", f"Ambiguous query '{q}' should trigger nlu_fallback"

        # Also test roundtrip via webhook
        res = client.post("/webhooks/vario/converse", json={"sender": "amb-user", "message": q})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "nlu_fallback"
        assert data["template_key"] is None
        assert "didn't quite understand" in data["response_text"]


# --- Slice 25: adm-checklist tests (SCRUM-27) ---

def test_action_get_document_checklist_success():
    # AC-1: Given a program, when applicant asks for checklist, returns list
    action = ActionGetDocumentChecklist()
    assert action.name() == "action_get_document_checklist"

    for prog in ["btech", "Computer Science", "mtech", "mba"]:
        result = action.execute_logic(prog)
        assert result["template_key"] == "get_document_checklist_response"
        assert result["missing_slot"] is None
        assert result["slots"]["found"] is True
        assert isinstance(result["slots"]["required_documents"], list)
        assert len(result["slots"]["required_documents"]) >= 3
        assert result["slots"]["items_summary"]
        assert result["response_text"] is not None


def test_action_get_document_checklist_missing_program():
    # AC-2: Given no program specified, prompts for program (slot prompt)
    action = ActionGetDocumentChecklist()
    for empty_prog in [None, "", "   "]:
        result = action.execute_logic(empty_prog)
        assert result["template_key"] is None
        assert result["missing_slot"] == "program"
        assert result["current_form"] == "get_document_checklist_form"
        assert result["current_step"] == "await_program"
        assert "Which program would you like the document checklist for?" in result["response_text"]


def test_action_get_document_checklist_not_found():
    # AC-3: Given an unknown program, graceful not-found without crashing
    action = ActionGetDocumentChecklist()
    result = action.execute_logic("Robotics and Automation")
    assert result["template_key"] == "get_document_checklist_not_found_response"
    assert result["slots"]["found"] is False
    assert result["slots"]["program"] == "robotics and automation"
    assert isinstance(result["slots"]["available_programs"], list)
    assert len(result["slots"]["available_programs"]) >= 1
    assert "No document checklist found" in result["response_text"]


def test_classify_document_checklist_intent():
    utterances = [
        ("what documents do I need for btech?", "btech"),
        ("document checklist for Computer Science", "computer science"),
        ("which certificates are required for mtech?", "mtech"),
        ("checklist of documents for mba", "mba"),
        ("what do I need to submit for Data Science?", "data science"),
    ]

    for utt, expected_prog in utterances:
        intent, conf, entities = classify_message(utt)
        assert intent == "get_document_checklist", f"Failed intent for: {utt}"
        assert conf >= 0.85, f"Confidence too low for: {utt}"
        assert entities.get("program", "").lower() == expected_prog.lower()


def test_converse_webhook_document_checklist_success():
    # AC-1 & ADR-002: End-to-end webhook call with specified program
    payload = {
        "sender": "user-chk-1",
        "message": "what documents do I need for btech?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "get_document_checklist"
    assert data["confidence"] >= 0.85
    assert data["template_key"] == "get_document_checklist_response"
    assert data["slots"]["found"] is True
    assert isinstance(data["slots"]["required_documents"], list)
    assert len(data["slots"]["required_documents"]) >= 3
    assert data["current_form"] is None
    assert data["current_step"] is None


def test_converse_webhook_document_checklist_slot_prompt():
    # AC-2: Webhook without program returns slot prompt
    payload = {
        "sender": "user-chk-2",
        "message": "list of documents needed for admission",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "get_document_checklist"
    assert data["template_key"] is None
    assert data["current_form"] == "get_document_checklist_form"
    assert data["current_step"] == "await_program"
    assert "Which program would you like the document checklist for?" in data["response_text"]


def test_converse_webhook_document_checklist_multiturn_flow():
    # Multi-turn dialogue: Prompt followed by applicant providing program
    turn1_payload = {
        "sender": "user-chk-3",
        "message": "document requirements for admission",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }
    res1 = client.post("/webhooks/vario/converse", json=turn1_payload)
    assert res1.status_code == 200
    turn1_data = res1.json()
    assert turn1_data["current_step"] == "await_program"

    # Turn 2: User answers with program
    turn2_payload = {
        "sender": "user-chk-3",
        "message": "Computer Science (B.Tech)",
        "session": {
            "current_form": turn1_data["current_form"],
            "current_step": turn1_data["current_step"],
            "slots": turn1_data["slots"],
        },
    }
    res2 = client.post("/webhooks/vario/converse", json=turn2_payload)
    assert res2.status_code == 200
    turn2_data = res2.json()

    assert turn2_data["intent"] == "get_document_checklist"
    assert turn2_data["template_key"] == "get_document_checklist_response"
    assert turn2_data["slots"]["found"] is True
    assert isinstance(turn2_data["slots"]["required_documents"], list)
    assert turn2_data["current_form"] is None
    assert turn2_data["current_step"] is None


def test_converse_webhook_document_checklist_not_found():
    # AC-3: Graceful not-found for unknown program
    payload = {
        "sender": "user-chk-4",
        "message": "what documents do I need for Astrophysics?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "get_document_checklist"
    assert data["template_key"] == "get_document_checklist_not_found_response"
    assert data["slots"]["found"] is False
    assert "available_programs" in data["slots"]
    assert "No document checklist found" in data["response_text"]


# --- Slice 26: adm-fee-deadline tests (SCRUM-38) ---

def test_action_ask_fee_deadline_tuition_fee():
    # AC-1: Given a fee question, return fee from calendar
    action = ActionAskFeeDeadline()
    assert action.name() == "action_ask_fee_deadline"

    test_cases = [
        ("how much is the tuition fee for B.Tech?", "3,20,000", "Computer Science"),
        ("tuition fee for MBA program", "4,50,000", "MBA"),
        ("what is the application fee?", "1,500", "Application Fee"),
        ("how much is the hostel fee?", "75,000", "Hostel Fee"),
    ]

    for q, expected_amt, expected_item in test_cases:
        result = action.execute_logic(q)
        assert result["template_key"] == "ask_fee_deadline_response"
        assert result["slots"]["academic_year"] == "2026-2027"
        assert expected_amt in result["slots"]["details"]
        assert expected_amt in result["response_text"]
        assert any(expected_item in f["item"] for f in result["slots"].get("fees", []))


def test_action_ask_fee_deadline_submission_deadline():
    # AC-2: Given a deadline question, return relevant deadline from calendar
    action = ActionAskFeeDeadline()

    test_cases = [
        ("what is the last date to submit the application?", "November 30, 2026", "Submission Deadline"),
        ("when is the document verification deadline?", "December 10, 2026", "Document Verification"),
        ("when does the merit list come out?", "December 18, 2026", "Merit List"),
        ("what is the second merit list deadline?", "December 28, 2026", "Second Merit"),
        ("when do classes commence?", "January 15, 2027", "Orientation"),
    ]

    for q, expected_date, expected_milestone in test_cases:
        result = action.execute_logic(q)
        assert result["template_key"] == "ask_fee_deadline_response"
        assert result["slots"]["academic_year"] == "2026-2027"
        assert expected_date in result["slots"]["details"]
        assert expected_date in result["response_text"]
        assert any(expected_milestone in d["milestone"] for d in result["slots"].get("deadlines", []))


def test_action_ask_fee_deadline_dynamic_calendar_update():
    # AC-3: Given a change to calendar (in Mock Admissions), answers update accordingly
    action = ActionAskFeeDeadline()
    from actions.actions import OFFLINE_CALENDAR

    # Mutate offline calendar / test calendar data
    original_deadlines = list(OFFLINE_CALENDAR["deadlines"])
    try:
        OFFLINE_CALENDAR["deadlines"] = original_deadlines + [
            {"milestone": "Spot Round Registration Deadline", "date": "February 1, 2027"}
        ]
        result = action.execute_logic("when is spot round registration deadline?")
        assert result["template_key"] == "ask_fee_deadline_response"
        assert "February 1, 2027" in result["slots"]["details"]
        assert "Spot Round Registration Deadline" in str(result["slots"].get("deadlines", []))
    finally:
        OFFLINE_CALENDAR["deadlines"] = original_deadlines


def test_action_ask_fee_deadline_clarification_on_vague_query():
    # AC-4: Given a low-confidence or vague question, ask for clarification rather than guessing
    action = ActionAskFeeDeadline()
    for vague_q in ["when?", "how much?", "fees?", "deadline?", "when", "fee"]:
        result = action.execute_logic(vague_q)
        assert result["needs_clarification"] is True
        assert result["template_key"] is None
        assert "clarify whether you are asking about tuition fees" in result["response_text"]


def test_classify_fee_deadline_intents():
    fee_deadline_queries = [
        "when is the last date to pay fees?",
        "what are the admission deadlines?",
        "how much is the tuition fee for B.Tech?",
        "what is the last date to submit the application?",
        "admission fee structure and payment dates",
        "when does the merit list come out?",
        "what is the refund policy for admission fees?",
        "when is the document verification deadline?",
        "tuition fee for MBA program",
        "what is the application fee?",
        "how much is the hostel fee?",
        "what are the fee deadlines?",
    ]

    for q in fee_deadline_queries:
        intent, conf, _ = classify_message(q)
        assert intent == "ask_fee_deadline", f"Failed for query: {q}"
        assert conf >= 0.80, f"Low confidence for: {q}"


def test_converse_webhook_fee_query_success():
    # AC-1 & ADR-002: Converse webhook roundtrip for fee inquiry
    payload = {
        "sender": "user-fee-1",
        "message": "how much is the tuition fee for B.Tech?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "ask_fee_deadline"
    assert data["confidence"] >= 0.85
    assert data["template_key"] == "ask_fee_deadline_response"
    assert data["slots"]["academic_year"] == "2026-2027"
    assert "3,20,000" in data["slots"]["details"]
    assert "3,20,000" in data["response_text"]
    assert data["current_form"] is None


def test_converse_webhook_deadline_query_success():
    # AC-2 & ADR-002: Converse webhook roundtrip for deadline inquiry
    payload = {
        "sender": "user-dl-1",
        "message": "what is the last date to submit the application?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "ask_fee_deadline"
    assert data["confidence"] >= 0.85
    assert data["template_key"] == "ask_fee_deadline_response"
    assert data["slots"]["academic_year"] == "2026-2027"
    assert "November 30, 2026" in data["slots"]["details"]
    assert "November 30, 2026" in data["response_text"]


def test_converse_webhook_refund_policy_success():
    payload = {
        "sender": "user-ref-1",
        "message": "what is the refund policy for admission fees?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "ask_fee_deadline"
    assert data["template_key"] == "ask_fee_deadline_response"
    assert "100% refund" in data["slots"]["details"]
    assert "refund_policy" in data["slots"]


def test_converse_webhook_vague_fee_query_requests_clarification():
    # AC-4: Vague query in converse endpoint requests clarification
    payload = {
        "sender": "user-vague-1",
        "message": "when?",
        "session": {"current_form": None, "current_step": None, "slots": {}},
    }

    res = client.post("/webhooks/vario/converse", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["template_key"] is None
    assert "clarify whether you are asking about tuition fees" in data["response_text"]



