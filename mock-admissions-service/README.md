# VARIO — Mock Admissions Service

Mock Admissions backend service for the Admissions Role Pack. Runs as a standalone FastAPI service on port 9004 (`MOCK_ADMISSIONS_URL`).

## Endpoints

- `GET /health` — Service health check
- `GET /applications/{application_id}` — Returns application details (status, next step, program). If unknown, returns 404 with suggested next step (FR-17).
- `GET /checklists/{program}` — Returns required document checklist for a program (FR-15).
- `GET /calendar` — Single source of truth for admission fees, milestones, and deadlines (FR-16).

## Running Locally

```bash
uvicorn app.main:app --port 9004 --reload
```

## Running Tests

```bash
pytest tests/
```
