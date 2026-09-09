# Slice 29 — oci-cloudflare

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 1 · **Module:** infra (backend hosting)

## References — read these first
- `AGENTS.md` (human review required for infra + secrets)
- `docs/ADD.md` § Stack (Compute: OCI Always Free ARM Ampere A1, 4 OCPU / 24 GB; Networking: Cloudflare Tunnel) + § Constraints
- `slice-27-docker-compose` (the containerized stack this hosts) and `slice-28-cicd` (which will deploy to this target)

## What to build
The production backend host: an OCI Always-Free ARM instance running the containerized backend (gateway + Rasa + mocks), exposed over HTTPS through a Cloudflare Tunnel — no public inbound ports.

Deliverables:
- Provisioned **OCI Ampere A1** VM within Always-Free limits, with Docker installed.
- The backend stack running on it (via the compose prod profile / containers).
- **Cloudflare Tunnel** (`cloudflared`) mapping a stable public hostname → the backend, terminating HTTPS.
- **Persistence across reboot**: `cloudflared` and the container stack come back up automatically (systemd units / restart policies).
- A short `docs/deploy-backend.md` (or section) documenting the host, the tunnel hostname, and how CI deploys to it — with all secrets/keys stored as GitHub Actions secrets, not in the repo.

## Acceptance criteria
- [ ] Given the OCI instance, when the backend is running, then it is reachable at a stable **HTTPS** URL via the Cloudflare Tunnel.
- [ ] Given the instance reboots, when it comes back, then the backend stack and the tunnel restart automatically without manual intervention.
- [ ] Given the security configuration, then there are no public inbound ports beyond what the tunnel requires (no open backend port to the internet).
- [ ] Given `slice-28-cicd`, then the deploy workflow can push a new backend build to this host using credentials stored only in GitHub Actions secrets.
- [ ] Given the deploy docs, then a teammate can find the host details and tunnel hostname without asking (no secrets in the doc).

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Frontend hosting (Vercel) and the database (Neon) — those are `slice-30-vercel-neon`.
- The CI/CD workflows themselves (`slice-28`); this slice just makes the target deployable.
- Autoscaling, multi-node, load balancing (out of scope for a 20-session demo).

## Human review required?
**Yes** — infrastructure provisioning and secrets. Do not merge/deploy without human review (per `AGENTS.md`).
