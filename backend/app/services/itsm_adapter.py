"""Adapter between VARIO and the mockable ITSM backend."""
import json
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.config import settings


class ITSMServiceError(Exception):
    """Base exception for ITSM adapter operations."""


class BackendUnavailableError(ITSMServiceError):
    """Raised when ITSM cannot be reached or returns an invalid response."""

    def __init__(self, message: str = "ITSM service is currently unavailable. Please try again shortly."):
        super().__init__(message)
        self.message = message


class TicketNotFoundError(ITSMServiceError):
    """Raised when a ticket is missing and strict lookup was requested."""

    def __init__(self, ticket_id: str, message: Optional[str] = None):
        self.ticket_id = ticket_id
        self.message = message or f"Ticket '{ticket_id}' was not found."
        super().__init__(self.message)


class TicketCreationError(ITSMServiceError):
    """Raised when ticket creation is rejected or its input is invalid."""

    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class IdentityVerificationError(ITSMServiceError):
    """Raised when a password reset is attempted before identity verification."""

    def __init__(self, message: str = "Identity verification is required before a password reset."):
        self.message = message
        super().__init__(message)


class ITSMAdapter:
    """Stable ITSM seam; only this class knows the configured backend URL."""

    DEFAULT_TIMEOUT: float = 2.5

    @classmethod
    def _base_url(cls) -> str:
        return getattr(settings, "MOCK_ITSM_URL", "http://localhost:9003").rstrip("/")

    @classmethod
    async def get_ticket_status(
        cls, ticket_id: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """Return ticket-card fields, or a structured not-found result."""
        clean_id = (ticket_id or "").strip().upper()
        if not clean_id or any(char in clean_id for char in ("/", "\\", "?", "#", " ")):
            message = "Ticket ID cannot be empty." if not clean_id else f"Invalid ticket ID: '{ticket_id}'."
            if raise_for_not_found:
                raise TicketNotFoundError(clean_id, message)
            return {"found": False, "ticket_id": clean_id, "status": "Not Found", "detail": message}

        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{cls._base_url()}/tickets/{quote(clean_id, safe='')}")
            if response.status_code == 404:
                message = cls._error_message(response, f"Ticket '{clean_id}' was not found.")
                if raise_for_not_found:
                    raise TicketNotFoundError(clean_id, message)
                return {"found": False, "ticket_id": clean_id, "status": "Not Found", "detail": message}
            if response.status_code != 200:
                raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
            data = cls._json(response)
            return {
                "found": True,
                "ticket_id": data.get("ticket_id", clean_id),
                "category": data.get("category"),
                "description": data.get("description"),
                "reporter": data.get("reporter"),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc

    @classmethod
    async def create_ticket(
        cls, category: str, description: str, reporter: str
    ) -> Dict[str, Any]:
        """Create a mock support ticket and return its generated ticket ID."""
        clean_category = (category or "").strip()
        clean_description = (description or "").strip()
        clean_reporter = (reporter or "").strip().upper()
        if not clean_category or not clean_description or not clean_reporter:
            raise TicketCreationError("category, description, and reporter are required.")

        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{cls._base_url()}/tickets",
                    json={
                        "category": clean_category,
                        "description": clean_description,
                        "reporter": clean_reporter,
                    },
                )
            if response.status_code in (400, 404, 422):
                raise TicketCreationError(
                    f"ITSM rejected ticket creation: {cls._error_message(response, 'Invalid ticket details.')}"
                )
            if response.status_code not in (200, 201):
                raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
            data = cls._json(response)
            if not data.get("ticket_id"):
                raise BackendUnavailableError("ITSM service returned a malformed ticket response (ticket_id missing).")
            return data
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc

    @classmethod
    async def verify_identity(cls, employee_id: str, answer: str) -> Dict[str, Any]:
        """Verify an employee's security answer without returning the stored answer."""
        clean_id = (employee_id or "").strip().upper()
        clean_answer = (answer or "").strip()
        if not clean_id or not clean_answer:
            return {"verified": False, "employee_id": clean_id, "detail": "Employee ID and answer are required."}
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{cls._base_url()}/identity/verify",
                    json={"employee_id": clean_id, "answer": clean_answer},
                )
            if response.status_code == 404:
                return {"verified": False, "employee_id": clean_id, "detail": "Employee was not found."}
            if response.status_code != 200:
                raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
            data = cls._json(response)
            return {
                "verified": bool(data.get("verified", False)),
                "employee_id": data.get("employee_id", clean_id),
                "detail": data.get("detail", ""),
            }
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc

    @classmethod
    async def reset_password(cls, employee_id: str) -> Dict[str, Any]:
        """Request a mock password reset; the mock enforces prior identity verification."""
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            raise IdentityVerificationError("Employee ID is required for password reset.")
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{cls._base_url()}/password/reset",
                    json={"employee_id": clean_id},
                )
            if response.status_code == 403:
                raise IdentityVerificationError(cls._error_message(response, "Identity verification is required."))
            if response.status_code == 404:
                return {"success": False, "found": False, "employee_id": clean_id, "detail": "Employee was not found."}
            if response.status_code != 200:
                raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
            return cls._json(response)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc

    @staticmethod
    def _json(response: httpx.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise BackendUnavailableError("ITSM service returned a malformed response (non-JSON payload).") from exc
        if not isinstance(data, dict):
            raise BackendUnavailableError("ITSM service returned a malformed response (expected a JSON object).")
        return data

    @staticmethod
    def _error_message(response: httpx.Response, fallback: str) -> str:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError):
            return response.text or fallback
        detail = data.get("detail", fallback)
        if isinstance(detail, dict):
            return str(detail.get("message", fallback))
        return str(detail)
