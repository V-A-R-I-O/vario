# Slice 03 — gateway-envelope

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 2 · **Module:** `gateway`

## References — read these first
- `AGENTS.md` (human review required for auth/authz changes; secrets)
- `docs/api-contract.md` § top (envelope shape + `Authorization: Bearer` + JWT payload), § Error Response Format (status codes), § Rate Limiting (per-group limits + headers)
- `docs/ADD.md` → `gateway` module (single entrypoint, no business logic)
- `slice-01-auth-login` (reuse its `verify_token` helper)

## What to build
The FastAPI API Gateway: the single HTTP entrypoint that wraps every response in the standard envelope, enforces JWT auth on protected routes, validates request schemas, and rate-limits per user/IP. **No business logic** — it dispatches to the feature modules.

Deliverables:
- **Envelope wrapper** — every response (success and error) is shaped `{status, data, error}`.
- **JWT auth middleware** — verifies the Bearer token on protected routes via `verify_token`; on success attaches `{user_id, role, email}` to the request context; `401` on missing/invalid. The login route stays public.
- **Error handling** — maps exceptions to the documented HTTP codes (`400/401/403/404/409/422/429/500`), each in the envelope.
- **Request validation** — Pydantic models → `422` with envelope on malformed bodies.
- **Rate limiting** per the api-contract table: `/api/auth/*` 10/min per IP, `/api/chat` 30/min per user, `/api/conversations/*` 60/min per user, `/api/admin/*` 30/min per user, `/api/admin/retrain` 3/hour per user. `429` + `X-RateLimit-Limit/Remaining/Reset` headers.
- Integrate the existing `POST /api/auth/login` (slice-01) under the envelope + rate limiting.
- A `/health` endpoint.

## Acceptance criteria
- [ ] Given any endpoint, when it responds, then the body is `{status, data, error}`.
- [ ] Given a protected route with no/invalid JWT, then it returns `401` in envelope form.
- [ ] Given a valid JWT, when a protected route runs, then `user_id`, `role`, and `email` are available to the handler.
- [ ] Given a malformed request body, then the gateway returns `422` in envelope form.
- [ ] Given more requests than an endpoint group's limit, then it returns `429` with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers.
- [ ] Given `/api/auth/login`, then it requires no auth and is limited to 10/min per IP.
- [ ] The gateway contains no business logic — only validation, auth, rate limiting, envelope, and dispatch.

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Chat, conversation, and admin business logic (their own slices) — just wire the routing/middleware.
- Role-based authorization checks on admin routes (added with the admin slices in Sprint 3).
- TTS / talk mode.

## Human review required?
**Yes** — establishes the JWT authorization-enforcement layer. Do not merge without human review (per `AGENTS.md`).
