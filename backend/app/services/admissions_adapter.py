import json
import httpx
from urllib.parse import quote
from typing import Optional, Dict, Any, List
from app.config import settings


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
        message: str = "Admissions service is currently unavailable. Please try again shortly.",
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
    Adapter interfacing between VARIO and the Admissions internal system (Mock Admissions Service).
    Provides application status checks, program document checklists, and admissions calendar queries.
    """

    DEFAULT_TIMEOUT: float = 5.0

    @classmethod
    def _base_url(cls) -> str:
        return settings.MOCK_ADMISSIONS_URL.rstrip("/")

    @classmethod
    async def get_application_status(
        cls, application_id: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves the current admission status and next steps for a given application ID.

        Args:
            application_id: The application reference identifier (e.g. 'APP-1001').
            raise_for_not_found: If True, raises ApplicationNotFoundError instead of returning not-found dict.

        Returns:
            Dict containing application details.

        Raises:
            ApplicationNotFoundError: If raise_for_not_found is True and ID is not found.
            BackendUnavailableError: If mock service is down, unreachable, times out, or returns malformed response.
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
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
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
                f"Admissions service is currently unavailable: {str(e)}"
            )

    @classmethod
    async def get_document_checklist(
        cls, program: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves the mandatory document checklist for a specific degree program.

        Args:
            program: Degree program name or alias (e.g. 'btech', 'mtech', 'mba').
            raise_for_not_found: If True, raises ProgramNotFoundError if program is not found.

        Returns:
            Dict containing checklist details.

        Raises:
            ProgramNotFoundError: If raise_for_not_found is True and program is unknown or empty.
            BackendUnavailableError: If mock service is down, times out, or returns malformed response.
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
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
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
                f"Admissions service is currently unavailable: {str(e)}"
            )

    @classmethod
    async def get_calendar(cls) -> Dict[str, Any]:
        """
        Retrieves the central admissions calendar with fees and deadlines (single source of truth for FR-16).

        Returns:
            Dict containing academic_year, deadlines, fees, refund_policy, and contact information.

        Raises:
            BackendUnavailableError: If mock service is down, times out, or returns malformed response.
        """
        url = f"{cls._base_url()}/calendar"
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
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
                f"Admissions service is currently unavailable: {str(e)}"
            )
