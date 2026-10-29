"""
Admissions Adapter for Rasa Admissions Action Server (slice-39).
Provides typed async access to the mock-admissions-service.
No dependencies on backend code (B2b fix).
"""
import os
import json
import logging
from urllib.parse import quote
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("rasa_admissions_adapter")


class AdmissionsServiceError(Exception):
    """Base exception for all Admissions adapter operations."""
    pass


class ApplicationNotFoundError(AdmissionsServiceError):
    """Raised when an application is not found in the Admissions system."""

    def __init__(self, application_id: str, message: str, suggested_next_step: str):
        super().__init__(message)
        self.application_id = application_id
        self.message = message
        self.suggested_next_step = suggested_next_step


class BackendUnavailableError(AdmissionsServiceError):
    """Raised when the Admissions backend/mock is unreachable, times out, or errors."""

    def __init__(
        self,
        message: str = "The admissions system is unavailable, please try again later.",
    ):
        super().__init__(message)
        self.message = message


class ProgramNotFoundError(AdmissionsServiceError):
    """Raised when a document checklist is queried for an unrecognized program."""

    def __init__(
        self, program: str, message: str, available_programs: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.program = program
        self.message = message
        self.available_programs = available_programs or []


class AdmissionsAdapter:
    """
    Adapter interfacing between Rasa Admissions and the Mock Admissions Service.
    Queries application status, document checklists, and admissions calendar.
    """

    DEFAULT_TIMEOUT: float = 5.0
    _transport: Optional[Any] = None

    @classmethod
    def _base_url(cls) -> str:
        if cls._transport is not None:
            return "http://mock-admissions"
        return os.getenv("MOCK_ADMISSIONS_URL", "http://localhost:9004").rstrip("/")

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._transport is not None:
            return httpx.AsyncClient(transport=cls._transport, timeout=cls.DEFAULT_TIMEOUT)
        return httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT)

    @classmethod
    async def get_application_status(
        cls, application_id: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves current admission status and next steps for a given application ID.
        """
        clean_id = (application_id or "").strip().upper()
        if not clean_id or any(char in clean_id for char in ["/", "\\", "?", "#", " "]):
            err_msg = f"Invalid application ID: '{application_id}'." if clean_id else "Application ID cannot be empty."
            suggested = "Please verify your application ID format (e.g. APP-1001) or contact admissions@org.example.com."
            if raise_for_not_found:
                raise ApplicationNotFoundError(
                    application_id=clean_id,
                    message=err_msg,
                    suggested_next_step=suggested,
                )
            return {
                "found": False,
                "application_id": clean_id,
                "status": "Not Found",
                "suggested_next_step": suggested,
                "detail": err_msg,
            }

        url = f"{cls._base_url()}/applications/{quote(clean_id, safe='')}"
        try:
            async with cls.get_client() as client:
                res = await client.get(url)

                if res.status_code == 200:
                    try:
                        data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "Admissions service returned a malformed response (non-JSON payload)."
                        )
                    return {
                        "found": True,
                        "application_id": data.get("application_id", clean_id),
                        "applicant_name": data.get("applicant_name"),
                        "program": data.get("program"),
                        "status": data.get("status"),
                        "next_step": data.get("next_step"),
                        "submission_date": data.get("submission_date"),
                        "fee_status": data.get("fee_status"),
                    }

                if res.status_code == 404:
                    try:
                        err_data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        err_data = {"detail": res.text or f"Application '{clean_id}' not found."}

                    detail = err_data.get("detail", {})
                    if isinstance(detail, dict):
                        msg = detail.get("message", f"Application '{clean_id}' not found.")
                        suggested_next_step = detail.get(
                            "suggested_next_step",
                            "Please verify your application ID or contact admissions@org.example.com.",
                        )
                    else:
                        msg = str(detail)
                        suggested_next_step = (
                            "Please verify your application ID or contact admissions@org.example.com."
                        )

                    if raise_for_not_found:
                        raise ApplicationNotFoundError(
                            application_id=clean_id,
                            message=msg,
                            suggested_next_step=suggested_next_step,
                        )

                    return {
                        "found": False,
                        "application_id": clean_id,
                        "status": "Not Found",
                        "suggested_next_step": suggested_next_step,
                        "detail": msg,
                    }

                raise BackendUnavailableError(
                    f"Admissions service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"The admissions system is unavailable, please try again later."
            )

    @classmethod
    async def get_document_checklist(
        cls, program: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves document checklist for a specific degree program.
        """
        clean_prog = (program or "").strip().lower()
        if not clean_prog:
            msg = "Program query cannot be empty."
            available = ["Computer Science (B.Tech)", "Data Science (M.Tech)", "MBA"]
            if raise_for_not_found:
                raise ProgramNotFoundError(
                    program="",
                    message=msg,
                    available_programs=available,
                )
            return {
                "found": False,
                "program": "",
                "available_programs": available,
                "detail": msg,
            }

        url = f"{cls._base_url()}/checklists/{quote(clean_prog, safe='')}"
        try:
            async with cls.get_client() as client:
                res = await client.get(url)

                if res.status_code == 200:
                    try:
                        data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "Admissions service returned a malformed response (non-JSON payload)."
                        )
                    return {
                        "found": True,
                        "program": data.get("program"),
                        "required_documents": data.get("required_documents", []),
                    }

                if res.status_code == 404:
                    try:
                        err_data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        err_data = {"detail": res.text or f"Program '{clean_prog}' not found."}

                    detail = err_data.get("detail", {})
                    if isinstance(detail, dict):
                        msg = detail.get("message", f"Program '{clean_prog}' not found.")
                        available = detail.get("available_programs", [])
                    else:
                        msg = str(detail)
                        available = []

                    if raise_for_not_found:
                        raise ProgramNotFoundError(
                            program=clean_prog,
                            message=msg,
                            available_programs=available,
                        )

                    return {
                        "found": False,
                        "program": clean_prog,
                        "available_programs": available,
                        "detail": msg,
                    }

                raise BackendUnavailableError(
                    f"Admissions service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"The admissions system is unavailable, please try again later."
            )

    @classmethod
    async def get_calendar(cls) -> Dict[str, Any]:
        """
        Retrieves the central admissions calendar with fees and deadlines (single source of truth for FR-16).
        """
        url = f"{cls._base_url()}/calendar"
        try:
            async with cls.get_client() as client:
                res = await client.get(url)
                if res.status_code == 200:
                    try:
                        return res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "Admissions service returned a malformed response (non-JSON payload)."
                        )

                raise BackendUnavailableError(
                    f"Admissions service returned unexpected HTTP status {res.status_code}."
                )
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"The admissions system is unavailable, please try again later."
            )
