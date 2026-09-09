# Slice 26 — adm-fee-deadline

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 3 · **Module:** Admissions role pack (end-to-end feature)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat
- `docs/ui-reference.md` § 4 → **FAQ answer** / **Data card** bot message types
- `docs/vario-overview.md` § 6 (FR-16), § 8 — US-4
- Depends on: `slice-05-chat-core`, `slice-22-adm-rasa`, `slice-23-adm-adapter` (`get_calendar`)

## What to build
Fee and deadline answers sourced from the single configurable admissions calendar (FR-16) — so updating the calendar updates the answers.

Deliverables:
- A Rasa-Admissions intent `ask_fee_deadline` that resolves fee and deadline questions.
- Custom action calling `AdmissionsAdapter.get_calendar()` and answering from it; response templates for fee/deadline answers.
- Confirm the calendar is the single source (the seed lives in Mock Admissions, `slice-23`); no fee/deadline data hardcoded in Rasa.

## Acceptance criteria
- [ ] Given a fee question, when asked in an Admissions conversation, then the bot returns the fee from the calendar.
- [ ] Given a deadline question, then the bot returns the relevant deadline from the calendar.
- [ ] Given a change to the calendar (in Mock Admissions), then the bot's answers change accordingly (single configurable source).
- [ ] Given a low-confidence question, then the bot asks for clarification rather than guessing.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **FAQ answer** / **data card** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Application status (`slice-24`) and document checklist (`slice-25`).
- Voice / talk mode.

## Human review required?
No.
