"""Regression tests for the Mock HRMS service contracts."""
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


def test_health_and_employee_demo_records():
    assert client.get("/health").json()["service"] == "mock-hrms"
    for employee_id in ("EMP-1001", "EMP-2001", "EMP-3001", "EMP-4001", "EMP-1010", "EMP-1011", "EMP-1012", "EMP-1013"):
        response = client.get(f"/employees/{employee_id}/leave-balance")
        assert response.status_code == 200
        assert response.json()["employee_id"] == employee_id


def test_unknown_employee_is_not_found():
    assert client.get("/employees/EMP-9999/leave-balance").status_code == 404


def test_policy_lookup_returns_seeded_policy():
    response = client.get("/policies/leave")
    assert response.status_code == 200
    assert response.json()
