# Slice 18 — itsm-adapter

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 2 · **Module:** `integration-adapters` (ITSM) + Mock ITSM service

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `integration-adapters` module + § Reliability
- `docs/vario-overview.md` § 6 (FR-10…FR-13, note FR-12 mock identity verification = employee ID + security question), § 7 (Reliability)
- `docs/PRD.md` § Open questions (resolved: password-reset identity check)
- `.env.example` (`MOCK_ITSM_URL`)

## What to build
The Mock ITSM backend and the `ITSMAdapter`. Build the full method surface the IT vertical needs across Sprint 2–3, but this slice's acceptance focuses on **ticket status**; the create/verify/reset methods exist for `slice-19` / `slice-21`.

Deliverables:
- **Mock ITSM** — a FastAPI service at `MOCK_ITSM_URL`, pre-seeded with tickets (id, category, description, reporter, status) and employees with a stored **security question/answer** for identity verification.
- **`ITSMAdapter`** implementing: `get_ticket_status(ticket_id)`, `create_ticket(category, description, reporter)` → ticket id, `verify_identity(employee_id, answer)`, `reset_password(employee_id)`. Points at `MOCK_ITSM_URL`.
- **Typed errors** — unknown ticket id → not-found; mock down → typed "backend unavailable" error (graceful, prompt).

## Acceptance criteria
- [ ] Given the Mock ITSM, when it starts, then it is seeded with several tickets and employees-with-security-questions.
- [ ] Given a seeded `ticket_id`, when `get_ticket_status` is called, then it returns the ticket's status (and enough fields to render a status card).
- [ ] Given an unknown `ticket_id`, then the adapter returns a not-found result (no crash).
- [ ] Given the mock is down, then the adapter raises a typed "backend unavailable" error and returns promptly.
- [ ] Given the adapter, then `create_ticket`, `verify_identity`, and `reset_password` are implemented and callable (exercised end-to-end in `slice-19` / `slice-21`).

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Rasa wiring / chat cards (`slice-17`, `slice-20`).
- Ticket-creation dedupe logic (`slice-19`) and the password-reset conversation flow (`slice-21`) — the methods exist here; the flows are elsewhere.
- Other adapters and any real ITSM integration.

## Human review required?
No.
