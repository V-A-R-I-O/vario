# Slice 01 — auth-login

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 1 · **Module:** `auth` (+ Login page on the frontend)

## References — read these first
- `AGENTS.md` (branch/PR convention, human-review policy, secrets — do not commit secret values)
- `docs/decisions/ADR-001-delegated-auth.md` (why there is no registration / password reset / lockout)
- `docs/api-contract.md` § Auth → `POST /api/auth/login` (request/response envelope, JWT claims, 401)
- `docs/ADD.md` → `auth` module + `users` entity in the Data model
- `docs/ui-reference.md` § 1 (Login page: elements + states)
- `.env.example` (`JWT_SECRET`, `JWT_EXPIRY_MINUTES`, `MOCK_AUTH_URL`)

## What to build
Delegated authentication end-to-end: a Mock Auth Service standing in for the org's identity provider, an Auth Adapter in front of it, the login endpoint that issues VARIO's own JWT, and the Login page.

Deliverables:
- **Mock Auth Service** — a small FastAPI service (same pattern as the other mocks) pre-seeded with test users. Seed at least one `end_user` (an employee) and one admin for each role pack (`hr_admin`, `it_admin`, `admissions_admin`). Each user has `email`, `password`, `full_name`, `role`, `external_id`. Exposes a verify-credentials endpoint.
- **Auth Adapter** (`AuthAdapter.authenticate(email, password)`) — the only code that knows it's talking to the mock; returns the user record on success, `None` on failure. Points at `MOCK_AUTH_URL`.
- **`POST /api/auth/login`** — validates via the adapter; on success **upserts** the `users` table (create on first login, update thereafter), issues a signed JWT with `{user_id, role, email}` claims (expiry from `JWT_EXPIRY_MINUTES`), and returns the standard envelope with `token` + user fields. Returns `401` on invalid credentials.
- **JWT helpers** — `issue_token(user)` and `verify_token(token)` (verify will be consumed by the gateway middleware in a later slice; just export it here).
- **Login page** (Next.js) — email + password fields, "Log in" button, the plain-text line "Forgot your password? Contact your administrator.", VARIO branding. On success, store the JWT and redirect to the (empty for now) Home route. States: default, loading, error.

## Acceptance criteria
- [ ] Given a seeded user, when `POST /api/auth/login` is called with correct credentials, then it returns `200` with `{status:"success", data:{user_id, email, full_name, role, external_id, token}, error:null}`.
- [ ] Given wrong credentials, when login is called, then it returns `401` with `{status:"error", data:null, error:<message>}`.
- [ ] Given a user's first-ever login, when it succeeds, then exactly one row is created in `users` with their `external_id`, `email`, `full_name`, `role`.
- [ ] Given a user who has logged in before, when they log in again, then their `users` row is updated in place (no duplicate row).
- [ ] Given a successful login, when the returned JWT is decoded, then it contains `user_id`, `role`, and `email`, and is rejected by `verify_token` once past `JWT_EXPIRY_MINUTES`.
- [ ] Given the Mock Auth Service, when it starts, then it is pre-seeded with ≥1 `end_user` and one admin per role pack (`hr_admin`, `it_admin`, `admissions_admin`).
- [ ] Given the Login page with valid credentials, when the user submits, then a loading state shows and the app redirects to Home on success.
- [ ] Given invalid credentials, when the user submits, then "Invalid email or password" is shown. There is **no** "account locked" state.

## Mockup / reference (if UI-facing)
`docs/design/login.html` — HTML mockup for the Login page (to be added by the design workstream; matches `docs/ui-reference.md` §1). Build to the mockup when present; otherwise implement the elements/states listed above.

## Out of scope for this slice
- User registration, email verification, password reset, account lockout (all the org's responsibility per ADR-001).
- Real identity-provider integration (mock only).
- Protected-route JWT middleware and rate limiting (that's `slice-03-gateway-envelope`).
- Sessions, conversations, chat.

## Human review required?
**Yes** — this is authentication. Do not merge without human review (per `AGENTS.md`).
