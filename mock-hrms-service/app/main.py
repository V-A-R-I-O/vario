"""Mock HRMS Service FastAPI Application."""
import os
import asyncio
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Header, Query, Request, status
from pydantic import BaseModel, Field

try:
    from . import seed_data as sd
    from .seed_data import (
        EMPLOYEES,
        POLICIES,
        LEAVE_COUNTER,
        reset_seed_data,
    )
except (ImportError, ValueError):
    try:
        from app import seed_data as sd
        from app.seed_data import (
            EMPLOYEES,
            POLICIES,
            LEAVE_COUNTER,
            reset_seed_data,
        )
    except (ImportError, ValueError):
        import mock_hrms_app.seed_data as sd
        from mock_hrms_app.seed_data import (
            EMPLOYEES,
            POLICIES,
            LEAVE_COUNTER,
            reset_seed_data,
        )

app = FastAPI(
    title="Mock HRMS Service",
    description="Mock internal HRMS backend for VARIO HR Role Pack",
    version="0.1.0",
)


async def _handle_artificial_delay(
    request: Request,
    header_delay: Optional[str] = None,
    query_delay: Optional[float] = None,
) -> None:
    """Applies artificial delay if requested via header, query param, or env var."""
    delay = 0.0

    # 1. Check env var
    env_delay_str = os.getenv("MOCK_HRMS_DELAY_SECONDS", "")
    if env_delay_str:
        try:
            delay = float(env_delay_str)
        except ValueError:
            pass

    # 2. Check query param
    if query_delay is not None and query_delay > 0:
        delay = query_delay

    # 3. Check header
    if header_delay:
        try:
            h_val = float(header_delay)
            if h_val > 0:
                delay = h_val
        except ValueError:
            pass

    if delay > 0:
        await asyncio.sleep(delay)


@app.middleware("http")
async def delay_middleware(request: Request, call_next):
    header_val = request.headers.get("x-mock-delay")
    query_val = None
    q = request.query_params.get("delay")
    if q:
        try:
            query_val = float(q)
        except (ValueError, TypeError):
            pass
    await _handle_artificial_delay(request, header_delay=header_val, query_delay=query_val)
    response = await call_next(request)
    return response


class SubmitLeaveRequest(BaseModel):
    employee_id: str = Field(..., description="Employee identifier, e.g. EMP-1042")
    leave_type: str = Field(..., description="Leave type: casual, sick, or earned")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    reason: Optional[str] = Field(default="", description="Reason for leave request")


LEAVE_TYPE_MAPPING = {
    "casual": "casual",
    "sick": "sick",
    "earned": "earned",
    "annual": "earned",
    "vacation": "earned",
    "paid": "earned",
    "pto": "earned",
}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "mock-hrms", "version": "0.1.0"}


@app.post("/reset")
async def reset_data() -> Dict[str, str]:
    reset_seed_data()
    return {"status": "ok", "message": "Seed data reset successfully."}


@app.get("/employees/{employee_id}/leave-balance")
@app.get("/leave/balance/{employee_id}")
async def get_leave_balance(
    employee_id: str,
    delay: Optional[float] = Query(None, description="Artificial delay in seconds"),
) -> Dict[str, Any]:
    norm_id = (employee_id or "").strip().upper()
    if not norm_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Employee ID cannot be empty.", "employee_id": employee_id},
        )

    emp = EMPLOYEES.get(norm_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Employee '{norm_id}' not found.", "employee_id": norm_id},
        )

    balances = emp.get("leave_balances", {})
    casual = balances.get("casual", 0)
    sick = balances.get("sick", 0)
    earned = balances.get("earned", 0)
    total = casual + sick + earned

    return {
        "employee_id": emp["employee_id"],
        "employee_name": emp.get("employee_name", ""),
        "department": emp.get("department", ""),
        "total": total,
        "breakdown": {
            "casual": casual,
            "sick": sick,
            "earned": earned,
        },
    }


