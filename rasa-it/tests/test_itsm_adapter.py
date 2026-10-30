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
        result = await ITSMAdapter.get_ticket_status("IT-9999")
    assert result == {"found": False, "ticket_id": "IT-9999", "status": "Not Found"}


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


@pytest.mark.asyncio
async def test_create_ticket_posts_validated_payload_and_returns_ticket():
    ticket = {"ticket_id": "IT-1004", "status": "Open", "reporter": "EMP-1042"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(201, json=ticket)
        result = await ITSMAdapter.create_ticket("network", "VPN unavailable", "emp-1042")
    assert result["ticket_id"] == "IT-1004"
    assert mock_post.await_args.kwargs["json"] == {"category": "network", "description": "VPN unavailable", "reporter": "EMP-1042"}


@pytest.mark.asyncio
async def test_create_ticket_handles_rejection_and_service_outage():
    from actions.itsm_adapter import TicketCreationRejectedError
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(404, json={"detail": {"message": "Employee not found"}})
        with pytest.raises(TicketCreationRejectedError, match="Employee not found"):
            await ITSMAdapter.create_ticket("network", "VPN unavailable", "EMP-9999")
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(BackendUnavailableError):
            await ITSMAdapter.create_ticket("network", "VPN unavailable", "EMP-1042")


@pytest.mark.asyncio
async def test_security_question_response_never_contains_answer():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"found": True, "employee_id": "EMP-1042", "security_question": "What city were you born in?"})
        result = await ITSMAdapter.get_security_question("emp-1042")
    assert result["security_question"] == "What city were you born in?"
    assert "security_answer" not in result
    assert "mysuru" not in str(result).casefold()


@pytest.mark.asyncio
async def test_verify_identity_and_reset_use_mock_contract():
    verified = {"verified": True, "employee_id": "EMP-1042", "detail": "Identity verified."}
    reset = {"success": True, "employee_id": "EMP-1042", "reset_requested": True, "message": "Mock password reset initiated."}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [httpx.Response(200, json=verified), httpx.Response(200, json=reset)]
        result = await ITSMAdapter.verify_identity("emp-1042", "Mysuru")
        reset_result = await ITSMAdapter.reset_password("emp-1042")
    assert result["verified"] is True
    assert reset_result["reset_requested"] is True
    assert mock_post.await_args_list[0].kwargs["json"] == {"employee_id": "EMP-1042", "answer": "Mysuru"}
    assert mock_post.await_args_list[1].kwargs["json"] == {"employee_id": "EMP-1042"}


@pytest.mark.asyncio
async def test_reset_adapter_rejects_unverified_identity():
    from actions.itsm_adapter import IdentityVerificationError
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(403, json={"detail": "Identity verification is required."})
        with pytest.raises(IdentityVerificationError):
            await ITSMAdapter.reset_password("EMP-1042")


@pytest.mark.asyncio
async def test_create_ticket_rejects_null_inputs_without_http_call():
    from actions.itsm_adapter import TicketCreationRejectedError

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        with pytest.raises(TicketCreationRejectedError, match="required"):
            await ITSMAdapter.create_ticket(None, "description", "EMP-1042")
    mock_post.assert_not_awaited()
