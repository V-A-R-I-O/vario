# Slice 20 — it-ticket-status

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 2 · **Module:** IT role pack (end-to-end feature)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (response shape)
- `docs/ui-reference.md` § 4 → **Data card** and **Not found** bot message types
- `docs/vario-overview.md` § 6 (FR-11), § 8 (UC-4)
- Depends on: `slice-05-chat-core`, `slice-17-it-rasa`, `slice-18-itsm-adapter`

## What to build
The first fully working IT thread: a user asks for the status of a ticket by ID and gets a status card — or clear guidance when the ID is invalid. Connects `slice-17` and `slice-18` through `chat-core`.

Deliverables:
- Complete `action_check_ticket_status` in Rasa-IT so it reads the `ticket_id` entity, calls `ITSMAdapter.get_ticket_status`, and returns the ticket-status `template_key` + slots.
- Seed the ticket-status `response_template` + variants using `{ticket_id}` / `{status}` placeholders.
- An IT **ticket-status card** composing the shared data-card component; plus wiring the **not-found** component for an invalid/unknown ticket id.
- Verify the full path in the deployed app.

## Acceptance criteria
- [ ] Given a logged-in user in an IT conversation, when they ask for the status of a valid ticket id, then a status card renders with the ticket id and status.
- [ ] Given an unknown/invalid ticket id, then the bot returns a not-found message with guidance (not an error/crash) (FR-11).
- [ ] Given the bot response, then the persisted bot message records `intent_name = check_ticket_status` and a `confidence`.
- [ ] Given repeated asks, then wording varies (renderer picks a random variant).
- [ ] Given a merge to `main`, then the working flow is visible in the deployed app.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **data card** + **not found** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Ticket creation + duplicate suppression (`slice-19`).
- Password reset (`slice-21`).
- Voice / talk mode.

## Human review required?
No.
