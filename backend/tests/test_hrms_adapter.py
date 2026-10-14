import pytest
import httpx
from unittest.mock import patch, AsyncMock

from app.services.hrms_adapter import (
    HRMSAdapter,
    HRMSServiceError,
    BackendUnavailableError,
    EmployeeNotFoundError,
    LeaveApplicationError,
)


@pytest.mark.asyncio
async def test_get_leave_balance_success():
    # AC 2: Given a seeded employee_id, returns structured balance (total + per-type breakdown)
    mock_payload = {
        "employee_id": "EMP-1042",
        "employee_name": "Jane Smith",
        "department": "Product Marketing",
        "total": 22,
        "breakdown": {
            "casual": 4,
            "sick": 6,
            "earned": 12,
        },
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await HRMSAdapter.get_leave_balance("EMP-1042")

        assert result["found"] is True
        assert result["employee_id"] == "EMP-1042"
        assert result["employee_name"] == "Jane Smith"
        assert result["total"] == 22
        assert result["balance"] == 22
        assert result["casual"] == 4
        assert result["sick"] == 6
        assert result["earned"] == 12
        assert result["breakdown"] == {"casual": 4, "sick": 6, "earned": 12}


@pytest.mark.asyncio
async def test_get_leave_balance_unknown_employee_returns_not_found_dict():
    # AC 3: Given an unknown employee_id, adapter returns not-found result (not an exception crashing caller)
    mock_err_body = {
        "detail": {
            "message": "Employee 'EMP-9999' not found.",
            "employee_id": "EMP-9999",
        }
    }
    mock_response = httpx.Response(404, json=mock_err_body)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await HRMSAdapter.get_leave_balance("EMP-9999")

        assert result["found"] is False
        assert result["employee_id"] == "EMP-9999"
        assert result["total"] == 0
        assert result["balance"] == 0
        assert result["status"] == "Not Found"
        assert "not found" in result["detail"].lower()


@pytest.mark.asyncio
async def test_get_leave_balance_unknown_employee_raises_when_requested():
    mock_err_body = {
        "detail": {
            "message": "Employee 'EMP-9999' not found.",
            "employee_id": "EMP-9999",
        }
    }
    mock_response = httpx.Response(404, json=mock_err_body)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(EmployeeNotFoundError) as exc_info:
            await HRMSAdapter.get_leave_balance("EMP-9999", raise_for_not_found=True)

        assert exc_info.value.employee_id == "EMP-9999"
        assert "not found" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_leave_balance_mock_down_raises_backend_unavailable():
    # AC 4: Given mock service is down, adapter raises typed "backend unavailable" error
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Failed to establish connection"),
    ):
        with pytest.raises(BackendUnavailableError) as exc_info:
            await HRMSAdapter.get_leave_balance("EMP-1042")

        assert "unavailable" in exc_info.value.message.lower()
        assert issubclass(BackendUnavailableError, HRMSServiceError)


@pytest.mark.asyncio
async def test_get_leave_balance_timeout_raises_backend_unavailable():
    # AC 4: Prompt return on timeout
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.TimeoutException("Request timed out"),
    ):
        with pytest.raises(BackendUnavailableError) as exc_info:
            await HRMSAdapter.get_leave_balance("EMP-1042")

        assert "unavailable" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_leave_balance_500_raises_backend_unavailable():
    mock_response = httpx.Response(500, text="Internal Server Error")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(BackendUnavailableError) as exc_info:
            await HRMSAdapter.get_leave_balance("EMP-1042")

        assert "internal error" in exc_info.value.message.lower() or "500" in exc_info.value.message


@pytest.mark.asyncio
async def test_get_leave_balance_malformed_non_json_200():
    mock_response = httpx.Response(200, text="<html><body>Gateway Error</body></html>")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(BackendUnavailableError) as exc_info:
            await HRMSAdapter.get_leave_balance("EMP-1042")

        assert "malformed" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_leave_balance_empty_id():
    result = await HRMSAdapter.get_leave_balance("   ")
    assert result["found"] is False
    assert result["total"] == 0
    assert "empty" in result["detail"].lower()

    with pytest.raises(EmployeeNotFoundError):
        await HRMSAdapter.get_leave_balance("", raise_for_not_found=True)


