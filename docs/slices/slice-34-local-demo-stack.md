# Slice 34 — local-demo-stack

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D (Tahir) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** Infra — Docker Compose, local demo, docs · **Story points:** 5

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docker-compose.yml`
- `docs/slices/slice-27-docker-compose.md`
- `frontend/next.config.mjs`
- `backend/app/main.py`
- `backend/scripts/seed.py`
- `backend/app/middleware.py`
- `mock-auth-service/app/seed_data.py`
- Depends on: slice-32. Final verification needs the Rasa packs from 35/37/39 — start with the current services and swap the images in as each pack lands.

## Dev environment
Built by Tahir; **verified on Mitesh's laptop C** (Windows 11, i5-13th-gen HX, 24 GB, Docker Desktop) — the demo host. Pair with Mitesh for the final run.

## What to build
- **docker-compose.yml** brings up the whole stack with correct ports, env, healthchecks and `depends_on`:
  - postgres, gateway and frontend
  - all four real mock services: auth, hrms, itsm and admissions
  - rasa-hr, rasa-it and rasa-admissions on `rasa/rasa:3.6.20-full`, each with an action server (Python 3.10 + rasa-sdk 3.6.x)
  - the Rasa tracker store on postgres
- One documented command trains all three models (models persisted). Compose fails clearly if a model is missing.
- Gateway start runs `alembic upgrade head` plus an idempotent seed. Stop using `create_all` on Postgres. The seed must not log `DATABASE_URL`.
- Frontend: Next.js rewrite `/api/*` → gateway; `NEXT_PUBLIC_API_BASE_URL=/api`. Only port 3000 needs to be reachable from other laptops.
- mock-auth: one employee login per presenter plus an applicant login. Agree the IDs with slices 36 and 38 so they exist in HRMS and ITSM.
- Rate limiting keyed by the forwarded client IP behind the trusted proxy (or per user), so four laptops behind one proxy/tunnel don't share the login limit.
- **docs/demo/local-demo.md** — runbook for laptop C:
  - WSL2 memory (`.wslconfig`) and a Windows Firewall rule for port 3000
  - Hotspot vs college Wi-Fi check
  - Cloudflare quick tunnel for HTTPS and the microphone (`cloudflared tunnel --url http://localhost:3000`, no account)
  - Chrome insecure-origin flag as a fallback
  - Training the models and resetting data between rehearsals
  - Demo accounts table and troubleshooting
- README rewrite: local run, ports, accounts.
- ADR-007 records the local-demo decision; mark the OCI/Vercel/Neon/Cloudflare-deploy references superseded.
- Fix references to the non-existent `docs/vario-overview.md` (the file is `docs/overview.md`).

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B1 | Blocker | docker compose does not run the real stack |
| B3 | Blocker | Database is never migrated or seeded automatically, and seeding is undocumented |
| B4 | Blocker | Frontend can't reach the API from other laptops (localhost baked into the bundle) |
| N3 | Major | Rate limits break a multi-laptop demo (shared IP behind proxy, single demo account) |
| N4 | Minor | Docs describe the dropped cloud deployment and an unstarted project |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given a fresh clone on laptop C with `.env` from `.env.example`, when the documented train and `docker compose up` commands run, then every service reports healthy.
- [ ] Given the stack on laptop C, when a client on the same hotspot opens `http://<C-IP>:3000`, then login and one chat in each role pack work.
- [ ] Given the quick-tunnel URL, when it's opened on another laptop, then login, chat and the talk-mode microphone work.
- [ ] Given a fresh database, then migrations and the seed run automatically, and a second start doesn't duplicate data.
- [ ] Given four laptops logging in through the tunnel within one minute, then none is rate-limited.
- [ ] Given the README and the runbook, then a teammate can boot the demo without asking anyone.
- [ ] Given the compose file, then no secret values are hardcoded.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Role-pack internals (35–39).
- CI changes (slice-38).
- Any cloud deployment.

## Human review required?
Yes — Docker Compose, environment variables and infra.
