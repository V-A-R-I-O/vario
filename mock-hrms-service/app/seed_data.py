"""Seed data for Mock HRMS service."""
import copy
from typing import Dict, Any, List

INITIAL_EMPLOYEES: Dict[str, Dict[str, Any]] = {
    "EMP-1001": {
        "employee_id": "EMP-1001",
        "employee_name": "Employee One",
        "email": "emp1@org.example.com",
        "department": "Engineering",
        "leave_balances": {
            "casual": 6,
            "sick": 8,
            "earned": 14,
        },
        "total": 28,
        "leave_history": [
            {
                "reference_id": "LEAVE-2031",
                "leave_type": "casual",
                "start_date": "2026-09-10",
                "end_date": "2026-09-11",
                "days": 2,
                "status": "approved",
                "reason": "Personal appointment",
                "submitted_at": "2026-09-07T10:05:00Z",
            }
        ],
    },
    "EMP-1042": {
        "employee_id": "EMP-1042",
        "employee_name": "Jane Smith",
        "email": "jane.smith@org.example.com",
        "department": "Product Marketing",
        "leave_balances": {
            "casual": 4,
            "sick": 6,
            "earned": 12,
        },
        "total": 22,
        "leave_history": [
            {
                "reference_id": "LEAVE-2015",
                "leave_type": "earned",
                "start_date": "2026-08-01",
                "end_date": "2026-08-05",
                "days": 5,
                "status": "approved",
                "reason": "Summer vacation",
                "submitted_at": "2026-07-20T14:30:00Z",
            }
        ],
    },
    "EMP-2001": {
        "employee_id": "EMP-2001",
        "employee_name": "HR Admin",
        "email": "hr@org.example.com",
        "department": "People Operations",
        "leave_balances": {
            "casual": 5,
            "sick": 7,
            "earned": 15,
        },
        "total": 27,
        "leave_history": [],
    },
    "EMP-3001": {
        "employee_id": "EMP-3001",
        "employee_name": "IT Admin",
        "email": "it@org.example.com",
        "department": "Information Technology",
        "leave_balances": {
            "casual": 3,
            "sick": 5,
            "earned": 10,
        },
        "total": 18,
        "leave_history": [],
    },
    "EMP-4001": {
        "employee_id": "EMP-4001",
        "employee_name": "Admissions Admin",
        "email": "admissions@org.example.com",
        "department": "Student Admissions",
        "leave_balances": {
            "casual": 5,
            "sick": 5,
            "earned": 10,
        },
        "total": 20,
        "leave_history": [],
    },
}

INITIAL_POLICIES: Dict[str, Dict[str, Any]] = {
    "leave-policy": {
        "policy_id": "leave-policy",
        "title": "Annual & Statutory Leave Policy",
        "summary": "Overview of casual, sick, and earned leave entitlements and request guidelines.",
        "details": "Employees are entitled to 8 casual days, 10 sick days, and 15 earned days annually. Casual leave requires 24h advance notice; sick leave exceeding 3 days requires a medical certificate. Earned leave requires manager pre-approval 2 weeks in advance.",
        "quota": {
            "casual": 8,
            "sick": 10,
            "earned": 15,
        },
    },
    "wfh-policy": {
        "policy_id": "wfh-policy",
        "title": "Work From Home (WFH) & Hybrid Policy",
        "summary": "Guidelines for remote work eligibility, core hours, and manager approval.",
        "details": "Employees may work remotely up to 2 days per week with line manager alignment. Core collaborative working hours are 10:00 AM to 4:00 PM.",
        "max_wfh_days_per_week": 2,
    },
    "parental-leave": {
        "policy_id": "parental-leave",
        "title": "Parental & Family Leave Policy",
        "summary": "Maternity and paternity benefits for expanding families.",
        "details": "Primary caregivers receive 26 weeks paid maternity/adoption leave. Secondary caregivers receive 2 weeks paid paternity leave within the child's first 6 months.",
        "maternity_weeks": 26,
        "paternity_weeks": 2,
    },
    "bereavement-leave": {
        "policy_id": "bereavement-leave",
        "title": "Bereavement & Compassionate Leave",
        "summary": "Paid leave for family bereavement and compassionate circumstances.",
        "details": "Employees are entitled to 5 consecutive business days of paid compassionate leave upon the loss of an immediate family member.",
        "days": 5,
    },
}

# In-memory working copies
EMPLOYEES: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_EMPLOYEES)
POLICIES: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_POLICIES)
LEAVE_COUNTER: int = 2031


def reset_seed_data() -> None:
    """Resets in-memory employee and policy data back to pristine state."""
    global EMPLOYEES, POLICIES, LEAVE_COUNTER
    EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
    POLICIES = copy.deepcopy(INITIAL_POLICIES)
    LEAVE_COUNTER = 2031
