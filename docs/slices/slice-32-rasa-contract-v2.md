# Slice 32 — rasa-contract-v2

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D (Tahir) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** Core engine — gateway, dialogue-router, session-manager · **Story points:** 5

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/overview.md` § 6–7 (FRs and NFRs this contract must satisfy)
- `docs/decisions/ADR-002-rasa-chat-contract.md`
- `docs/api-contract.md § POST /api/chat`
- `backend/app/routers/chat.py`
- `backend/app/services/dialogue_router.py`
- `backend/app/services/session_manager.py`
- Depends on: Nothing — this slice goes first. ADR-006 must be merged on day 1, because slices 33, 35, 37 and 39 build against it.

## Dev environment
Tahir — laptop A (M1, 8 GB). Backend work runs natively; no Rasa needed (use the contract fixture).

## What to build
- **ADR-006 — Rasa converse contract v2** (freeze on day 1). It must pin down:
  - Request: `POST {RASA_*_URL}/webhooks/vario/converse` with `sender` = **conversation_id** (one Rasa tracker per conversation), `message`, and `metadata.auth_context` = `{employee_id, full_name, role}` from the authenticated user — never from chat text.
  - Response: the ADR-002 fields plus `card` (this turn's card payload or `null`) and `sensitive_next_input` (true when the next user message must be redacted, e.g. a security answer). `slots` carries only this turn's template values.
  - How the custom Rasa input channel builds the response: intent/confidence from `latest_message`, `active_loop` → `current_form`, `requested_slot` → `current_step`, collected text and JSON messages → `response_text` / `template_key` / `card` / `audit_event`.
  - Where dialogue state lives: Rasa SQL tracker store in the stack's Postgres (survives restarts); the gateway `sessions` row becomes a mirror.
  - Examples for a form turn, a card turn and a degraded turn.
- **Shared Rasa input channel module** — one copy used by all three packs (mounted or copied at build; ADR decides), plus a contract test fixture packs and the frontend can test against.
- **Gateway changes:**
  - Send conversation_id as `sender` and the identity in `metadata`.
  - Store the session mirror exactly as returned (stop the endless slot merge).
  - Persist each bot message's `card` (Alembic migration: JSON column on `messages`) and return it from `/api/chat` and message history.
  - Skip the FR-2 clarification override while a form is active.
  - Redact the next user message when `sensitive_next_input` was set (replaces the hard-coded IT form/step check).
  - Rasa instance unreachable/erroring → HTTP 200 with a friendly role-pack-specific bot reply and `degraded: true`; keep the user's message.
  - Unhandled 500s carry CORS headers.
  - Enforce or remove `sessions.expires_at` (ADR decides).
- Update `docs/api-contract.md` for the new optional fields.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B5a | Blocker | Session slots accumulate forever; every reply returns all past values |
| M6 | Major | Role-pack outage returns HTTP 500, loses the user's message and has no CORS header |
| N1 | Trivial | sessions.expires_at is written but never enforced |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given ADR-006 is merged, then it specifies the exact request/response JSON with examples for a form turn, a card turn and a degraded turn.
- [ ] Given any chat turn, then the role pack receives `sender` = conversation_id and `metadata.auth_context.employee_id` equal to the logged-in user's `external_id`.
- [ ] Given a turn whose response omits a key used in an earlier turn, then `/api/chat` `session.slots` does not contain the earlier value.
- [ ] Given a bot reply with a card, when the conversation history is fetched, then the same card is returned for that message.
- [ ] Given an active form and a low-confidence user reply, then the role pack's reply is returned (no clarification override).
- [ ] Given `sensitive_next_input` was true on the previous reply, then the user's next message is stored redacted, and the existing IT redaction tests still pass.
- [ ] Given a role pack is down, when a user sends a message, then the API returns 200 with a friendly degraded reply, the user message is persisted, and the response has CORS headers.
- [ ] Given an unhandled exception, then the 500 response includes CORS headers.
- [ ] Given the backend suite, then all tests pass and new tests cover each criterion above.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Role-pack NLU, forms and actions (slices 35/37/39).
- Frontend card rendering (slice-33).
- Docker Compose (slice-34).

## Human review required?
Yes — adds a DB migration and changes how the logged-in identity is passed to role packs.
