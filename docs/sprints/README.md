# V.A.R.I.O — Sprint Plan Overview

7 weeks · team of 4 (A, B, C, D) · 4 sprints. This folder holds one doc per sprint; the per-work-unit detail lives in `docs/slices/`. Read `AGENTS.md` before executing any slice.

## Ownership model

The professor's constraint — **each member builds functional modules end-to-end, including UI** — is met by giving three members a **vertical domain** (Rasa instance → integration adapter → mock → chat cards → their role's admin content) and the fourth the **shared platform** (which is itself UI-heavy: login, chat shell, admin console framework, talk mode). Every member ships user-facing UI they built. Nobody is backend-only or frontend-only.

| Member | Primary domain | Owns end-to-end |
|---|---|---|
| **A** | HR role pack | HRMS mock+adapter, Rasa-HR, HR chat cards (leave balance / request / FAQ), HR admin content, **rephraser-service** |
| **B** | IT Support role pack | ITSM mock+adapter, Rasa-IT, IT chat cards (ticket create / status / password reset), IT admin content, **retraining-service**, **CI/CD** |
| **C** | Admissions role pack | Admissions mock+adapter, Rasa-Admissions, Admissions cards (status / checklist / fees), Admissions admin content, **conversation-logs**, **Vercel + Neon** |
| **D** | Platform & Core | auth + mock-auth, gateway, session/router/renderer, shared chat shell + message component library, admin console framework, talk-mode/TTS, DB schema, **Docker Compose**, **hardening/perf** |

The admin console is **role-scoped**, so A/B/C each build, seed, and verify *their own* role's admin screens on top of D's framework — that is how they get admin UI without colliding.

**Cross-cutting services** (rephraser, retraining, conversation-logs) are deliberately handed to A/B/C in the later sprints to balance D's load, once their own domains are stable.

## 7-week roadmap

Infra-first, continuous delivery. Sprint 1 stands up the **whole deployment pipeline** and deploys a trivial walking skeleton through it; from then on **every merged slice auto-deploys** to production. Feature work integrates and ships continuously rather than piling up for a big-bang deploy at the end.

| Sprint | Weeks | Theme | Exit state |
|---|---|---|---|
| [1](sprint-01.md) | 1 | Deployed walking skeleton & CD pipeline | Login works on the production URL; every merge auto-deploys via CI/CD to OCI+Vercel behind Cloudflare |
| [2](sprint-02.md) | 2–3 | Role packs & read flows | Each role pack stands up; all three status-lookup flows live and auto-deploying through the gateway |
| [3](sprint-03.md) | 4–5 | Write workflows + admin + voice | Every FR functionally complete, continuously deployed |
| [4](sprint-04.md) | 6–7 | Cross-cutting services + harden + demo | Hardened, 20-session demo rehearsed |

## Cadence & rules

- **All four members have a live lane every week.** Each sprint doc has a "Per-member lanes" table proving it.
- **One slice ≈ one agent session / roughly one member-week.** See the slice template in `docs/slices/`.
- **Infra-first / continuous delivery.** The full pipeline (CI/CD → OCI + Cloudflare + Vercel + Neon) goes live in Sprint 1 against a trivial skeleton. Every slice after that auto-deploys on merge — "any update is reflected in the deployed app itself." No separate staging-vs-prod ceremony; the demo environment is always current.
- **The API contract (`docs/api-contract.md`) is frozen.** A/B/C build their role packs against it in isolation (Storybook + curl) in early Sprint 2, so they don't block on D's chat shell; integration happens within the same sprint.
- **Human review required** (per `AGENTS.md`) on: auth, DB schema/destructive migrations, and all infra/CI/secrets slices. These are marked ⚠️ in each sprint.
- **Commit/PR convention:** reference the slice ID, e.g. `slice-14-hr-leave-balance: render leave balance card`.

## Slice → owner → sprint index

Full slice specs live in `docs/slices/`. Summary:

| # | Slice | Owner | Sprint |
|---|---|---|---|
| 01 | ⚠️ auth-login | D | 1 |
| 02 | ⚠️ db-schema | D | 1 |
| 27 | docker-compose | D | 1 |
| 28 | ⚠️ cicd | B | 1 |
| 29 | ⚠️ oci-cloudflare | A | 1 |
| 30 | ⚠️ vercel-neon | C | 1 |
| 03 | ⚠️ gateway-envelope | D | 2 |
| 04 | conversation-store | D | 2 |
| 05 | chat-core | D | 2 |
| 12 | hr-rasa | A | 2 |
| 13 | hrms-adapter | A | 2 |
| 14 | hr-leave-balance | A | 2 |
| 17 | it-rasa | B | 2 |
| 18 | itsm-adapter | B | 2 |
| 20 | it-ticket-status | B | 2 |
| 22 | adm-rasa | C | 2 |
| 23 | adm-adapter | C | 2 |
| 24 | adm-app-status | C | 2 |
| 06 | ⚠️ talk-mode | D | 3 |
| 07 | ⚠️ admin-shell | D | 3 |
| 08 | admin-intent-crud | D | 3 |
| 15 | hr-leave-request | A | 3 |
| 16 | hr-policy-faq | A | 3 |
| 19 | it-ticket-create | B | 3 |
| 21 | it-password-reset | B | 3 |
| 25 | adm-checklist | C | 3 |
| 26 | adm-fee-deadline | C | 3 |
| 09 | ⚠️ rephraser | A | 4 |
| 10 | retraining | B | 4 |
| 11 | conversation-logs | C | 4 |
| 31 | perf-hardening | D | 4 |
