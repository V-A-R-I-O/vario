# Slice 30 — Vercel / Neon deployment (superseded)

> **Status: RETIRED — NOT ACTIVE WORK.** VARIO will run and be demonstrated locally. This file is retained for history; do not provision Vercel or Neon for the project.

**Original owner:** C · **Original sprint:** 1

## Superseding decision
Use the local Docker Compose stack documented in `docs/slices/slice-34-local-demo-stack.md` and ADR-007. The Next.js frontend and PostgreSQL database run locally.

## Requirements explicitly retired
- Vercel project provisioning and production frontend deployment.
- Neon dev/prod database provisioning and branch connection strings.
- Cloud environment-variable wiring for Vercel, OCI and Neon.
- Automatic frontend deployment on merge to `main`.
- Neon-specific migration acceptance criteria.

## Replacement
Keep `DATABASE_URL` and `NEXT_PUBLIC_API_BASE_URL` as application configuration where used. Configure them for the local Compose network and verify migrations against local PostgreSQL. CI must not require a hosted database unless a separately approved test service is added.

Do not delete this historical slice or reuse its ID.
