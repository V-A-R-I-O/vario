import os
import json
import httpx
from urllib.parse import quote
from typing import Optional, Dict, Any, List


class HRMSServiceError(Exception):
    """Base exception for all HRMS adapter operations."""
    pass


class BackendUnavailableError(HRMSServiceError):
    """Raised when the HRMS backend/mock is unreachable, times out, or returns a 5xx / malformed response."""

    def __init__(
        self,
        message: str = "HRMS service is currently unavailable. Please try again shortly.",
    ):
        super().__init__(message)
        self.message = message


class EmployeeNotFoundError(HRMSServiceError):
    """Raised when an employee is not found in the HRMS system (when raise_for_not_found=True)."""

    def __init__(self, employee_id: str, message: Optional[str] = None):
        msg = message or f"Employee '{employee_id}' not found in HRMS."
        super().__init__(msg)
        self.employee_id = employee_id
        self.message = msg


class LeaveApplicationError(HRMSServiceError):
    """Raised when a leave application submission fails validation (bad dates, invalid leave type, etc.)."""

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class HRMSAdapter:
    """
    Adapter interfacing with the organization's HRMS backend (mock in dev, real HRMS in prod).
    Self-contained within rasa-hr/actions without importing from backend.
    """

    DEFAULT_TIMEOUT: float = 5.0

    @classmethod
    def _base_url(cls) -> str:
        return os.getenv("MOCK_HRMS_URL", "http://localhost:9002").rstrip("/")

    @classmethod
    async def get_leave_balance(
        cls, employee_id: str, raise_for_not_found: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves leave balance for an employee.

        Args:
            employee_id: Employee ID (e.g. 'EMP-1042').
            raise_for_not_found: If True, raises EmployeeNotFoundError when employee does not exist.
                                 If False (default), returns a structured not-found dictionary.

        Returns:
            Dict containing found, employee_id, total, balance, casual, sick, earned, breakdown.

        Raises:
            EmployeeNotFoundError: If raise_for_not_found is True and employee is not found.
            BackendUnavailableError: If HRMS service is down, times out, or returns malformed response.
        """
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            msg = "Employee ID cannot be empty."
            if raise_for_not_found:
                raise EmployeeNotFoundError(employee_id="", message=msg)
            return {
                "found": False,
                "employee_id": "",
                "employee_name": None,
                "total": 0,
                "balance": 0,
                "casual": 0,
                "sick": 0,
                "earned": 0,
                "breakdown": {"casual": 0, "sick": 0, "earned": 0},
                "status": "Not Found",
                "detail": msg,
            }

        url = f"{cls._base_url()}/employees/{quote(clean_id, safe='')}/leave-balance"
        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                res = await client.get(url)

                if res.status_code == 200:
                    try:
                        data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "HRMS service returned a malformed response (non-JSON payload)."
                        )

                    breakdown = data.get("breakdown", {})
                    total = data.get("total", 0)
                    return {
                        "found": True,
                        "employee_id": data.get("employee_id", clean_id),
                        "employee_name": data.get("employee_name"),
                        "department": data.get("department"),
                        "total": total,
                        "balance": total,
                        "casual": breakdown.get("casual", 0),
                        "sick": breakdown.get("sick", 0),
                        "earned": breakdown.get("earned", 0),
                        "breakdown": breakdown,
                    }

                if res.status_code == 404:
                    try:
                        err_data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        err_data = {"detail": res.text or f"Employee '{clean_id}' not found."}

                    detail = err_data.get("detail", {})
                    if isinstance(detail, dict):
                        msg = detail.get("message", f"Employee '{clean_id}' not found.")
                    else:
                        msg = str(detail)

                    if raise_for_not_found:
                        raise EmployeeNotFoundError(employee_id=clean_id, message=msg)

                    return {
                        "found": False,
                        "employee_id": clean_id,
                        "employee_name": None,
                        "total": 0,
                        "balance": 0,
                        "casual": 0,
                        "sick": 0,
                        "earned": 0,
                        "breakdown": {"casual": 0, "sick": 0, "earned": 0},
                        "status": "Not Found",
                        "detail": msg,
                    }

                if res.status_code >= 500:
                    raise BackendUnavailableError(
                        f"HRMS service internal error: HTTP {res.status_code}."
                    )

                raise BackendUnavailableError(
                    f"HRMS service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"HRMS service is currently unavailable: {str(e)}"
            )

    @classmethod
    async def get_leave_status(
        cls,
        employee_id: str,
        reference_id: Optional[str] = None,
        raise_for_not_found: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves leave application status history for an employee.

        Args:
            employee_id: Employee ID (e.g. 'EMP-1001').
            reference_id: Optional reference ID to filter for a specific request.
            raise_for_not_found: If True, raises EmployeeNotFoundError when employee does not exist.

        Returns:
            Dict containing found, employee_id, applications, latest_status, latest_reference_id.

        Raises:
            EmployeeNotFoundError: If raise_for_not_found is True and employee is not found.
            BackendUnavailableError: If HRMS service is down, times out, or returns malformed response.
        """
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            msg = "Employee ID cannot be empty."
            if raise_for_not_found:
                raise EmployeeNotFoundError(employee_id="", message=msg)
            return {
                "found": False,
                "employee_id": "",
                "employee_name": None,
                "applications": [],
                "latest_status": None,
                "latest_reference_id": None,
                "status": "Not Found",
                "detail": msg,
            }

        url = f"{cls._base_url()}/employees/{quote(clean_id, safe='')}/leave-status"
        params = {}
        if reference_id:
            params["reference_id"] = reference_id.strip()

        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                res = await client.get(url, params=params)

                if res.status_code == 200:
                    try:
                        data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "HRMS service returned a malformed response (non-JSON payload)."
                        )

                    applications = data.get("applications", [])
                    latest = applications[-1] if applications else None
                    return {
                        "found": True,
                        "employee_id": data.get("employee_id", clean_id),
                        "employee_name": data.get("employee_name"),
                        "applications": applications,
                        "latest_status": latest.get("status") if latest else None,
                        "latest_reference_id": latest.get("reference_id") if latest else None,
                    }

                if res.status_code == 404:
                    try:
                        err_data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        err_data = {"detail": res.text or f"Employee '{clean_id}' not found."}

                    detail = err_data.get("detail", {})
                    if isinstance(detail, dict):
                        msg = detail.get("message", f"Employee '{clean_id}' not found.")
                    else:
                        msg = str(detail)

                    if raise_for_not_found:
                        raise EmployeeNotFoundError(employee_id=clean_id, message=msg)

                    return {
                        "found": False,
                        "employee_id": clean_id,
                        "employee_name": None,
                        "applications": [],
                        "latest_status": None,
                        "latest_reference_id": None,
                        "status": "Not Found",
                        "detail": msg,
                    }

                if res.status_code >= 500:
                    raise BackendUnavailableError(
                        f"HRMS service internal error: HTTP {res.status_code}."
                    )

                raise BackendUnavailableError(
                    f"HRMS service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"HRMS service is currently unavailable: {str(e)}"
            )

    @classmethod
    async def submit_leave(
        cls,
        employee_id: str,
        type: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        reason: str = "",
        *,
        leave_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        raise_for_not_found: bool = False,
    ) -> Dict[str, Any]:
        """
        Submits a leave request for an employee.

        Args:
            employee_id: Employee ID (e.g. 'EMP-1042').
            type / leave_type: Leave type ('casual', 'sick', 'earned', 'annual').
            start / start_date: Start date (YYYY-MM-DD).
            end / end_date: End date (YYYY-MM-DD).
            reason: Optional justification.
            raise_for_not_found: If True, raises EmployeeNotFoundError when employee does not exist.

        Returns:
            Dict containing success, reference_id, employee_id, leave_type, days, status, remaining_balance.

        Raises:
            LeaveApplicationError: If arguments fail validation.
            EmployeeNotFoundError: If raise_for_not_found is True and employee is not found.
            BackendUnavailableError: If HRMS service is down or times out.
        """
        clean_id = (employee_id or "").strip().upper()
        if not clean_id:
            msg = "Employee ID cannot be empty."
            if raise_for_not_found:
                raise EmployeeNotFoundError(employee_id="", message=msg)
            return {
                "success": False,
                "found": False,
                "employee_id": "",
                "reference_id": None,
                "status": "Not Found",
                "detail": msg,
            }

        actual_type = (type or leave_type or "").strip()
        actual_start = (start or start_date or "").strip()
        actual_end = (end or end_date or "").strip()

        if not actual_type:
            raise LeaveApplicationError("leave_type is required.")
        if not actual_start:
            raise LeaveApplicationError("start_date is required.")
        if not actual_end:
            raise LeaveApplicationError("end_date is required.")

        url = f"{cls._base_url()}/leave/submit"
        payload = {
            "employee_id": clean_id,
            "leave_type": actual_type,
            "start_date": actual_start,
            "end_date": actual_end,
            "reason": reason or "",
        }

        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                res = await client.post(url, json=payload)

                if res.status_code in (200, 201):
                    try:
                        data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "HRMS service returned a malformed response (non-JSON payload)."
                        )

                    return {
                        "success": True,
                        "found": True,
                        "reference_id": data.get("reference_id"),
                        "employee_id": data.get("employee_id", clean_id),
                        "leave_type": data.get("leave_type", actual_type),
                        "start_date": data.get("start_date", actual_start),
                        "end_date": data.get("end_date", actual_end),
                        "days": data.get("days", 1),
                        "status": data.get("status", "submitted"),
                        "remaining_balance": data.get("remaining_balance", {}),
                        "message": data.get("message", "Leave application submitted successfully."),
                    }

                if res.status_code == 404:
                    try:
                        err_data = res.json()
                    except (ValueError, json.JSONDecodeError):
                        err_data = {"detail": res.text or f"Employee '{clean_id}' not found."}

                    detail = err_data.get("detail", {})
                    if isinstance(detail, dict):
                        msg = detail.get("message", f"Employee '{clean_id}' not found.")
                    else:
                        msg = str(detail)

                    if raise_for_not_found:
                        raise EmployeeNotFoundError(employee_id=clean_id, message=msg)

                    return {
                        "success": False,
                        "found": False,
                        "employee_id": clean_id,
                        "reference_id": None,
                        "status": "Not Found",
                        "detail": msg,
                    }

                if res.status_code in (400, 422):
                    try:
                        err_data = res.json()
                        detail = err_data.get("detail", res.text)
                    except (ValueError, json.JSONDecodeError):
                        detail = res.text
                    raise LeaveApplicationError(
                        message=f"Invalid leave application: {detail}",
                        detail=detail,
                    )

                if res.status_code >= 500:
                    raise BackendUnavailableError(
                        f"HRMS service internal error: HTTP {res.status_code}."
                    )

                raise BackendUnavailableError(
                    f"HRMS service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"HRMS service is currently unavailable: {str(e)}"
            )

    @classmethod
    async def get_policy(cls, policy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves an HR policy or all policies.

        Args:
            policy_id: Optional policy identifier (e.g. 'leave-policy', 'wfh-policy').

        Returns:
            Dict containing policy data or list of policies.

        Raises:
            BackendUnavailableError: If HRMS service is down or times out.
        """
        if policy_id:
            clean_pid = policy_id.strip().lower()
            url = f"{cls._base_url()}/policies/{quote(clean_pid, safe='')}"
        else:
            url = f"{cls._base_url()}/policies"

        try:
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                res = await client.get(url)

                if res.status_code == 200:
                    try:
                        return res.json()
                    except (ValueError, json.JSONDecodeError):
                        raise BackendUnavailableError(
                            "HRMS service returned a malformed response (non-JSON payload)."
                        )

                if res.status_code == 404:
                    return {
                        "found": False,
                        "policy_id": policy_id,
                        "detail": f"Policy '{policy_id}' not found.",
                    }

                raise BackendUnavailableError(
                    f"HRMS service returned unexpected HTTP status {res.status_code}."
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise BackendUnavailableError(
                f"HRMS service is currently unavailable: {str(e)}"
            )
