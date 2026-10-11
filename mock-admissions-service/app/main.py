from fastapi import FastAPI, HTTPException, status
from typing import Dict, Any, Optional

try:
    from .seed_data import (
        SEED_APPLICATIONS,
        SEED_CHECKLISTS,
        SEED_CALENDAR,
        DEFAULT_SUGGESTED_NEXT_STEP,
    )
except (ImportError, ValueError):
    from app.seed_data import (
        SEED_APPLICATIONS,
        SEED_CHECKLISTS,
        SEED_CALENDAR,
        DEFAULT_SUGGESTED_NEXT_STEP,
    )

app = FastAPI(
    title="Mock Admissions Service",
    description="Mock internal admissions backend for VARIO Admissions Role Pack",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "mock-admissions"}


@app.get("/applications/{application_id}")
def get_application(application_id: str) -> Dict[str, Any]:
    norm_id = application_id.strip().upper()
    app_record = SEED_APPLICATIONS.get(norm_id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"Application '{application_id}' not found.",
                "application_id": application_id,
                "suggested_next_step": DEFAULT_SUGGESTED_NEXT_STEP,
            },
        )
    return app_record


@app.get("/checklists/{program}")
def get_document_checklist(program: str) -> Dict[str, Any]:
    clean_prog = program.strip().lower()

    # Direct key lookup or alias matching
    matched = None
    if clean_prog in SEED_CHECKLISTS:
        matched = SEED_CHECKLISTS[clean_prog]
    else:
        for entry in SEED_CHECKLISTS.values():
            if clean_prog == entry["program"].lower():
                matched = entry
                break
            for alias in entry.get("aliases", []):
                if alias in clean_prog or clean_prog in alias:
                    matched = entry
                    break
            if matched:
                break

    if not matched:
        available = [item["program"] for item in SEED_CHECKLISTS.values()]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"No checklist found for program '{program}'.",
                "available_programs": available,
            },
        )

    return {
        "program": matched["program"],
        "required_documents": matched["required_documents"],
    }


@app.get("/calendar")
def get_calendar() -> Dict[str, Any]:
    return SEED_CALENDAR
