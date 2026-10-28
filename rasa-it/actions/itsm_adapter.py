"""Small ITSM HTTP client for the separately deployed IT role-pack container.

The backend owns the canonical adapter; this thin client keeps the Rasa runtime
behind the same mockable HTTP contract without importing backend application code.
"""
import os
from typing import Any, Dict
from urllib.parse import quote

import httpx


class BackendUnavailableError(Exception):
    """The ITSM endpoint is unreachable or returned an invalid response."""


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
                response = await client.get(
                    f"{cls.base_url()}/tickets/{quote(clean_id, safe='')}"
                )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise BackendUnavailableError(
                "ITSM service is currently unavailable. Please try again shortly."
            ) from exc

        if response.status_code == 404:
            return {"found": False, "ticket_id": clean_id, "status": "Not Found"}
        if response.status_code != 200:
            raise BackendUnavailableError(
                f"ITSM service returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise BackendUnavailableError("ITSM service returned a malformed response.") from exc
        if not isinstance(data, dict) or not data.get("ticket_id") or not data.get("status"):
            raise BackendUnavailableError("ITSM service returned an incomplete ticket response.")

        return {
            "found": True,
            "ticket_id": data.get("ticket_id", clean_id),
            "category": data.get("category"),
            "description": data.get("description"),
            "reporter": data.get("reporter"),
            "status": data.get("status"),
            "updated_at": data.get("updated_at"),
        }
