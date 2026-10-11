from typing import Dict, Any, List

SEED_APPLICATIONS: Dict[str, Dict[str, Any]] = {
    "APP-1001": {
        "application_id": "APP-1001",
        "applicant_name": "Aarav Sharma",
        "program": "Computer Science (B.Tech)",
        "status": "Under Review",
        "next_step": "Your application is currently being evaluated by the departmental admissions committee. Results will be posted by October 25, 2026.",
        "submission_date": "2026-09-10",
        "fee_status": "Paid",
    },
    "APP-1002": {
        "application_id": "APP-1002",
        "applicant_name": "Diya Patel",
        "program": "Data Science (M.Tech)",
        "status": "Accepted",
        "next_step": "Congratulations! Pay the seat confirmation deposit of ₹50,000 by November 15, 2026 to confirm your admission.",
        "submission_date": "2026-09-05",
        "fee_status": "Pending Deposit",
    },
    "APP-1003": {
        "application_id": "APP-1003",
        "applicant_name": "Rohan Mehta",
        "program": "Computer Science (B.Tech)",
        "status": "Documents Pending",
        "next_step": "Upload your official Class 12 passing certificate and Migration Certificate on the applicant portal by October 20, 2026.",
        "submission_date": "2026-09-18",
        "fee_status": "Paid",
    },
    "APP-1004": {
        "application_id": "APP-1004",
        "applicant_name": "Ananya Iyer",
        "program": "MBA",
        "status": "Rejected",
        "next_step": "Eligibility criteria were not met for this cycle. You may reapply during the spring semester or contact academic counseling.",
        "submission_date": "2026-08-28",
        "fee_status": "Paid",
    },
}

SEED_CHECKLISTS: Dict[str, Dict[str, Any]] = {
    "btech": {
        "program": "Computer Science (B.Tech)",
        "aliases": ["btech", "b.tech", "computer science", "cs"],
        "required_documents": [
            "Class 10 Grade Sheet / Birth Certificate",
            "Class 12 / Higher Secondary Marksheet",
            "National/State Entrance Exam Scorecard (JEE / CET)",
            "Transfer Certificate & Conduct Certificate",
            "Valid Government Photo ID (Passport or Aadhaar)",
        ],
    },
    "mtech": {
        "program": "Data Science (M.Tech)",
        "aliases": ["mtech", "m.tech", "data science", "ds"],
        "required_documents": [
            "Undergraduate Degree Certificate & Consolidated Transcripts",
            "GATE / PGCET Scorecard",
            "Curriculum Vitae (CV) / Resume",
            "Statement of Purpose (SOP)",
            "Two Letters of Recommendation (Academic or Professional)",
        ],
    },
    "mba": {
        "program": "MBA",
        "aliases": ["mba", "business administration", "management"],
        "required_documents": [
            "Bachelor's Degree Certificate with Minimum 50% Aggregate",
            "Management Entrance Exam Scorecard (CAT / GMAT / MAT / XAT)",
            "Statement of Purpose (SOP)",
            "Work Experience Certificate (if applicable)",
            "Government Identity Proof",
        ],
    },
}

SEED_CALENDAR: Dict[str, Any] = {
    "academic_year": "2026-2027",
    "deadlines": [
        {"milestone": "Regular Application Submission Deadline", "date": "November 30, 2026"},
        {"milestone": "Document Verification Deadline", "date": "December 10, 2026"},
        {"milestone": "First Merit List & Deposit Payment", "date": "December 18, 2026"},
        {"milestone": "Second Merit List & Deposit Payment", "date": "December 28, 2026"},
        {"milestone": "Orientation & Commencement of Classes", "date": "January 15, 2027"},
    ],
    "fees": [
        {"item": "Application Fee (All Programs)", "amount": "₹1,500 (Non-refundable)"},
        {"item": "Computer Science (B.Tech) Annual Tuition", "amount": "₹3,20,000"},
        {"item": "Data Science (M.Tech) Annual Tuition", "amount": "₹2,80,000"},
        {"item": "MBA Annual Tuition", "amount": "₹4,50,000"},
        {"item": "Hostel Fee & Caution Deposit", "amount": "₹75,000 (includes ₹10,000 refundable caution deposit)"},
    ],
    "refund_policy": "100% refund (minus ₹1,000 processing fee) if withdrawal request is submitted at least 15 days before classes begin. 50% refund within 7 days before classes begin.",
    "contact": {
        "email": "admissions@org.example.com",
        "phone": "+91-80-2672-1983",
        "office_hours": "Monday to Friday, 9:00 AM - 5:00 PM IST",
    },
}

DEFAULT_SUGGESTED_NEXT_STEP = (
    "Please double-check your application ID format (e.g., APP-1001) or reach out "
    "to the Admissions Office at admissions@org.example.com or +91-80-2672-1983."
)
