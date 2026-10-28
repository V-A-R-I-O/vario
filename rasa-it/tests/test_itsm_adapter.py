from unittest.mock import AsyncMock, patch

import httpx
import pytest

from actions.itsm_adapter import BackendUnavailableError, ITSMAdapter


@pytest.mark.asyncio
async def test_get_ticket_status_returns_card_fields():
    payload = {
        "ticket_id": "IT-1001",
        "category": "hardware",
        "description": "Laptop battery drains quickly",
        "reporter": "EMP-1042",
        "status": "In Progress",
        "updated_at": "2026-10-21T12:30:00Z",
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=payload)
        result = await ITSMAdapter.get_ticket_status("it-1001")
    assert result["found"] is True
    assert result["ticket_id"] == "IT-1001"
    assert result["status"] == "In Progress"
    assert result["category"] == "hardware"


@pytest.mark.asyncio
async def test_unknown_ticket_is_a_not_found_result():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(404, json={"detail": "not found"})
        result = await ITSMAdapter.get_ticket_status("TKT-9999")
    assert result == {"found": False, "ticket_id": "TKT-9999", "status": "Not Found"}


@pytest.mark.asyncio
async def test_backend_unavailable_and_timeout_raise_typed_error():
    assert ITSMAdapter.DEFAULT_TIMEOUT <= 3
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.get_ticket_status("IT-1001")
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("slow")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.get_ticket_status("IT-1001")


@pytest.mark.asyncio
async def test_malformed_or_incomplete_response_is_rejected():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, text="<html>bad gateway</html>")
        with pytest.raises(BackendUnavailableError, match="malformed"):
            await ITSMAdapter.get_ticket_status("IT-1001")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"ticket_id": "IT-1001"})
        with pytest.raises(BackendUnavailableError, match="incomplete"):
            await ITSMAdapter.get_ticket_status("IT-1001")
