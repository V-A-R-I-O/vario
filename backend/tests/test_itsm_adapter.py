import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.services.itsm_adapter import (
    ITSMAdapter,
    ITSMServiceError,
    BackendUnavailableError,
    TicketNotFoundError,
    TicketCreationError,
    IdentityVerificationError,
)


@pytest.mark.asyncio
async def test_get_ticket_status_success():
    payload = {"ticket_id": "IT-1001", "category": "hardware", "description": "Laptop battery drains quickly", "reporter": "EMP-1042", "status": "In Progress", "created_at": "2026-10-20T09:15:00Z", "updated_at": "2026-10-21T12:30:00Z"}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=payload)
        result = await ITSMAdapter.get_ticket_status("it-1001")
    assert result["found"] is True
    assert result["ticket_id"] == "IT-1001"
    assert result["status"] == "In Progress"
    assert result["category"] == "hardware"


@pytest.mark.asyncio
async def test_unknown_ticket_returns_not_found_and_optional_typed_error():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(404, json={"detail": {"message": "Ticket missing"}})
        result = await ITSMAdapter.get_ticket_status("IT-9999")
    assert result["found"] is False
    assert result["status"] == "Not Found"
    assert "missing" in result["detail"].lower()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(404, json={"detail": "Ticket missing"})
        with pytest.raises(TicketNotFoundError):
            await ITSMAdapter.get_ticket_status("IT-9999", raise_for_not_found=True)


@pytest.mark.asyncio
async def test_backend_down_and_timeout_are_typed_and_bounded():
    assert ITSMAdapter.DEFAULT_TIMEOUT <= 3
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(BackendUnavailableError) as exc:
            await ITSMAdapter.get_ticket_status("IT-1001")
    assert "unavailable" in exc.value.message.lower()
    assert isinstance(exc.value, ITSMServiceError)
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("slow")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.get_ticket_status("IT-1001")


@pytest.mark.asyncio
async def test_malformed_success_response_is_typed_error():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, text="<html>bad gateway</html>")
        with pytest.raises(BackendUnavailableError, match="malformed"):
            await ITSMAdapter.get_ticket_status("IT-1001")


@pytest.mark.asyncio
async def test_create_ticket_posts_contract_and_returns_id():
    payload = {"ticket_id": "IT-1004", "status": "Open", "category": "software"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(201, json=payload)
        result = await ITSMAdapter.create_ticket("software", "Install editor", "emp-1042")
    assert result["ticket_id"] == "IT-1004"
    assert mock_post.await_args.kwargs["json"]["reporter"] == "EMP-1042"


@pytest.mark.asyncio
async def test_create_ticket_validates_required_fields():
    with pytest.raises(TicketCreationError):
        await ITSMAdapter.create_ticket("", "description", "EMP-1042")


@pytest.mark.asyncio
async def test_verify_identity_success_and_unknown_employee():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(200, json={"verified": True, "employee_id": "EMP-1042"})
        result = await ITSMAdapter.verify_identity("emp-1042", "answer")
    assert result["verified"] is True
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(404, json={"detail": "not found"})
        result = await ITSMAdapter.verify_identity("EMP-9999", "answer")
    assert result["verified"] is False


@pytest.mark.asyncio
async def test_reset_password_requires_prior_verification():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(403, json={"detail": "verify first"})
        with pytest.raises(IdentityVerificationError):
            await ITSMAdapter.reset_password("EMP-1042")


@pytest.mark.asyncio
async def test_reset_password_unknown_employee_returns_not_found():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(404, json={"detail": "not found"})
        result = await ITSMAdapter.reset_password("EMP-9999")
    assert result["found"] is False


@pytest.mark.asyncio
async def test_create_and_identity_backend_errors_are_typed():
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.create_ticket("hardware", "Broken laptop", "EMP-1042")
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.verify_identity("EMP-1042", "answer")
