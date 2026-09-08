# Slice 21 — it-password-reset

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 3 · **Module:** IT role pack (guided flow + mock identity verification)

## References — read these first
- `AGENTS.md`
- `docs/PRD.md` § Open questions (resolved: identity check = employee ID + security question against Mock ITSM)
- `docs/vario-overview.md` § 6 (FR-12), § 7 (Safety), § 8 — US-3
- `docs/ui-reference.md` § 4 → **Slot prompt**, **Result**, **Error** bot message types
- Depends on: `slice-05-chat-core`, `slice-18-itsm-adapter` (`verify_identity`, `reset_password`)

## What to build
A guided password-reset flow with a mocked identity-verification gate. This simulates an ITSM workflow — it is **not** VARIO's own authentication (VARIO delegates real auth per ADR-001). No real credentials are involved; verification is against Mock ITSM seed data.

Deliverables:
- A Rasa-IT flow for `reset_password`: collect the `employee_id`, then ask the user's stored **security question** and collect the answer.
- Call `ITSMAdapter.verify_identity(employee_id, answer)`.
- On success: call `ITSMAdapter.reset_password(employee_id)`, render a **result** message (reset initiated), and fire an audit event (`password_reset_initiated`).
- On failure: do **not** trigger a reset; render an **error/denied** message with guidance; allow a bounded number of retries.

## Acceptance criteria
- [ ] Given a reset-password intent, when the flow runs, then it asks for the `employee_id` and then the security question.
- [ ] Given the correct security answer, then identity is verified, the reset is triggered, a result message shows, and an `audit_log` entry (`password_reset_initiated`) is written.
- [ ] Given an incorrect answer, then the reset is **not** triggered and the user is informed (with bounded retries).
- [ ] Given the flow, then a reset can only fire after a successful verification (safety).
- [ ] Given the implementation, then no real credential/password value is stored or logged — only mock ITSM interactions.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **slot prompt** + **result** + **error** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Ticket create (`slice-19`) and status (`slice-20`).
- Any real password/identity system (mock only).
- Voice / talk mode.

## Human review required?
No — this is a mock ITSM workflow, not VARIO's real auth. But during review, confirm no real credential handling was introduced.
