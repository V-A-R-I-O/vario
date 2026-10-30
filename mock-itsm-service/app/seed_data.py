"""Deterministic demo data and durable per-employee identity attempt counters."""
import copy
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict

INITIAL_TICKETS: Dict[str, Dict[str, Any]] = {
    "IT-1001": {"ticket_id": "IT-1001", "category": "hardware", "description": "Laptop battery drains quickly", "reporter": "EMP-1042", "status": "In Progress", "created_at": "2026-10-20T09:15:00Z", "updated_at": "2026-10-21T12:30:00Z"},
    "IT-1002": {"ticket_id": "IT-1002", "category": "access", "description": "Cannot access the analytics portal", "reporter": "EMP-1001", "status": "Open", "created_at": "2026-10-22T10:00:00Z", "updated_at": "2026-10-22T10:00:00Z"},
    "IT-1003": {"ticket_id": "IT-1003", "category": "software", "description": "VPN client installation request", "reporter": "EMP-1042", "status": "Resolved", "created_at": "2026-10-18T08:45:00Z", "updated_at": "2026-10-19T14:20:00Z"},
}
INITIAL_EMPLOYEES: Dict[str, Dict[str, str]] = {
    "EMP-1001": {"employee_id": "EMP-1001", "security_question": "What was the name of your first school?", "security_answer": "sunrise"},
    "EMP-1042": {"employee_id": "EMP-1042", "security_question": "What city were you born in?", "security_answer": "mysuru"},
    "EMP-2001": {"employee_id": "EMP-2001", "security_question": "What is your favorite book?", "security_answer": "the hobbit"},
}
TICKETS = copy.deepcopy(INITIAL_TICKETS)
EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
VERIFIED_EMPLOYEES: set[str] = set()
TICKET_COUNTER = 1003
_ATTEMPT_LOCK = threading.Lock()


def _attempt_path() -> Path:
    return Path(os.environ.get("IDENTITY_ATTEMPTS_PATH", str(Path(tempfile.gettempdir()) / "vario-identity-attempts.json")))


def _read_attempts() -> Dict[str, int]:
    path = _attempt_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return {str(key): max(0, int(value)) for key, value in payload.items()}
    except (OSError, ValueError, TypeError):
        return {}


def _write_attempts(attempts: Dict[str, int]) -> None:
    path = _attempt_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(attempts, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def identity_attempt_state(employee_id: str) -> Dict[str, Any]:
    clean_id = (employee_id or "").strip().upper()
    with _ATTEMPT_LOCK:
        attempts = _read_attempts().get(clean_id, 0)
    return {"attempts": attempts, "locked": attempts >= 3, "attempts_remaining": max(0, 3 - attempts)}


def record_identity_failure(employee_id: str) -> Dict[str, Any]:
    clean_id = (employee_id or "").strip().upper()
    with _ATTEMPT_LOCK:
        attempts = _read_attempts()
        attempts[clean_id] = min(3, attempts.get(clean_id, 0) + 1)
        _write_attempts(attempts)
        count = attempts[clean_id]
    return {"attempts": count, "locked": count >= 3, "attempts_remaining": max(0, 3 - count)}


def clear_identity_attempts(employee_id: str) -> None:
    clean_id = (employee_id or "").strip().upper()
    with _ATTEMPT_LOCK:
        attempts = _read_attempts()
        attempts.pop(clean_id, None)
        _write_attempts(attempts)


def reset_identity_attempts() -> None:
    with _ATTEMPT_LOCK:
        _write_attempts({})


def reset_seed_data() -> None:
    """Restore demo records and clear verification/attempt state for explicit test/demo reset."""
    global TICKETS, EMPLOYEES, VERIFIED_EMPLOYEES, TICKET_COUNTER
    TICKETS = copy.deepcopy(INITIAL_TICKETS)
    EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
    VERIFIED_EMPLOYEES = set()
    TICKET_COUNTER = 1003
    reset_identity_attempts()
