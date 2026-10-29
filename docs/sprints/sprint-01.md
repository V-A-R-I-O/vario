# Sprint 1 — Deployed Walking Skeleton & CD Pipeline (Week 1)

## Goal
Build and verify a minimal VARIO application locally: public landing page, login, authenticated shell, local PostgreSQL and a reliable pull-request CI pipeline. Docker Compose is the supported runtime. GitHub Actions validates changes; it does not deploy to cloud hosting.

## Exit criteria
- [ ] The VARIO landing page loads locally without authentication.
- [ ] A seeded test user logs in via `POST /api/auth/login` on the local URL and receives a valid VARIO JWT.
- [ ] Pushing a PR runs CI (lint + test + build); merging to main runs CI; cloud deployment is not required.
- [ ] The frontend can call the local gateway using the configured local API route.
- [ ] The 9-entity schema is migrated successfully on local PostgreSQL.
- [ ] `docker compose up` brings the stack up locally for every developer.
- [ ] A teammate can follow the README and Slice 34 runbook to start and verify the application locally.

## Per-member lanes

| Member | Slices | Focus |
|---|---|---|
| **D** | ⚠️`slice-01-auth-login`, ⚠️`slice-02-db-schema`, `slice-27-docker-compose` | Repo/monorepo scaffold (Next.js + FastAPI), auth + mock-auth + JWT + Login UI, schema/migrations, Docker Compose |
| **B** | ⚠️`slice-28-cicd` | GitHub Actions: lint + tests + builds on PRs and pushes |
| **A** | `slice-00-landing-page`, ⚠️`slice-29-oci-cloudflare` | Public VARIO landing page; Slice 29 cloud deployment is retired |
| **C** | ⚠️`slice-30-vercel-neon` | Slice 30 cloud deployment is retired; support local validation as agreed |

## Dependencies & sequencing
- **Provision accounts on day 1** (OCI, Cloudflare, Vercel, Neon, GitHub) — these have the longest lead time.
- `slice-00-landing-page` (A) can be developed independently of the backend and authentication because it is public and frontend-only.
- `slice-02-db-schema` (D) and `slice-30-vercel-neon` (C) coordinate on the connection string: D writes and runs migrations against local PostgreSQL.
- The deploy targets (A: OCI, C: Vercel) and the pipeline (B: CI/CD) converge at the end of the week: B's CI validates changes and the team verifies the local Compose stack together.
- The application D deploys remains deliberately minimal (landing page → login → empty authenticated page). Do **not** build feature-domain functionality this sprint — the point is the pipeline.

## Risks / de-risking
- **First-time infra setup is the whole risk this sprint.** OCI Always-Free provisioning and Cloudflare Tunnel are the usual time sinks — start them Monday, not Wednesday.
- If a service is not ready, prioritize a working local fallback; do not block development on cloud accounts.
- Domain (Rasa) work intentionally does **not** start this week; it begins Sprint 2. Keep the skeleton dumb.

## Human review
- `slice-00-landing-page` is a normal frontend slice. Human review is required for changes touching authentication, deployment configuration, environment variables, secrets, or other sensitive areas.
- Every existing ⚠️ slice this sprint remains subject to human review before merge/deploy per `AGENTS.md`.
