# Slice 15 — hr-leave-request

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 3 · **Module:** HR role pack (multi-turn write workflow)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (session / slots / multi-turn)
- `docs/ui-reference.md` § 4 → **Slot prompt**, **Confirmation**, **Result** bot message types
- `docs/vario-overview.md` § 6 (FR-8, FR-9), § 7 (Safety: no record-affecting action without explicit confirmation + audit), § 8 (UC-2)
- Depends on: `slice-05-chat-core`, `slice-13-hrms-adapter` (`submit_leave`), `slice-14-hr-leave-balance`

## What to build
The guided leave-request workflow: collect leave details across turns, confirm, submit, return a reference ID — and audit the action.

Deliverables:
- A Rasa-HR form for `submit_leave_request` collecting slots: `leave_type`, `start_date`, `end_date`, `reason`. Use option buttons (slot-prompt component) for `leave_type`; validate dates.
- A **confirmation step**: a summary card + Confirm / Cancel (no submission without explicit Confirm — NFR safety).
- On Confirm: call `HRMSAdapter.submit_leave`, get a reference ID, render a **result** card. Fire an audit event (`leave_submitted`, reference id, details).
- On Cancel: end the workflow cleanly, nothing submitted.

## Acceptance criteria
- [ ] Given a leave-request intent, when the workflow runs, then it collects `leave_type`, `start_date`, `end_date`, and `reason` across turns, with slots persisting.
- [ ] Given all slots filled, then a confirmation summary with Confirm / Cancel is shown before any submission.
- [ ] Given Confirm, then the leave is submitted via the adapter and a result card shows the returned reference ID.
- [ ] Given Cancel, then nothing is submitted and the workflow ends gracefully.
- [ ] Given a submission, then an `audit_log` entry (`leave_submitted`, actor, reference id, details) is written (FR-9, safety NFR).

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **slot prompt** + **confirmation** + **result** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Leave balance (`slice-14`) and policy FAQ (`slice-16`).
- Voice / talk mode.
- Admin editing of this workflow's response text (that happens via the admin console, `slice-08`).

## Human review required?
No.
