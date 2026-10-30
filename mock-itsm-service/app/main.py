"""Mock ITSM service used by the VARIO integration adapter."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import seed_data as sd

app = FastAPI(
    title="Mock ITSM Service",
    description="In-memory ticketing and identity-verification backend for VARIO development/demo.",
    version="0.1.0",
)


class TicketCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    reporter: str = Field(min_length=1, max_length=80)


class IdentityVerifyRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=300)


class PasswordResetRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "mock-itsm", "version": "0.1.0"}


@app.post("/reset")
async def reset_data() -> Dict[str, str]:
    sd.reset_seed_data()
    return {"status": "ok", "message": "Seed data reset successfully."}


@app.get("/tickets")
async def list_tickets() -> Dict[str, Any]:
    """Return ticket summaries for local debugging; never includes identity answers."""
    return {"tickets": list(sd.TICKETS.values())}


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> Dict[str, Any]:
    clean_id = (ticket_id or "").strip().upper()
    ticket = sd.TICKETS.get(clean_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": f"Ticket '{clean_id}' was not found.", "ticket_id": clean_id})
    return dict(ticket)


@app.post("/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(request: TicketCreateRequest) -> Dict[str, Any]:
    category, description, reporter = request.category.strip(), request.description.strip(), request.reporter.strip().upper()
    if not category or not description or not reporter:
        raise HTTPException(status_code=400, detail="category, description, and reporter are required.")
    if reporter not in sd.EMPLOYEES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": f"Employee '{reporter}' was not found.", "employee_id": reporter})
    sd.TICKET_COUNTER += 1
    ticket_id = f"IT-{sd.TICKET_COUNTER}"
    now = _now()
    ticket = {"ticket_id": ticket_id, "category": category, "description": description,
              "reporter": reporter, "status": "Open", "created_at": now, "updated_at": now}
    sd.TICKETS[ticket_id] = ticket
    return dict(ticket)


@app.get("/identity/{employee_id}/question")
async def get_security_question(employee_id: str) -> Dict[str, Any]:
    clean_id = (employee_id or "").strip().upper()
    employee = sd.EMPLOYEES.get(clean_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": "Employee was not found.", "employee_id": clean_id})
    attempts = sd.identity_attempt_state(clean_id)
    return {"found": True, "employee_id": clean_id, "security_question": employee["security_question"],
            "locked": attempts["locked"], "attempts_remaining": attempts["attempts_remaining"]}


@app.post("/identity/verify")
async def verify_identity(request: IdentityVerifyRequest) -> Dict[str, Any]:
    employee_id = request.employee_id.strip().upper()
    employee = sd.EMPLOYEES.get(employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": f"Employee '{employee_id}' was not found.", "employee_id": employee_id})
    state = sd.identity_attempt_state(employee_id)
    if state["locked"]:
        return {"verified": False, "employee_id": employee_id, "locked": True,
                "attempts_remaining": 0, "detail": "Too many failed verification attempts. Contact IT Support."}
    expected = " ".join(employee["security_answer"].casefold().split())
    supplied = " ".join(request.answer.casefold().split())
    verified = bool(supplied) and supplied == expected
    if verified:
        sd.VERIFIED_EMPLOYEES.add(employee_id)
        sd.clear_identity_attempts(employee_id)
        state = {"locked": False, "attempts_remaining": 3, "attempts": 0}
    else:
        sd.VERIFIED_EMPLOYEES.discard(employee_id)
        state = sd.record_identity_failure(employee_id)
    return {"verified": verified, "employee_id": employee_id, "locked": state["locked"],
            "attempts_remaining": state["attempts_remaining"],
            "detail": "Identity verified." if verified else (
                "Too many failed verification attempts. Contact IT Support." if state["locked"]
                else "The security answer did not match.")}


@app.post("/password/reset")
async def reset_password(request: PasswordResetRequest) -> Dict[str, Any]:
    employee_id = request.employee_id.strip().upper()
    if employee_id not in sd.EMPLOYEES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": f"Employee '{employee_id}' was not found.", "employee_id": employee_id})
    if employee_id not in sd.VERIFIED_EMPLOYEES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Identity verification is required before a password reset.")
    sd.VERIFIED_EMPLOYEES.discard(employee_id)
    return {"success": True, "employee_id": employee_id, "reset_requested": True,
            "message": "Mock password reset initiated."}
