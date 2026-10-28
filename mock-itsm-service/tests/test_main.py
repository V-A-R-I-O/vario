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
