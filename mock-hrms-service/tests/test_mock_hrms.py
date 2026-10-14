import pytest
import time
from fastapi.testclient import TestClient

from app.main import app
from app.seed_data import reset_seed_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    reset_seed_data()
    yield
    reset_seed_data()


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "mock-hrms"


def test_seeded_employees_balances():
    # AC 1: Pre-seeded with several employees each having casual/sick/earned balances
    seeded_ids = ["EMP-1001", "EMP-1042", "EMP-2001", "EMP-3001", "EMP-4001"]
    for emp_id in seeded_ids:
        res = client.get(f"/employees/{emp_id}/leave-balance")
        assert res.status_code == 200, f"Failed for {emp_id}"
        data = res.json()
        assert data["employee_id"] == emp_id
        assert "breakdown" in data
        breakdown = data["breakdown"]
        assert "casual" in breakdown and isinstance(breakdown["casual"], (int, float))
        assert "sick" in breakdown and isinstance(breakdown["sick"], (int, float))
        assert "earned" in breakdown and isinstance(breakdown["earned"], (int, float))
        assert data["total"] == breakdown["casual"] + breakdown["sick"] + breakdown["earned"]


def test_get_leave_balance_success():
    # AC 2: Given seeded employee_id, returns structured balance (total + per-type breakdown)
    res = client.get("/employees/EMP-1042/leave-balance")
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == "EMP-1042"
    assert data["employee_name"] == "Jane Smith"
    assert data["total"] == 22
    assert data["breakdown"] == {
        "casual": 4,
        "sick": 6,
        "earned": 12,
    }

    # Also test alias route /leave/balance/{employee_id}
    res_alias = client.get("/leave/balance/EMP-1042")
    assert res_alias.status_code == 200
    assert res_alias.json() == data


def test_get_leave_balance_unknown_employee():
    # AC 3 backend: Unknown employee returns 404
    res = client.get("/employees/EMP-9999/leave-balance")
    assert res.status_code == 404
    detail = res.json()["detail"]
    assert "not found" in detail["message"].lower()
    assert detail["employee_id"] == "EMP-9999"


def test_get_leave_status_success():
    res = client.get("/employees/EMP-1001/leave-status")
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == "EMP-1001"
    assert len(data["applications"]) >= 1
    first_app = data["applications"][0]
    assert first_app["reference_id"] == "LEAVE-2031"
    assert first_app["leave_type"] == "casual"
    assert first_app["status"] == "approved"

    # Filter by reference_id
    filtered = client.get("/employees/EMP-1001/leave-status?reference_id=LEAVE-2031")
    assert filtered.status_code == 200
    assert len(filtered.json()["applications"]) == 1

    # Filter by non-existent reference_id
    filtered_none = client.get("/employees/EMP-1001/leave-status?reference_id=LEAVE-9999")
    assert filtered_none.status_code == 200
    assert len(filtered_none.json()["applications"]) == 0


def test_get_leave_status_unknown_employee():
    res = client.get("/employees/EMP-9999/leave-status")
    assert res.status_code == 404


def test_submit_leave_success():
    # Deliverable: submit leave (returns a reference ID)
    payload = {
        "employee_id": "EMP-1042",
        "leave_type": "casual",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "reason": "Family obligation",
    }
    res = client.post("/leave/submit", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["reference_id"].startswith("LEAVE-")
    assert data["days"] == 2
    assert data["leave_type"] == "casual"
    assert data["remaining_balance"]["breakdown"]["casual"] == 2  # 4 - 2 = 2
    assert data["remaining_balance"]["total"] == 20

    # Verify that the record now appears in leave-status
    status_res = client.get("/employees/EMP-1042/leave-status")
    assert status_res.status_code == 200
    history = status_res.json()["applications"]
    assert any(h["reference_id"] == data["reference_id"] for h in history)


def test_submit_leave_invalid_dates():
    # End date before start date
    payload = {
        "employee_id": "EMP-1042",
        "leave_type": "sick",
        "start_date": "2026-11-05",
        "end_date": "2026-11-01",
        "reason": "Invalid range",
    }
    res = client.post("/leave/submit", json=payload)
    assert res.status_code == 400
    assert "cannot be after" in res.json()["detail"]

    # Malformed date format
    payload["end_date"] = "invalid-date"
    res = client.post("/leave/submit", json=payload)
    assert res.status_code == 400


def test_submit_leave_invalid_type():
    payload = {
        "employee_id": "EMP-1042",
        "leave_type": "unsupported_type",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "reason": "Test",
    }
    res = client.post("/leave/submit", json=payload)
    assert res.status_code == 400
    assert "Invalid leave type" in res.json()["detail"]


def test_submit_leave_unknown_employee():
    payload = {
        "employee_id": "EMP-9999",
        "leave_type": "casual",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "reason": "Test",
    }
    res = client.post("/leave/submit", json=payload)
    assert res.status_code == 404


def test_policy_lookup():
    # Deliverable: policy lookup
    res = client.get("/policies")
    assert res.status_code == 200
    policies = res.json()["policies"]
    assert len(policies) >= 3
    policy_ids = [p["policy_id"] for p in policies]
    assert "leave-policy" in policy_ids
    assert "wfh-policy" in policy_ids

    # Lookup specific policy
    leave_res = client.get("/policies/leave-policy")
    assert leave_res.status_code == 200
    assert leave_res.json()["policy_id"] == "leave-policy"
    assert "entitled to 8 casual days" in leave_res.json()["details"]

    # Lookup unknown policy
    not_found = client.get("/policies/nonexistent-policy")
    assert not_found.status_code == 404


def test_artificial_delay():
    # Optional requirement: an artificial delay flag on the mock
    start = time.perf_counter()
    res = client.get("/health", headers={"X-Mock-Delay": "0.1"})
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed >= 0.08

    # Query param delay
    start = time.perf_counter()
    res = client.get("/employees/EMP-1001/leave-balance?delay=0.1")
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed >= 0.08
