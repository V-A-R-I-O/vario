# Slice 27 — docker-compose

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 1 · **Module:** infra (local dev)

## References — read these first
- `AGENTS.md` (don't scaffold CI/release pipelines here — this is local dev only)
- `docs/ADD.md` § Stack + System layers (the services that must exist: frontend, gateway, 3 Rasa, 4 mocks, Postgres)
- `.env.example` (all service URLs/ports are defined here — Compose consumes them)

## What to build
A `docker-compose.yml` that brings the whole stack up locally with one command, so every developer runs the same environment. Week-1 reality: several services are still stubs — Compose should define them anyway so they slot in as they land.

Deliverables:
- `docker-compose.yml` defining services: `frontend` (Next.js), `gateway` (FastAPI backend), `rasa-hr`, `rasa-it`, `rasa-admissions`, `mock-auth`, `mock-hrms`, `mock-itsm`, `mock-admissions`, `postgres`.
- `Dockerfile` for the frontend and the backend at minimum. Rasa and mock services may reference placeholder/stub images or build contexts that role owners flesh out.
- Env wiring: services read from `.env` (ports and URLs matching `.env.example`).
- A short "Local development" section in `README.md` documenting `docker compose up` and the ports.

## Acceptance criteria
- [ ] Given a checkout and a populated `.env`, when a developer runs `docker compose up`, then Postgres, the backend, and the frontend start and stay healthy.
- [ ] Given the compose stack, then the backend connects to `postgres` via `DATABASE_URL` and the frontend reaches the backend via `NEXT_PUBLIC_API_BASE_URL`.
- [ ] Given the compose file, then all stack services (3 Rasa + 4 mocks) are declared (stub images allowed) so they can be filled in without editing topology later.
- [ ] Given the compose file, then no secret values are hardcoded — everything comes from `.env` (which is gitignored).
- [ ] Given `README.md`, then it documents how to boot the stack and which port each service uses.

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Production orchestration on OCI (that's `slice-29-oci-cloudflare`).
- CI/CD (that's `slice-28-cicd`).
- Kubernetes / any non-Compose orchestrator.

## Human review required?
**Light** — this is infra config but local-only, with no secrets or deploy path. A quick teammate sanity-check of the compose file is enough (it doesn't gate a deploy).
