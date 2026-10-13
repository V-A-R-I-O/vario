import pytest
import sys
import types
import importlib.util
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Load mock-hrms-service in an isolated namespace to avoid collision with backend app
repo_root = Path(__file__).resolve().parent.parent.parent
mock_hrms_dir = repo_root / "mock-hrms-service"

mock_pkg = types.ModuleType("mock_hrms_app")
sys.modules["mock_hrms_app"] = mock_pkg

seed_spec = importlib.util.spec_from_file_location(
    "mock_hrms_app.seed_data", mock_hrms_dir / "app" / "seed_data.py"
)
seed_mod = importlib.util.module_from_spec(seed_spec)
sys.modules["mock_hrms_app.seed_data"] = seed_mod
seed_spec.loader.exec_module(seed_mod)

main_spec = importlib.util.spec_from_file_location(
    "mock_hrms_app.main", mock_hrms_dir / "app" / "main.py"
)
main_mod = importlib.util.module_from_spec(main_spec)
sys.modules["mock_hrms_app.main"] = main_mod
main_spec.loader.exec_module(main_mod)
mock_hrms_app = main_mod.app
reset_seed_data = seed_mod.reset_seed_data

from app.services.hrms_adapter import (
    HRMSAdapter,
    BackendUnavailableError,
    EmployeeNotFoundError,
)


@pytest.fixture(autouse=True)
def reset_mock_state():
    reset_seed_data()
    yield
    reset_seed_data()


@pytest.fixture
def mock_asgi_transport():
    return ASGITransport(app=mock_hrms_app)


@pytest.mark.asyncio
async def test_integration_get_leave_balance(mock_asgi_transport):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9002"
        ),
    ):
        res = await HRMSAdapter.get_leave_balance("EMP-1042")

        assert res["found"] is True
        assert res["employee_id"] == "EMP-1042"
        assert res["employee_name"] == "Jane Smith"
        assert res["total"] == 22
        assert res["casual"] == 4
        assert res["sick"] == 6
        assert res["earned"] == 12
        assert res["breakdown"] == {"casual": 4, "sick": 6, "earned": 12}


@pytest.mark.asyncio
async def test_integration_get_leave_balance_unknown_employee(mock_asgi_transport):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9002"
        ),
    ):
        res = await HRMSAdapter.get_leave_balance("EMP-9999")

        assert res["found"] is False
        assert res["employee_id"] == "EMP-9999"
        assert res["total"] == 0
        assert res["balance"] == 0
        assert res["status"] == "Not Found"
        assert "not found" in res["detail"].lower()


@pytest.mark.asyncio
async def test_integration_get_leave_status(mock_asgi_transport):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9002"
        ),
    ):
        res = await HRMSAdapter.get_leave_status("EMP-1001")

        assert res["found"] is True
        assert res["employee_id"] == "EMP-1001"
        assert len(res["applications"]) >= 1
        assert res["latest_status"] == "approved"
        assert res["latest_reference_id"] == "LEAVE-2031"


@pytest.mark.asyncio
async def test_integration_submit_leave_and_verify_balance_update(mock_asgi_transport):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9002"
        ),
    ):
        # 1. Check initial balance
        initial = await HRMSAdapter.get_leave_balance("EMP-1042")
        assert initial["breakdown"]["casual"] == 4
        assert initial["total"] == 22

        # 2. Submit leave for 2 days
        submit_res = await HRMSAdapter.submit_leave(
            employee_id="EMP-1042",
            type="casual",
            start="2026-11-10",
            end="2026-11-11",
            reason="Dentist appointment",
        )
        assert submit_res["success"] is True
        assert submit_res["reference_id"].startswith("LEAVE-")
        assert submit_res["days"] == 2

        # 3. Check updated balance
        updated = await HRMSAdapter.get_leave_balance("EMP-1042")
        assert updated["breakdown"]["casual"] == 2
        assert updated["total"] == 20

        # 4. Check status list contains newly created reference_id
        status_res = await HRMSAdapter.get_leave_status("EMP-1042")
        ref_ids = [app["reference_id"] for app in status_res["applications"]]
        assert submit_res["reference_id"] in ref_ids


@pytest.mark.asyncio
async def test_integration_get_policy(mock_asgi_transport):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9002"
        ),
    ):
        all_policies = await HRMSAdapter.get_policy()
        assert "policies" in all_policies
        assert len(all_policies["policies"]) >= 4

        leave_pol = await HRMSAdapter.get_policy("leave-policy")
        assert leave_pol["policy_id"] == "leave-policy"
        assert "Annual & Statutory" in leave_pol["title"]
