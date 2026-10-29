# Slice 37 — it-real-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B (Rohith) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** IT role pack — Rasa runtime, forms, actions · **Story points:** 8

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docs/slices/slice-17-it-rasa.md`
- `docs/slices/slice-19-it-ticket-create.md`
- `docs/slices/slice-20-it-ticket-status.md`
- `docs/slices/slice-21-it-password-reset.md`
- `rasa-it/`
- Depends on: ADR-006 from slice-32 (start NLU/domain/forms on day 1).

## Dev environment
Rohith — laptop D (Windows 10, 8 GB, 20 GB free, **no Docker**). Work natively: Python 3.10 venv, `pip install rasa==3.6.20 rasa-sdk==3.6.2` (~3 GB), then run `rasa run` and `rasa run actions` locally. Integrate on laptop C over the LAN. Don't install Docker Desktop on this machine.

## What to build
- Replace `rasa-it/server.py` with a **Rasa 3.6.20 project** (DIET + FallbackClassifier 0.4; use the existing nlu, domain, rules and stories as the base).
- Forms, with cancel and interruptions at any step:
  - `ticket_status_form` (ticket_id)
  - `raise_ticket_form` (category, description → confirm)
  - `reset_password_form` (employee_id, security answer)
- Action server (Python 3.10, rasa-sdk pinned to 3.6.x) using `rasa-it/actions/itsm_adapter.py`. Remove the unused backend copy of the ITSM adapter.
- Keep what works:
  - FR-13 duplicate suppression
  - The reporter comes from `metadata.auth_context`
  - The security answer is never stored: set `sensitive_next_input` when asking for it (ADR-006)
- Limit reset attempts per employee across restarts (e.g. lock out in mock-itsm after 3 failures).
- Put the ticket ID in the "ticket created" text. "check my ticket status" without an ID asks for one.
- Each lookup returns only its own result — never the previous ticket's status.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| M3b | Major | Ticket-ID prompt traps the user; even 'cancel' is rejected |
| M4c | Major | Ticket status questions start a new ticket instead |
| B5c | Major | IT replies carry the previous ticket's status, so cards show the wrong ticket |
| M2b | Minor | Password-reset retry limit resets when the flow restarts (unlimited guesses) |
| N9 | Minor | 'Ticket created' reply has no ticket ID; 'check my ticket status' reuses the last ID |
| N10 | Minor | IT pack runs on the wrong Python for Rasa, with unpinned deps and a duplicate adapter |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given the ticket-ID prompt, when the user says "cancel" or asks something else, then the prompt ends or the new intent is handled.
- [ ] Given "Is my ticket still open?" or "status of the ticket I submitted", then it's classified as check_ticket_status.
- [ ] Given a lookup of one ticket then another (and with mock-itsm down), then each card shows only its own ticket or a clear error.
- [ ] Given 3 wrong security answers, then restarting the flow does not allow more guesses.
- [ ] Given a created ticket, then the reply text contains the ticket ID.
- [ ] Given an identical repeated request, then FR-13 still returns the existing ticket, and the security answer never appears in messages, sessions, responses or logs.
- [ ] Given `rasa data validate`, then it passes, and the existing IT tests are ported to the new runtime.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Ticket ID format and mock-itsm seed data (slice-38).
- CI (slice-38).

## Human review required?
No — but the reviewer confirms no real credential handling was introduced.
