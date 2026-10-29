# ADR-007: Local-first runtime and demo

- **Status:** Accepted
- **Date:** 2026-10-29
- **Decision owners:** VARIO project team

## Context
The earlier plan required OCI compute, a permanent Cloudflare Tunnel, Vercel hosting and Neon PostgreSQL. Account/payment setup and deployment complexity add cost and risk without being necessary to implement, test or demonstrate the capstone. The repository already defines a complete local Docker Compose stack and a local demo slice.

## Decision
VARIO will be implemented, tested and demonstrated locally using Docker Compose and local PostgreSQL. GitHub Actions is used for continuous integration (tests, lint and builds); merging to `main` does not deploy to a cloud host.

## Consequences
- Slice 29 (OCI/Cloudflare hosting) and Slice 30 (Vercel/Neon hosting) are retired, not deleted or renumbered.
- Slice 28 remains active for CI, branch protection and review checks; cloud deployment requirements are removed.
- `DATABASE_URL` and frontend API configuration remain application settings, configured for local services.
- Local startup, migrations, idempotent seed data, health checks and demo instructions become the acceptance path.
- OCI, Vercel, Neon and permanent Cloudflare deployment credentials are not required by active workflows. Before removing any GitHub secret, search all active workflows and code references to confirm it is unused.
- A temporary Cloudflare Quick Tunnel is optional only when a remote-device HTTPS/microphone demo is needed. It is not a hosting target and is not required for ordinary local use.

## Alternatives considered
1. **OCI + Cloudflare + Vercel + Neon:** rejected due to setup/payment friction and unnecessary deployment overhead for the local capstone demo.
2. **Local Docker Compose + GitHub Actions CI:** accepted; repeatable, reviewable and aligned with the existing local-demo slice.

## References
- `docs/slices/slice-28-cicd.md`
- `docs/slices/slice-29-oci-cloudflare.md` (superseded)
- `docs/slices/slice-30-vercel-neon.md` (superseded)
- `docs/slices/slice-34-local-demo-stack.md`
- `docs/sprints/sprint-01.md`
