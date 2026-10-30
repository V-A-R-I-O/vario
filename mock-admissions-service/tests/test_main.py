"""Regression tests for the Mock Admissions service contracts."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    assert client.get("/health").json()["service"] == "mock-admissions"


def test_seeded_application_lookup_and_unknown_application():
    response = client.get("/applications/APP-1001")
    assert response.status_code == 200
    assert response.json()["application_id"] == "APP-1001"
    assert client.get("/applications/APP-9999").status_code == 404


def test_document_checklist_supports_known_program_aliases():
    response = client.get("/checklists/btech")
    assert response.status_code == 200
    assert response.json()["required_documents"]
    assert client.get("/checklists/unknown-program").status_code == 404


def test_calendar_is_available():
    response = client.get("/calendar")
    assert response.status_code == 200
    assert response.json()["academic_year"]