@pytest.mark.asyncio
async def test_get_leave_status_success():
    mock_payload = {
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "applications": [
            {
                "reference_id": "LEAVE-2031",
                "leave_type": "casual",
                "start_date": "2026-09-10",
                "end_date": "2026-09-11",
                "days": 2,
                "status": "approved",
                "reason": "Personal appointment",
                "submitted_at": "2026-09-07T10:05:00Z",
            }
        ],
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await HRMSAdapter.get_leave_status("EMP-1001")

        assert result["found"] is True
        assert result["employee_id"] == "EMP-1001"
        assert len(result["applications"]) == 1
        assert result["latest_status"] == "approved"
        assert result["latest_reference_id"] == "LEAVE-2031"


@pytest.mark.asyncio
async def test_get_leave_status_unknown_employee():
    mock_err = {"detail": {"message": "Employee 'EMP-9999' not found."}}
    mock_response = httpx.Response(404, json=mock_err)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await HRMSAdapter.get_leave_status("EMP-9999")

        assert result["found"] is False
        assert result["applications"] == []
        assert result["latest_status"] is None


@pytest.mark.asyncio
async def test_get_leave_status_mock_down():
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        with pytest.raises(BackendUnavailableError):
            await HRMSAdapter.get_leave_status("EMP-1001")


@pytest.mark.asyncio
async def test_submit_leave_success():
    # AC & Deliverable: submit_leave(employee_id, type, start, end, reason) returns reference ID
    mock_payload = {
        "success": True,
        "reference_id": "LEAVE-2032",
        "employee_id": "EMP-1042",
        "leave_type": "casual",
        "start_date": "2026-11-01",
        "end_date": "2026-11-03",
        "days": 3,
        "status": "submitted",
        "remaining_balance": {
            "total": 19,
            "breakdown": {"casual": 1, "sick": 6, "earned": 12},
        },
        "message": "Leave application submitted successfully.",
    }
    mock_response = httpx.Response(201, json=mock_payload)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await HRMSAdapter.submit_leave(
            employee_id="EMP-1042",
            type="casual",
            start="2026-11-01",
            end="2026-11-03",
            reason="Vacation",
        )

        assert result["success"] is True
        assert result["reference_id"] == "LEAVE-2032"
        assert result["days"] == 3
        assert result["status"] == "submitted"


@pytest.mark.asyncio
async def test_submit_leave_unknown_employee():
    mock_err = {"detail": {"message": "Employee 'EMP-9999' not found."}}
    mock_response = httpx.Response(404, json=mock_err)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await HRMSAdapter.submit_leave(
            employee_id="EMP-9999",
            type="casual",
            start="2026-11-01",
            end="2026-11-02",
        )

        assert result["success"] is False
        assert result["found"] is False
        assert "not found" in result["detail"].lower()


@pytest.mark.asyncio
async def test_submit_leave_validation_error_raises_leave_application_error():
    mock_err = {"detail": "Invalid leave type 'foo'."}
    mock_response = httpx.Response(400, json=mock_err)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(LeaveApplicationError) as exc_info:
            await HRMSAdapter.submit_leave(
                employee_id="EMP-1042",
                type="foo",
                start="2026-11-01",
                end="2026-11-02",
            )

        assert "Invalid leave application" in exc_info.value.message


@pytest.mark.asyncio
async def test_submit_leave_mock_down():
    with patch(
        "httpx.AsyncClient.post",
        side_effect=httpx.ConnectError("Service down"),
    ):
        with pytest.raises(BackendUnavailableError):
            await HRMSAdapter.submit_leave(
                employee_id="EMP-1042",
                type="casual",
                start="2026-11-01",
                end="2026-11-02",
            )


@pytest.mark.asyncio
async def test_get_policy_success():
    mock_payload = {
        "policy_id": "leave-policy",
        "title": "Annual & Statutory Leave Policy",
        "details": "Details here",
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await HRMSAdapter.get_policy("leave-policy")

        assert result["policy_id"] == "leave-policy"
        assert result["title"] == "Annual & Statutory Leave Policy"
