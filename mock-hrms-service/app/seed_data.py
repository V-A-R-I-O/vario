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
    "EMP-1010": {
        "employee_id": "EMP-1010",
        "employee_name": "Pavan Kishor",
        "email": "pavan@org.example.com",
        "department": "Engineering",
        "leave_balances": {
            "casual": 6,
            "sick": 8,
            "earned": 14,
        },
        "total": 28,
        "leave_history": [
            {
                "reference_id": "LEAVE-2025",
                "leave_type": "casual",
                "start_date": "2026-08-10",
                "end_date": "2026-08-11",
                "days": 2,
                "status": "approved",
                "reason": "Personal work",
                "submitted_at": "2026-08-05T10:00:00Z",
            }
        ],
    },
    "EMP-1011": {
        "employee_id": "EMP-1011",
        "employee_name": "Tahir",
        "email": "tahir@org.example.com",
        "department": "Infrastructure",
        "leave_balances": {
            "casual": 5,
            "sick": 7,
            "earned": 12,
        },
        "total": 24,
        "leave_history": [],
    },
    "EMP-1012": {
        "employee_id": "EMP-1012",
        "employee_name": "Rohith",
        "email": "rohith@org.example.com",
        "department": "IT Operations",
        "leave_balances": {
            "casual": 4,
            "sick": 6,
            "earned": 10,
        },
        "total": 20,
        "leave_history": [],
    },
    "EMP-1013": {
        "employee_id": "EMP-1013",
        "employee_name": "Mitesh",
        "email": "mitesh@org.example.com",
        "department": "Admissions QA",
        "leave_balances": {
            "casual": 5,
            "sick": 8,
            "earned": 15,
        },
        "total": 28,
        "leave_history": [],
    },
}

INITIAL_POLICIES: Dict[str, Dict[str, Any]] = {
    "leave-policy": {
        "policy_id": "leave-policy",
        "title": "Annual & Statutory Leave Policy",
        "summary": "Overview of casual, sick, and earned leave entitlements and request guidelines.",
        "details": "Employees are entitled to 8 casual days, 10 sick days, and 15 earned days annually. Casual leave requires 24h advance notice; sick leave exceeding 3 days requires a medical certificate. Earned leave requires manager pre-approval 2 weeks in advance. Unused earned leaves can be carried forward up to 5 days.",
        "quota": {
            "casual": 8,
            "sick": 10,
            "earned": 15,
        },
        "carry_forward_days": 5,
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
    "maternity-policy": {
        "policy_id": "maternity-policy",
        "title": "Maternity & Adoption Leave Policy",
        "summary": "Maternity and adoption leave entitlements for primary caregivers.",
        "details": "Primary caregivers receive 26 weeks of paid maternity and adoption leave.",
        "weeks": 26,
    },
    "paternity-policy": {
        "policy_id": "paternity-policy",
        "title": "Paternity Leave Policy",
        "summary": "Paternity leave entitlements for secondary caregivers.",
        "details": "Secondary caregivers receive 2 weeks of paid paternity leave within the child's first 6 months.",
        "weeks": 2,
    },
    "sick-leave-policy": {
        "policy_id": "sick-leave-policy",
        "title": "Sick Leave Policy",
        "summary": "Guidelines for illness and medical leave.",
        "details": "Employees are entitled to 10 paid sick days per year. Sick leave exceeding 3 consecutive days requires a medical certificate.",
        "days": 10,
    },
    "bereavement-leave": {
        "policy_id": "bereavement-leave",
        "title": "Bereavement & Compassionate Leave",
        "summary": "Paid leave for family bereavement and compassionate circumstances.",
        "details": "Employees are entitled to 5 consecutive business days of paid compassionate leave upon the loss of an immediate family member.",
        "days": 5,
    },
    "carry-forward-policy": {
        "policy_id": "carry-forward-policy",
        "title": "Leave Carry-Forward Policy",
        "summary": "Rules on rolling over unused leave to the following year.",
        "details": "Employees may carry forward up to 5 days of unused earned leave into the following calendar year.",
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
    EMPLOYEES.clear()
    EMPLOYEES.update(copy.deepcopy(INITIAL_EMPLOYEES))
    POLICIES.clear()
    POLICIES.update(copy.deepcopy(INITIAL_POLICIES))
    LEAVE_COUNTER = 2031
