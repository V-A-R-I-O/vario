# Slice 13 — hrms-adapter

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 2 · **Module:** `integration-adapters` (HRMS) + Mock HRMS service

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `integration-adapters` module (common interface; the only code that knows it's a mock; swappable later) + § Reliability (graceful degradation if a mock is down)
- `docs/vario-overview.md` § 6 (FR-6, FR-8, FR-9) and § 7 (Reliability)
- `.env.example` (`MOCK_HRMS_URL`)

## What to build
The Mock HRMS backend and the `HRMSAdapter` in front of it — the swappable seam between the HR role pack and "the HR system." Only the adapter knows it's talking to a mock.

Deliverables:
- **Mock HRMS** — a FastAPI service at `MOCK_HRMS_URL`, pre-seeded with employees, per-type leave balances (casual / sick / earned), leave records, and a small set of HR policies. Endpoints for: leave balance, leave status, submit leave (returns a reference ID), policy lookup.
- **`HRMSAdapter`** implementing the common interface: `get_leave_balance(employee_id)`, `get_leave_status(employee_id)`, `submit_leave(employee_id, type, start, end, reason)`. Points at `MOCK_HRMS_URL`.
- **Typed errors** — unknown employee → a not-found result; mock unreachable → a typed "backend unavailable" error the caller can degrade on (never hang/crash).
- Optional: an artificial delay flag on the mock to exercise the "excluding mock API delays" performance carve-out.

## Acceptance criteria
- [ ] Given the Mock HRMS, when it starts, then it is seeded with several employees each having casual/sick/earned balances.
- [ ] Given a seeded `employee_id`, when `get_leave_balance` is called, then it returns a structured balance (total + per-type breakdown).
- [ ] Given an unknown `employee_id`, then the adapter returns a not-found result (not an exception that crashes the caller).
- [ ] Given the mock service is down, when the adapter is called, then it raises a typed "backend unavailable" error and returns promptly.
- [ ] Given the adapter interface, then no code outside the adapter references mock-specific details (swappable to a real HRMS later).

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Rasa wiring / the chat card (`slice-12`, `slice-14`).
- The leave-request confirmation flow UI (`slice-15`) — `submit_leave` exists here but is exercised there.
- Other adapters (ITSM, Admissions, Auth) and any real HRMS integration.

## Human review required?
No.
