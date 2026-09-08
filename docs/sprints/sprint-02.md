# Sprint 2 — Role Packs & Read Flows (Weeks 2–3)

## Goal
With the pipeline live, build the first real vertical: stand up all three Rasa role packs and ship an end-to-end **read/lookup** flow for each (leave balance, ticket status, application status), rendered as proper chat cards. Because CD is already running, each flow **auto-deploys the moment it merges** — the demo app grows continuously through the sprint.

## Exit criteria
- [ ] Each of Rasa-HR / IT / Admissions classifies its lookup intent and calls its integration adapter → mock service.
- [ ] A user logs in, starts a conversation (HR/IT/Admissions), sends a message via `POST /api/chat`, and gets a data card back — end-to-end through the gateway.
- [ ] `check_leave_balance` (HR), `check_ticket_status` (IT), `check_application_status` (Admissions) all work in the deployed app.
- [ ] Admissions returns a graceful "not found" for an unknown application ID (FR-17).
- [ ] Session state (form/step/slots) persists to Postgres across turns; every classification is logged (FR-5).

## Per-member lanes

| Member | Slices | Focus |
|---|---|---|
| **D** | `slice-03-gateway-envelope`, `slice-04-conversation-store`, `slice-05-chat-core` | Full gateway (JWT mw, envelope, rate limit); conversations + Home/New-Conversation UI; **chat-core** (session/router/renderer + `/api/chat` + chat shell + shared message component library) |
| **A** | `slice-12-hr-rasa`, `slice-13-hrms-adapter`, `slice-14-hr-leave-balance` | Rasa-HR + `check_leave_balance`; HRMS mock + `get_leave_balance()`; leave-balance card end-to-end |
| **B** | `slice-17-it-rasa`, `slice-18-itsm-adapter`, `slice-20-it-ticket-status` | Rasa-IT + `check_ticket_status`; ITSM mock + `get_ticket_status()`; status card + invalid-ID guidance |
| **C** | `slice-22-adm-rasa`, `slice-23-adm-adapter`, `slice-24-adm-app-status` | Rasa-Admissions + `check_application_status`; Admissions mock + adapter; status card + not-found |

## Dependencies & sequencing
- This is the **densest sprint for A/B/C** (Rasa + adapter + read-flow each) — a direct consequence of infra-first. Keep each Rasa instance to its one lookup intent; accuracy tuning and extra intents come later.
- A/B/C build their Rasa + adapter + mock as standalone services (curl-testable) and their card component in Storybook against the frozen `docs/api-contract.md` in Week 2, then wire to D's `chat-core` in Week 3.
- **`slice-05-chat-core` is the unblocker** — D front-loads it (after `conversation-store`) so integration lands mid-to-late Week 3. Hold an end-of-Week-2 integration checkpoint (chat-core + one role pack).

## Risks / de-risking
- **Rasa learning curve + sprint density** is the combined risk. If a role pack slips, ship two read-flows in the deployed app and carry the third into early Sprint 3 rather than faking integration.
- Keep component-library props aligned to the chat response shape in `docs/api-contract.md` to avoid rework at integration.

## Human review
- None required this sprint (no auth/infra/schema/secrets changes). Standard PR review applies.
