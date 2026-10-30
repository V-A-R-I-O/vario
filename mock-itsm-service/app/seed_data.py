"""Deterministic in-memory seed data for the Mock ITSM service."""
import copy
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
    "EMP-3001": {"employee_id": "EMP-3001", "security_question": "What was your first work location?", "security_answer": "north campus"},
    "EMP-4001": {"employee_id": "EMP-4001", "security_question": "What was your first work location?", "security_answer": "south campus"},
    "EMP-1010": {"employee_id": "EMP-1010", "security_question": "What was your first work location?", "security_answer": "north campus"},
    "EMP-1011": {"employee_id": "EMP-1011", "security_question": "What was your first work location?", "security_answer": "north campus"},
    "EMP-1012": {"employee_id": "EMP-1012", "security_question": "What was your first work location?", "security_answer": "north campus"},
    "EMP-1013": {"employee_id": "EMP-1013", "security_question": "What was your first work location?", "security_answer": "north campus"},
}

TICKETS = copy.deepcopy(INITIAL_TICKETS)
EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
VERIFIED_EMPLOYEES: set[str] = set()
TICKET_COUNTER = 1003


def reset_seed_data() -> None:
    """Restore tickets, employees, and verification state to initial demo data."""
    global TICKETS, EMPLOYEES, VERIFIED_EMPLOYEES, TICKET_COUNTER
    TICKETS = copy.deepcopy(INITIAL_TICKETS)
    EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
    VERIFIED_EMPLOYEES = set()
    TICKET_COUNTER = 1003
