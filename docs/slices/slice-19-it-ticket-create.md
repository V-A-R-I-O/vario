# Slice 19 — it-ticket-create

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 3 · **Module:** IT role pack (multi-turn write workflow + dedupe)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (session / slots)
- `docs/ui-reference.md` § 4 → **Slot prompt**, **Confirmation**, **Result** bot message types
- `docs/vario-overview.md` § 6 (FR-10, FR-13), § 7 (Safety: confirmation + audit), § 8 (UC-3)
- Depends on: `slice-05-chat-core`, `slice-18-itsm-adapter` (`create_ticket`), `slice-20-it-ticket-status`

## What to build
The guided ticket-creation workflow, with duplicate suppression for an immediately-repeated identical request in the same session (FR-13).

Deliverables:
- A Rasa-IT form for `raise_ticket` collecting slots: `category`, `description` (reporter comes from the authenticated user context).
- A **confirmation step** (summary + Confirm / Cancel) before creating the record (NFR safety).
- On Confirm: call `ITSMAdapter.create_ticket`, return the ticket ID in a **result** card; fire an audit event (`ticket_created`).
- **Dedupe (FR-13):** record a signature of the just-created ticket in the session; if an identical request is immediately repeated in the same session, return the existing ticket instead of creating a new one.

## Acceptance criteria
- [ ] Given an issue description, when the workflow runs, then it collects `category` and `description` across turns.
- [ ] Given all slots filled, then a confirmation with Confirm / Cancel is shown before creation.
- [ ] Given Confirm, then a ticket is created via the adapter, its ID is shown in a result card, and an `audit_log` entry (`ticket_created`) is written.
- [ ] Given an identical create request immediately repeated in the same session, then no second ticket is created — the existing ticket is returned (FR-13).
- [ ] Given Cancel, then no ticket is created.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **slot prompt** + **confirmation** + **result** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Ticket status (`slice-20`) and password reset (`slice-21`).
- Voice / talk mode.

## Human review required?
No.
