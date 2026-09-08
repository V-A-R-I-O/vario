# Slice 04 — conversation-store

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 2 · **Module:** `conversation-store` (+ Home & New Conversation pages)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Conversations (`GET`/`POST /api/conversations`, `GET /api/conversations/:id/messages` — params, envelopes, `last_message_preview`, error codes)
- `docs/ADD.md` → `conversation-store` module + `conversations` / `messages` entities
- `docs/ui-reference.md` § 2 (Home / Conversation List) and § 3 (New Conversation)

## What to build
Durable conversation + message history and the two pages that sit in front of it. Scoped to the **caller's own** conversations (admin-wide logs are `slice-11`, a different endpoint).

Deliverables:
- **`GET /api/conversations`** — list the caller's conversations, most recent first; optional `role_pack` / `status` filters; each item includes `title`, `last_message_preview`, `last_message_at`, `status`, `role_pack`.
- **`POST /api/conversations`** — create with `role_pack` (required) and optional `title`; auto-generate a placeholder title when omitted; `201`; `422` on invalid `role_pack`.
- **`GET /api/conversations/:id/messages`** — owner-only; `limit`/`before` pagination; `403` if not owner, `404` if missing.
- **Home page** — sidebar list (role-pack badge, title, last-message preview, relative timestamp), prominent "New Conversation" button, empty state, loading state.
- **New Conversation page/modal** — three role-pack cards (HR / IT Support / Admissions) with icon + description; clicking one creates a conversation and navigates to the Chat View (the chat shell may be a stub until `slice-05`).

## Acceptance criteria
- [ ] Given a logged-in user, when they `GET /api/conversations`, then only their own conversations are returned, most recent first, each with `last_message_preview` and `last_message_at`.
- [ ] Given `role_pack`/`status` query params, then the list is filtered accordingly.
- [ ] Given `POST /api/conversations` with a valid `role_pack`, then `201` and a conversation is created; with an invalid `role_pack`, then `422`.
- [ ] Given no `title`, when creating, then a placeholder title is auto-generated.
- [ ] Given `GET /api/conversations/:id/messages` as the owner, then `200` with messages; as a non-owner, then `403`; for a missing id, then `404`.
- [ ] Given the Home page, then it renders loaded, empty, and loading states per the mockup.
- [ ] Given the New Conversation page, when a role-pack card is clicked, then a conversation is created and the app navigates to the Chat View.

## Mockup / reference (if UI-facing)
`docs/design/home-conversation-list.html` and `docs/design/new-conversation.html` (match `docs/ui-reference.md` §2, §3).

## Out of scope for this slice
- Sending messages / the chat pipeline / rendering bot message types (`slice-05`).
- Admin-wide conversation logs (`slice-11`).
- Talk mode.

## Human review required?
No.
