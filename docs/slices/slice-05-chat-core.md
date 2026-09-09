# Slice 05 — chat-core

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 2 · **Module:** `session-manager` + `dialogue-router` + `response-renderer` (+ Chat View shell & message component library)

> This is the integration unblocker for the whole team — the role packs plug their cards into the component library this slice ships. Front-load it after `slice-04`.

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (`POST /api/chat`, chat-mode request/response, `session` object, error codes)
- `docs/ADD.md` → `session-manager`, `dialogue-router`, `response-renderer` modules + chat-mode flow diagram
- `docs/ui-reference.md` § 4 (Chat View layout, the 9 **bot message types**, states)
- `docs/vario-overview.md` § 6 (FR-1, FR-2, FR-4, FR-5)

## What to build
The conversation engine and the chat surface: load session state, route a message to the right Rasa instance, render the response from a stored variant, persist everything, and display it. Talk mode is a **later** slice — build chat mode only, but leave the `mode` field in place.

Deliverables:
- **session-manager** — load-or-create the `sessions` row for a conversation (`current_form`, `current_step`, `slots`, `expires_at`); Postgres is authoritative; update after every turn.
- **dialogue-router** — read `conversation.role_pack`, forward the message + session to the correct `RASA_*_URL`; pass the Rasa result to the renderer. No NLU logic of its own.
- **response-renderer** — given `template_key` + slot values, pick a **random** stored variant from `response_variants` and substitute placeholders.
- **`POST /api/chat`** (chat mode) — persist the user message → route → Rasa (adapter calls happen inside Rasa custom actions, not here) → render → persist the bot message → update session → return `{response_text, intent, confidence, entities, session}`. Below-confidence-threshold → a **clarification** prompt, not a workflow (FR-2). Log every classification/routing decision (FR-5).
- **Chat View shell** — header (role-pack + title), scrollable thread (user right / bot left with avatar), input bar (text + send). States: active, loading ("thinking" indicator), empty, connection error.
- **Shared message component library** — generic, props-driven components for every bot message type in `ui-reference.md`: plain text, data card, slot prompt (option buttons), confirmation (confirm/cancel), result (reference ID), not-found (warning), FAQ answer, error, list. Role packs compose these; they are not role-specific.

## Acceptance criteria
- [ ] Given a message in a conversation the caller owns, when `POST /api/chat` (chat mode) runs, then it returns `200` with `response_text`, `intent`, `confidence`, `entities`, and `session {current_form, current_step, slots}`.
- [ ] Given a non-owner, then `403`; a missing conversation, then `404`; a missing `message`, then `422`.
- [ ] Given a multi-turn exchange, then session slots persist across turns in Postgres (FR-4).
- [ ] Given a message whose top intent is below the confidence threshold, then the bot returns a clarification prompt rather than executing a workflow (FR-2).
- [ ] Given any message, then the classification + routing decision is written to the log (FR-5).
- [ ] Given a conversation's `role_pack`, then the router forwards to the matching Rasa instance and no other.
- [ ] Given a `template_key` with variants, then the renderer returns one variant at random with slot values substituted.
- [ ] Given the component library in Storybook, then all 9 bot message types render from props.
- [ ] Given the Chat View, then it renders active, loading, empty, and error states.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Talk mode / TTS (`slice-06`) — but keep the `mode` field and don't hardcode chat-only into the contract.
- Role-specific card *content* (HR/IT/Admissions owners compose the library components in their read-flow slices).
- Admin console.

## Human review required?
No.
