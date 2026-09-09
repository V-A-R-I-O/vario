# Sprint 1 — Deployed Walking Skeleton & CD Pipeline (Week 1)

## Goal
Stand up the **entire delivery pipeline** and push a trivial-but-real app all the way through it to production. The skeleton does almost nothing — a user logs in and lands on an authenticated empty page — but it travels the full path: local Docker → GitHub → CI/CD → OCI backend (behind Cloudflare Tunnel) + Vercel frontend + Neon DB. Once this is live, **every merged slice from Sprint 2 onward auto-deploys**, so any change is immediately reflected in the running/demo app.

## Exit criteria
- [ ] A seeded test user logs in via `POST /api/auth/login` on the **production URL** and receives a valid VARIO JWT.
- [ ] Pushing a PR runs CI (lint + test + build); merging to main **auto-deploys** frontend (Vercel) and backend (OCI).
- [ ] Backend is reachable over HTTPS via Cloudflare Tunnel; frontend talks to it through `NEXT_PUBLIC_API_BASE_URL`.
- [ ] The 9-entity schema is migrated on Neon (dev + prod).
- [ ] `docker compose up` brings the stack up locally for every developer.
- [ ] A visible "hello, deploy pipeline" change merged by any member appears on the live URL within the pipeline's run time.

## Per-member lanes

| Member | Slices | Focus |
|---|---|---|
| **D** | ⚠️`slice-01-auth-login`, ⚠️`slice-02-db-schema`, `slice-27-docker-compose` | Repo/monorepo scaffold (Next.js + FastAPI), auth + mock-auth + JWT + Login UI, schema/migrations, Docker Compose |
| **B** | ⚠️`slice-28-cicd` | GitHub Actions: lint + pytest + Jest on PRs, build + deploy on merge to main |
| **A** | ⚠️`slice-29-oci-cloudflare` | Provision OCI Ampere A1 compute; Cloudflare Tunnel for backend HTTPS |
| **C** | ⚠️`slice-30-vercel-neon` | Vercel project for the frontend; Neon dev+prod DBs; env/secrets wiring |

## Dependencies & sequencing
- **Provision accounts on day 1** (OCI, Cloudflare, Vercel, Neon, GitHub) — these have the longest lead time.
- `slice-02-db-schema` (D) and `slice-30-vercel-neon` (C) coordinate on the connection string: C provisions the Neon instances, D writes and runs the migrations against them.
- The deploy targets (A: OCI, C: Vercel) and the pipeline (B: CI/CD) converge at the end of the week: B's pipeline deploys to A's compute and C's Vercel project. Hold a Thursday integration checkpoint to wire them together.
- The app D deploys is deliberately minimal (login → empty authenticated page). Do **not** build features this sprint — the point is the pipeline.

## Risks / de-risking
- **First-time infra setup is the whole risk this sprint.** OCI Always-Free provisioning and Cloudflare Tunnel are the usual time sinks — start them Monday, not Wednesday.
- If OCI provisioning stalls, B's CI/CD can deploy the backend to a temporary target and be repointed at OCI once ready — don't let one blocked account block the pipeline.
- Domain (Rasa) work intentionally does **not** start this week; it begins Sprint 2. Keep the skeleton dumb.

## Human review
- Every slice this sprint is ⚠️ (auth, schema, and all infra/CI/secrets) and requires human review before merge/deploy per `AGENTS.md`.
