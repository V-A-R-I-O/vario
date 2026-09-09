# Slice 30 — vercel-neon

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 1 · **Module:** infra (frontend hosting + database)

## References — read these first
- `AGENTS.md` (human review required for infra + secrets)
- `docs/ADD.md` § Stack (Frontend hosting: Vercel; Database: PostgreSQL via Neon serverless free tier)
- `.env.example` (`DATABASE_URL`, `NEXT_PUBLIC_API_BASE_URL`)
- Coordinates with `slice-02-db-schema` (which migrates against the Neon DB this provisions), `slice-28-cicd`, and `slice-29-oci-cloudflare` (the backend URL the frontend points at)

## What to build
The frontend host and the database: a Vercel project for the Next.js app and a Neon Postgres project (dev + prod), with all environment/secret wiring in place so the app and migrations connect cleanly.

Deliverables:
- **Vercel project** linked to the repo, configured with `NEXT_PUBLIC_API_BASE_URL` pointing at the Cloudflare-tunneled backend URL (from `slice-29`).
- **Neon project** with separate **dev** and **prod** databases (or branches), and their connection strings.
- **Env wiring**: `DATABASE_URL` supplied to the backend (via OCI env / GitHub Actions secrets) and available to migrations (`slice-02`); Vercel env vars set for the frontend.
- Confirm `.env.example` lists every variable this introduces; add any missing ones.

## Acceptance criteria
- [ ] Given the Vercel project, when the frontend is deployed, then it loads at a Vercel URL and successfully calls the backend over HTTPS.
- [ ] Given Neon, then a **dev** and a **prod** database exist, each with a connection string.
- [ ] Given the connection strings, then they are provided to the backend and to CI **only as secrets** (GitHub Actions secrets / Vercel env) — never committed.
- [ ] Given `slice-28-cicd`, then a merge to `main` auto-deploys the frontend to Vercel.
- [ ] Given `.env.example`, then it accurately reflects every env var required to run the frontend and connect to Neon.

## Mockup / reference (if UI-facing)
No UI surface (this provisions hosting; it does not build pages).

## Out of scope for this slice
- Backend hosting / Cloudflare Tunnel (`slice-29`).
- The database **schema** and migrations (`slice-02`) — this slice creates the empty Neon DBs and hands over the connection string.
- The CI/CD workflow definitions (`slice-28`).

## Human review required?
**Yes** — infrastructure provisioning and secrets. Do not merge/deploy without human review (per `AGENTS.md`).
