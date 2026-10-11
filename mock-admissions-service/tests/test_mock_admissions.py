import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "mock-admissions"


def test_get_application_success():
    res = client.get("/applications/APP-1001")
    assert res.status_code == 200
    data = res.json()
    assert data["application_id"] == "APP-1001"
    assert data["applicant_name"] == "Aarav Sharma"
    assert data["program"] == "Computer Science (B.Tech)"
    assert data["status"] == "Under Review"
    assert "next_step" in data
    assert len(data["next_step"]) > 0


def test_get_application_case_insensitive():
    res = client.get("/applications/app-1002")
    assert res.status_code == 200
    data = res.json()
    assert data["application_id"] == "APP-1002"
    assert data["status"] == "Accepted"
    assert "deposit" in data["next_step"].lower() or "50,000" in data["next_step"]


def test_get_application_all_seeded_exist():
    # AC 1: Mock is seeded with several applications
    ids = ["APP-1001", "APP-1002", "APP-1003", "APP-1004"]
    for app_id in ids:
        res = client.get(f"/applications/{app_id}")
        assert res.status_code == 200
        body = res.json()
        assert body["application_id"] == app_id
        assert "status" in body
        assert "next_step" in body


def test_get_application_unknown_returns_404_with_suggested_next_step():
    # AC 3 & FR-17: Unknown application ID carries suggested next step
    res = client.get("/applications/APP-9999")
    assert res.status_code == 404
    body = res.json()
    assert "detail" in body
    detail = body["detail"]
    assert "suggested_next_step" in detail
    assert "admissions@org.example.com" in detail["suggested_next_step"]


def test_get_document_checklist_success():
    # AC 5: Per-program document checklist
    res = client.get("/checklists/btech")
    assert res.status_code == 200
    data = res.json()
    assert data["program"] == "Computer Science (B.Tech)"
    assert isinstance(data["required_documents"], list)
    assert len(data["required_documents"]) >= 3


def test_get_document_checklist_aliases():
    res_mtech = client.get("/checklists/mtech")
    assert res_mtech.status_code == 200
    assert "GATE" in str(res_mtech.json()["required_documents"])

    res_mba = client.get("/checklists/mba")
    assert res_mba.status_code == 200
    assert "CAT" in str(res_mba.json()["required_documents"])


def test_get_document_checklist_not_found():
    res = client.get("/checklists/unknown_degree_xyz")
    assert res.status_code == 404
    body = res.json()
    assert "available_programs" in body["detail"]


def test_get_calendar_success():
    # AC 1 & FR-16: Single configurable admissions calendar
    res = client.get("/calendar")
    assert res.status_code == 200
    data = res.json()
    assert "academic_year" in data
    assert "deadlines" in data
    assert isinstance(data["deadlines"], list)
    assert len(data["deadlines"]) >= 3
    assert "fees" in data
    assert isinstance(data["fees"], list)
    assert len(data["fees"]) >= 3
    assert "refund_policy" in data
