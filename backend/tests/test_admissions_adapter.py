import pytest
import httpx
from unittest.mock import patch, AsyncMock

from app.services.admissions_adapter import (
    AdmissionsAdapter,
    ApplicationNotFoundError,
    BackendUnavailableError,
    ProgramNotFoundError,
)


@pytest.mark.asyncio
async def test_get_application_status_success():
    mock_payload = {
        "application_id": "APP-1001",
        "applicant_name": "Aarav Sharma",
        "program": "Computer Science (B.Tech)",
        "status": "Under Review",
        "next_step": "Committee review in progress until Oct 25.",
        "submission_date": "2026-09-10",
        "fee_status": "Paid",
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await AdmissionsAdapter.get_application_status("APP-1001")

        assert result["found"] is True
        assert result["application_id"] == "APP-1001"
        assert result["status"] == "Under Review"
        assert result["next_step"] == "Committee review in progress until Oct 25."
        assert result["applicant_name"] == "Aarav Sharma"


@pytest.mark.asyncio
async def test_get_application_status_not_found_result():
    # AC 3: Given an unknown application_id, adapter returns not-found result carrying suggested next step (FR-17)
    mock_err_body = {
        "detail": {
            "message": "Application 'APP-9999' not found.",
            "application_id": "APP-9999",
            "suggested_next_step": "Please verify your ID or contact admissions@org.example.com",
        }
    }
    mock_response = httpx.Response(404, json=mock_err_body)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await AdmissionsAdapter.get_application_status("APP-9999")

        assert result["found"] is False
        assert result["application_id"] == "APP-9999"
        assert result["status"] == "Not Found"
        assert "suggested_next_step" in result
        assert "admissions@org.example.com" in result["suggested_next_step"]


@pytest.mark.asyncio
async def test_get_application_status_not_found_raises_exception():
    mock_err_body = {
        "detail": {
            "message": "Application 'APP-9999' not found.",
            "application_id": "APP-9999",
            "suggested_next_step": "Please contact admissions office.",
        }
    }
    mock_response = httpx.Response(404, json=mock_err_body)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(ApplicationNotFoundError) as exc_info:
            await AdmissionsAdapter.get_application_status("APP-9999", raise_for_not_found=True)

        assert exc_info.value.application_id == "APP-9999"
        assert "admissions office" in exc_info.value.suggested_next_step


@pytest.mark.asyncio
async def test_get_application_status_mock_down_raises_backend_unavailable():
    # AC 4: Given the mock is down, adapter raises typed "backend unavailable" error
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Failed to establish connection"),
    ):
        with pytest.raises(BackendUnavailableError) as exc_info:
            await AdmissionsAdapter.get_application_status("APP-1001")

        assert "unavailable" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_application_status_timeout_raises_backend_unavailable():
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.TimeoutException("Request timed out"),
    ):
        with pytest.raises(BackendUnavailableError) as exc_info:
            await AdmissionsAdapter.get_application_status("APP-1001")

        assert "unavailable" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_application_status_500_status():
    mock_response = httpx.Response(500, text="Internal Server Error")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(BackendUnavailableError):
            await AdmissionsAdapter.get_application_status("APP-1001")


@pytest.mark.asyncio
async def test_get_document_checklist_success():
    # AC 5: get_document_checklist is implemented and callable
    mock_payload = {
        "program": "Computer Science (B.Tech)",
        "required_documents": [
            "Class 10 Marksheet",
            "Class 12 Marksheet",
            "JEE Scorecard",
        ],
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        res = await AdmissionsAdapter.get_document_checklist("btech")

        assert res["found"] is True
        assert res["program"] == "Computer Science (B.Tech)"
        assert len(res["required_documents"]) == 3


@pytest.mark.asyncio
async def test_get_document_checklist_not_found():
    mock_payload = {
        "detail": {
            "message": "Program 'unknown' not found.",
            "available_programs": ["Computer Science (B.Tech)", "MBA"],
        }
    }
    mock_response = httpx.Response(404, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        res = await AdmissionsAdapter.get_document_checklist("unknown")

        assert res["found"] is False
        assert "available_programs" in res
        assert len(res["available_programs"]) == 2


@pytest.mark.asyncio
async def test_get_document_checklist_not_found_raises_exception():
    mock_payload = {
        "detail": {
            "message": "Program 'unknown' not found.",
            "available_programs": ["MBA"],
        }
    }
    mock_response = httpx.Response(404, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(ProgramNotFoundError):
            await AdmissionsAdapter.get_document_checklist("unknown", raise_for_not_found=True)


@pytest.mark.asyncio
async def test_get_calendar_success():
    # AC 5: get_calendar is implemented and callable
    mock_payload = {
        "academic_year": "2026-2027",
        "deadlines": [{"milestone": "Deadline", "date": "Nov 30"}],
        "fees": [{"item": "Tuition", "amount": "₹3,20,000"}],
        "refund_policy": "Full refund before start.",
    }
    mock_response = httpx.Response(200, json=mock_payload)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        res = await AdmissionsAdapter.get_calendar()

        assert res["academic_year"] == "2026-2027"
        assert len(res["deadlines"]) == 1
        assert len(res["fees"]) == 1


@pytest.mark.asyncio
async def test_get_calendar_backend_unavailable():
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Service unreachable"),
    ):
        with pytest.raises(BackendUnavailableError):
            await AdmissionsAdapter.get_calendar()
