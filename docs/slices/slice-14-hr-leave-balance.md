# Slice 14 — hr-leave-balance

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 2 · **Module:** HR role pack (end-to-end feature)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (`POST /api/chat` response shape)
- `docs/ui-reference.md` § 4 → the **Data card** bot message type
- `docs/vario-overview.md` § 6 (FR-6), § 8 (UC-1)
- Depends on: `slice-05-chat-core` (component library), `slice-12-hr-rasa`, `slice-13-hrms-adapter`

## What to build
The first fully working HR thread: an employee asks for their leave balance in natural language and gets a data card back — routed all the way through the live pipeline. This connects `slice-12` and `slice-13` through `chat-core`.

Deliverables:
- Complete `action_check_leave_balance` in Rasa-HR so it calls `HRMSAdapter.get_leave_balance`, fills slots, and returns the leave-balance `template_key` + slot values.
- Seed the leave-balance `response_template` + variants (base text using placeholders like `{total}`, `{casual}`, `{sick}`, `{earned}`).
- An HR **leave-balance data card** — composing the shared data-card component from `slice-05` — showing total plus the per-type breakdown.
- Verify the full path: gateway → chat-core → dialogue-router → Rasa-HR → HRMSAdapter → Mock HRMS → response-renderer → card, in the deployed app.

## Acceptance criteria
- [ ] Given a logged-in employee in an HR conversation, when they ask for their leave balance in natural language, then a data card renders showing total + casual/sick/earned breakdown.
- [ ] Given the bot response, then the persisted bot message records `intent_name = check_leave_balance` and a `confidence`.
- [ ] Given an employee with no HRMS record, then the bot returns a graceful message (no crash, no empty card).
- [ ] Given the response variants, then repeated asks vary the wording (renderer picks a random variant).
- [ ] Given a merge to `main`, then the working flow is visible in the deployed app.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — use the **data card** example (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Leave-request submission / the multi-turn form (`slice-15`).
- Policy FAQ (`slice-16`).
- Voice / talk mode.

## Human review required?
No.
