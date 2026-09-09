# Slice 11 — conversation-logs

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 4 · **Module:** `conversation-store` (admin read) + Conversation Logs page

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Admin — Conversation Logs (`GET /api/admin/conversations`, `GET /api/admin/conversations/:id/messages` — scoping, filters, transcript shape, error codes)
- `docs/ADD.md` → `conversation-store` module + § Security (role scoping)
- `docs/ui-reference.md` § 10 (Conversation Logs page)
- `docs/vario-overview.md` § 6 (FR-19)
- Depends on: `slice-04-conversation-store` (data), `slice-07-admin-shell` (admin authz + nav)

## What to build
The admin-facing, read-only view over conversations handled by the admin's role pack — the "where did the bot misunderstand?" tool. Distinct from the end-user `GET /api/conversations` (that's the caller's own; this is role-pack-wide, read-only).

Deliverables:
- **`GET /api/admin/conversations`** — role pack derived from the JWT; lists conversations in that pack with `user_name`, `user_email`, `title`, `message_count`, `last_intent`, `started_at`, `last_message_at`; filters `actor_id` / `from` / `to`; pagination.
- **`GET /api/admin/conversations/:id/messages`** — read-only transcript; each bot message carries `intent_name` + `confidence`; `403` if the conversation is in another role pack, `404` if missing.
- **Conversation Logs page** — list (user, started-at, message count, last intent) → click to expand the full transcript (read-only, chat styling), with each bot message showing detected intent + confidence; pagination.

## Acceptance criteria
- [ ] Given an admin, when they `GET /api/admin/conversations`, then only their role pack's conversations are returned, honouring filters and pagination.
- [ ] Given `GET /api/admin/conversations/:id/messages` for a conversation in the admin's pack, then the full transcript is returned with per-bot-message intent + confidence.
- [ ] Given a conversation in a different role pack, then `403`; a missing id, then `404`.
- [ ] Given a non-admin, then `403`.
- [ ] Given the Conversation Logs page, then the list renders and a row expands to a read-only transcript showing intent + confidence on bot messages; pagination works.
- [ ] This satisfies FR-19 (an admin can review their pack's conversation logs).

## Mockup / reference (if UI-facing)
`docs/design/admin-conversation-logs.html` (matches `docs/ui-reference.md` §10).

## Out of scope for this slice
- Any editing of conversations (strictly read-only).
- The audit log (`slice-07`) and the end-user conversation list (`slice-04`).

## Human review required?
No — read-only, and role-pack scoping is enforced by `slice-07`. Confirm the scoping holds during review (it exposes end-user conversation content to admins).
