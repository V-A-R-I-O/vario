import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

DATE_PATTERNS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y.%m.%d",
]


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse a date string into a date object.
    Supports ISO formats, common punctuation formats, and natural language
    relative expressions (today, tomorrow, next monday, in N days).
    """
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip().lower()
    today = date.today()

    if clean in ("today", "now"):
        return today

    if clean in ("tomorrow", "tmrw"):
        return today + timedelta(days=1)

    if clean in ("day after tomorrow",):
        return today + timedelta(days=2)

    # "in X days" / "in X day"
    m_days = re.match(r"^in\s+(\d+)\s+days?$", clean)
    if m_days:
        return today + timedelta(days=int(m_days.group(1)))

    # "in X weeks? / in X week"
    m_weeks = re.match(r"^in\s+(\d+)\s+weeks?$", clean)
    if m_weeks:
        return today + timedelta(weeks=int(m_weeks.group(1)))

    # "next <weekday>" or "<weekday>"
    m_next_wd = re.match(r"^(?:next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)$", clean)
    if m_next_wd:
        target_wd = WEEKDAYS[m_next_wd.group(1)]
        current_wd = today.weekday()
        days_ahead = target_wd - current_wd
        if days_ahead <= 0 or clean.startswith("next "):
            days_ahead += 7
        return today + timedelta(days=days_ahead)

    # Standard formats
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, TypeError):
            continue

    # Attempt to extract YYYY-MM-DD from within text
    m_iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", date_str)
    if m_iso:
        try:
            return datetime.strptime(m_iso.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    return None


def validate_date_input(
    date_str: str,
    reference_date: Optional[date] = None,
    allow_past: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate a date string for leave requests.

    Returns:
        (iso_date_string, error_message)
        If valid: (YYYY-MM-DD, None)
        If invalid: (None, error_guidance_message)
    """
    parsed = parse_date(date_str)
    if not parsed:
        return None, "Please provide a valid date (e.g. 'YYYY-MM-DD', 'tomorrow', or 'next monday')."

    today = date.today()
    if not allow_past and parsed < today:
        return None, "Dates cannot be in the past. Please enter a valid future date."

    if reference_date and parsed < reference_date:
        return None, "End date must be on or after the start date."

    return parsed.isoformat(), None
