# Slice 23 — adm-adapter

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 2 · **Module:** `integration-adapters` (Admissions) + Mock Admissions service

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `integration-adapters` module + § Reliability
- `docs/vario-overview.md` § 6 (FR-14…FR-17) and § 7 (Reliability)
- `.env.example` (`MOCK_ADMISSIONS_URL`)

## What to build
The Mock Admissions backend and the `AdmissionsAdapter`. Build the full method surface the Admissions vertical needs across Sprint 2–3, but this slice's acceptance focuses on **application status**; checklist and calendar methods exist for `slice-25` / `slice-26`.

Deliverables:
- **Mock Admissions** — a FastAPI service at `MOCK_ADMISSIONS_URL`, pre-seeded with applications (id, applicant, program, status, next-step), per-program **document checklists**, and a single configurable **admissions calendar** (fees + deadlines).
- **`AdmissionsAdapter`** implementing: `get_application_status(application_id)`, `get_document_checklist(program)`, `get_calendar()`. Points at `MOCK_ADMISSIONS_URL`.
- **Typed errors** — unknown application id → not-found (with a suggested next step, per FR-17); mock down → typed "backend unavailable" error (graceful, prompt).

## Acceptance criteria
- [ ] Given the Mock Admissions, when it starts, then it is seeded with several applications, per-program checklists, and one calendar.
- [ ] Given a seeded `application_id`, when `get_application_status` is called, then it returns status + a suggested next step.
- [ ] Given an unknown `application_id`, then the adapter returns a not-found result carrying a suggested next step (supports FR-17).
- [ ] Given the mock is down, then the adapter raises a typed "backend unavailable" error and returns promptly.
- [ ] Given the adapter, then `get_document_checklist` and `get_calendar` are implemented and callable (exercised in `slice-25` / `slice-26`).

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Rasa wiring / chat cards (`slice-22`, `slice-24`).
- Checklist list UI (`slice-25`) and fee/deadline flow (`slice-26`) — methods exist here; flows are elsewhere.
- Other adapters and any real Admissions integration.

## Human review required?
No.
