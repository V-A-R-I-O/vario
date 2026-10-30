"""Small ITSM HTTP client for the separately deployed IT role-pack container."""
import os
from typing import Any, Dict
from urllib.parse import quote

import httpx


class BackendUnavailableError(Exception):
    """The ITSM endpoint is unreachable or returned an invalid response."""


class TicketCreationRejectedError(Exception):
    """The ITSM service rejected ticket creation because the submitted details are invalid."""


class IdentityVerificationError(Exception):
    """The mock ITSM service rejected a reset because identity was not verified."""


class ITSMAdapter:
    DEFAULT_TIMEOUT = 2.5

    @classmethod
    def base_url(cls) -> str:
        return os.getenv("MOCK_ITSM_URL", "http://localhost:9003").rstrip("/")

    @classmethod
    async def get_ticket_status(cls, ticket_id: str) -> Dict[str, Any]:
        clean_id = (ticket_id or "").strip().upper()
        if not clean_id:
            return {"found": False, "ticket_id": clean_id, "status": "Not Found"}
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{cls.base_url()}/tickets/{quote(clean_id, safe='')}")
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc
        if response.status_code == 404:
            return {"found": False, "ticket_id": clean_id, "status": "Not Found"}
        if response.status_code != 200:
            raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed response.") from exc
        if not isinstance(data, dict) or not data.get("ticket_id") or not data.get("status"):
            raise BackendUnavailableError("ITSM service returned an incomplete ticket response.")
        return {key: data.get(key) for key in
                ("found", "ticket_id", "category", "description", "reporter", "status", "updated_at")} | {"found": True}

    @classmethod
    async def create_ticket(cls, category: str, description: str, reporter: str) -> Dict[str, Any]:
        clean_category = (category or "").strip()
        clean_description = (description or "").strip()
        clean_reporter = (reporter or "").strip().upper()
        if not clean_category or not clean_description or not clean_reporter:
            raise TicketCreationRejectedError("Category, description, and reporter are required.")
        if len(clean_category) > 80 or len(clean_description) > 2000 or len(clean_reporter) > 80:
            raise TicketCreationRejectedError("Ticket details exceed the supported length.")
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(f"{cls.base_url()}/tickets",
                    json={"category": clean_category, "description": clean_description, "reporter": clean_reporter})
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc
        if response.status_code in (400, 404, 422):
            try:
                detail = response.json().get("detail", "Ticket details were rejected.")
                if isinstance(detail, dict):
                    detail = detail.get("message", "Ticket details were rejected.")
            except ValueError:
                detail = "Ticket details were rejected."
            raise TicketCreationRejectedError(str(detail))
        if response.status_code not in (200, 201):
            raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
        try:
            ticket = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed ticket response.") from exc
        if not isinstance(ticket, dict) or not ticket.get("ticket_id"):
            raise BackendUnavailableError("ITSM service returned an incomplete ticket response.")
        return ticket

    @classmethod
    async def get_security_question(cls, employee_id: str) -> Dict[str, Any]:
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            return {"found": False, "employee_id": "", "detail": "Employee ID is required."}
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{cls.base_url()}/identity/{quote(clean_id, safe='')}/question")
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc
        if response.status_code == 404:
            return {"found": False, "employee_id": clean_id, "detail": "Employee was not found."}
        if response.status_code != 200:
            raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed identity response.") from exc
        if not isinstance(payload, dict) or not payload.get("security_question"):
            raise BackendUnavailableError("ITSM service returned an incomplete identity response.")
        return {"found": True, "employee_id": str(payload.get("employee_id") or clean_id).upper(),
                "security_question": str(payload["security_question"]), "locked": bool(payload.get("locked")),
                "attempts_remaining": int(payload.get("attempts_remaining", 3))}

    @classmethod
    async def verify_identity(cls, employee_id: str, answer: str) -> Dict[str, Any]:
        clean_id, clean_answer = (employee_id or "").strip().upper(), (answer or "").strip()
        if not clean_id or not clean_answer:
            return {"verified": False, "employee_id": clean_id, "detail": "Employee ID and answer are required.",
                    "locked": False, "attempts_remaining": 3}
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(f"{cls.base_url()}/identity/verify",
                                             json={"employee_id": clean_id, "answer": clean_answer})
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc
        if response.status_code == 404:
            return {"verified": False, "employee_id": clean_id, "detail": "Employee was not found.",
                    "locked": False, "attempts_remaining": 3}
        if response.status_code != 200:
            raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed verification response.") from exc
        if not isinstance(payload, dict):
            raise BackendUnavailableError("ITSM service returned a malformed verification response.")
        return {"verified": bool(payload.get("verified")), "employee_id": str(payload.get("employee_id") or clean_id).upper(),
                "detail": str(payload.get("detail") or ""), "locked": bool(payload.get("locked")),
                "attempts_remaining": int(payload.get("attempts_remaining", 3))}

    @classmethod
    async def reset_password(cls, employee_id: str) -> Dict[str, Any]:
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            raise IdentityVerificationError("Employee ID is required for password reset.")
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                response = await client.post(f"{cls.base_url()}/password/reset", json={"employee_id": clean_id})
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError("ITSM service is currently unavailable. Please try again shortly.") from exc
        if response.status_code == 403:
            raise IdentityVerificationError("Identity verification is required before a password reset.")
        if response.status_code == 404:
            return {"success": False, "found": False, "employee_id": clean_id, "detail": "Employee was not found."}
        if response.status_code != 200:
            raise BackendUnavailableError(f"ITSM service returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed reset response.") from exc
        if not isinstance(payload, dict) or payload.get("success") is not True or payload.get("reset_requested") is not True:
            raise BackendUnavailableError("ITSM service did not confirm the mock password-reset request.")
        return payload
