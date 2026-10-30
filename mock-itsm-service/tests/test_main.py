"""Contract tests for the Mock ITSM service."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed_data import reset_seed_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    reset_seed_data()
    yield
    reset_seed_data()


def test_health_and_seeded_tickets():
    assert client.get("/health").json()["service"] == "mock-itsm"
    tickets = client.get("/tickets").json()["tickets"]
    assert len(tickets) >= 3
    assert {ticket["status"] for ticket in tickets} >= {"Open", "In Progress", "Resolved"}


def test_ticket_not_found():
    assert client.get("/tickets/IT-9999").status_code == 404


def test_create_ticket_and_fetch_status():
    response = client.post("/tickets", json={"category": "software", "description": "Install editor", "reporter": "EMP-1042"})
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["ticket_id"] == "IT-1004"
    assert ticket["status"] == "Open"
    assert client.get(f"/tickets/{ticket['ticket_id']}").json()["description"] == "Install editor"


def test_ticket_creation_rejects_unknown_reporter():
    response = client.post("/tickets", json={"category": "software", "description": "Install editor", "reporter": "EMP-9999"})
    assert response.status_code == 404


def test_identity_verification_and_reset_guard():
    assert client.post("/password/reset", json={"employee_id": "EMP-1042"}).status_code == 403
    wrong = client.post("/identity/verify", json={"employee_id": "EMP-1042", "answer": "wrong"})
    assert wrong.status_code == 200
    assert wrong.json()["verified"] is False
    correct = client.post("/identity/verify", json={"employee_id": "EMP-1042", "answer": "Mysuru"})
    assert correct.json()["verified"] is True
    assert "security_answer" not in correct.json()
    assert client.post("/password/reset", json={"employee_id": "EMP-1042"}).json()["success"] is True
    assert client.post("/password/reset", json={"employee_id": "EMP-1042"}).status_code == 403


def test_security_question_endpoint_returns_question_without_answer():
    response = client.get("/identity/EMP-1042/question")
    assert response.status_code == 200
    assert response.json()["security_question"] == "What city were you born in?"
    assert "security_answer" not in response.json()
    assert "mysuru" not in str(response.json()).casefold()


def test_security_question_endpoint_rejects_unknown_employee():
    response = client.get("/identity/EMP-9999/question")
    assert response.status_code == 404


def test_three_failed_answers_lock_account_across_flow_restarts():
    for attempt in range(3):
        response = client.post("/identity/verify", json={"employee_id": "EMP-1042", "answer": f"wrong-{attempt}"})
        assert response.status_code == 200
        assert response.json()["verified"] is False
    locked = client.post("/identity/verify", json={"employee_id": "EMP-1042", "answer": "Mysuru"})
    assert locked.status_code == 200
    assert locked.json()["locked"] is True
    assert locked.json()["attempts_remaining"] == 0
    assert client.post("/password/reset", json={"employee_id": "EMP-1042"}).status_code == 403


def test_identity_lockout_survives_module_reload():
    import importlib
    from app import seed_data as seed_module

    for attempt in range(3):
        state = seed_module.record_identity_failure("EMP-1042")
        assert state["attempts"] == attempt + 1
    assert seed_module.identity_attempt_state("EMP-1042")["locked"] is True

    importlib.reload(seed_module)
    restored = seed_module.identity_attempt_state("EMP-1042")
    assert restored["locked"] is True
    assert restored["attempts_remaining"] == 0