@app.get("/employees/{employee_id}/leave-status")
@app.get("/leave/status/{employee_id}")
async def get_leave_status(
    employee_id: str,
    reference_id: Optional[str] = Query(None, description="Optional leave reference ID to filter by"),
    delay: Optional[float] = Query(None, description="Artificial delay in seconds"),
) -> Dict[str, Any]:
    norm_id = (employee_id or "").strip().upper()
    if not norm_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Employee ID cannot be empty.", "employee_id": employee_id},
        )

    emp = EMPLOYEES.get(norm_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Employee '{norm_id}' not found.", "employee_id": norm_id},
        )

    history = emp.get("leave_history", [])
    if reference_id:
        norm_ref = reference_id.strip().upper()
        history = [item for item in history if item.get("reference_id", "").upper() == norm_ref]

    return {
        "employee_id": emp["employee_id"],
        "employee_name": emp.get("employee_name", ""),
        "applications": history,
    }


@app.post("/leave/submit", status_code=status.HTTP_201_CREATED)
@app.post("/employees/{employee_id}/leave", status_code=status.HTTP_201_CREATED)
async def submit_leave(
    req: SubmitLeaveRequest,
    employee_id: Optional[str] = None,
    delay: Optional[float] = Query(None, description="Artificial delay in seconds"),
) -> Dict[str, Any]:
    target_emp_id = employee_id or req.employee_id
    norm_id = (target_emp_id or "").strip().upper()

    if not norm_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Employee ID cannot be empty.", "employee_id": target_emp_id},
        )

    emp = EMPLOYEES.get(norm_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Employee '{norm_id}' not found.", "employee_id": norm_id},
        )

    # Validate leave type
    raw_type = (req.leave_type or "").strip().lower()
    norm_type = LEAVE_TYPE_MAPPING.get(raw_type)
    if not norm_type:
        valid_types = ", ".join(sorted(set(LEAVE_TYPE_MAPPING.values())))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid leave type '{req.leave_type}'. Allowed types: {valid_types}.",
        )

    # Validate dates
    try:
        s_date = datetime.strptime(req.start_date.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid start_date '{req.start_date}'. Must be in YYYY-MM-DD format.",
        )

    try:
        e_date = datetime.strptime(req.end_date.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid end_date '{req.end_date}'. Must be in YYYY-MM-DD format.",
        )

    if s_date > e_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_date ({req.start_date}) cannot be after end_date ({req.end_date}).",
        )

    duration_days = (e_date - s_date).days + 1

    # Generate reference ID
    sd.LEAVE_COUNTER += 1
    ref_id = f"LEAVE-{sd.LEAVE_COUNTER}"

    # Record leave application
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "reference_id": ref_id,
        "leave_type": norm_type,
        "start_date": req.start_date.strip(),
        "end_date": req.end_date.strip(),
        "days": duration_days,
        "status": "submitted",
        "reason": (req.reason or "").strip(),
        "submitted_at": now_iso,
    }
    emp["leave_history"].append(record)

    # Deduct balance
    current_val = emp["leave_balances"].get(norm_type, 0)
    emp["leave_balances"][norm_type] = max(0, current_val - duration_days)
    emp["total"] = sum(emp["leave_balances"].values())

    return {
        "success": True,
        "reference_id": ref_id,
        "employee_id": norm_id,
        "leave_type": norm_type,
        "start_date": req.start_date.strip(),
        "end_date": req.end_date.strip(),
        "days": duration_days,
        "status": "submitted",
        "remaining_balance": {
            "total": emp["total"],
            "breakdown": dict(emp["leave_balances"]),
        },
        "message": "Leave application submitted successfully.",
    }


@app.get("/policies")
async def list_policies() -> Dict[str, Any]:
    return {"policies": list(POLICIES.values())}


@app.get("/policies/{policy_id}")
async def get_policy(policy_id: str) -> Dict[str, Any]:
    norm_key = (policy_id or "").strip().lower()
    policy = POLICIES.get(norm_key)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found.",
        )
    return policy
