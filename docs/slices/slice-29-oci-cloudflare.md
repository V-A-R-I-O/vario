# Slice 29 — OCI / Cloudflare deployment (superseded)

> **Status: RETIRED — NOT ACTIVE WORK.** VARIO is local-first. This file is retained for history; do not provision OCI or implement a permanent Cloudflare Tunnel for VARIO.

**Original owner:** A · **Original sprint:** 1

## Superseding decision
Use the local Docker Compose stack in `docs/slices/slice-34-local-demo-stack.md` and ADR-007. The application, database and supporting services run on the development/demo machine. GitHub Actions is used for CI only.

## Requirements explicitly retired
- OCI Always-Free VM provisioning.
- Production Compose profile hosted on OCI.
- Permanent Cloudflare Tunnel / stable public backend hostname.
- Reboot persistence for cloud-hosted services.
- `docs/deploy-backend.md` instructions for deploying to OCI.
- CI deployment credentials and deployment to the OCI host.

## Replacement
Validate the stack locally with Docker Compose, health checks, migrations, seed data, and the demo runbook. Optional temporary tunnel access is a separate demo convenience only when needed for cross-device HTTPS/microphone testing; it is not a hosting target.

Do not delete this historical slice or reuse its ID.
