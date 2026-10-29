# V.A.R.I.O — Sprint Plan Overview

7 weeks · team of 4 (A, B, C, D) · 4 sprints. This folder holds one doc per sprint; the per-work-unit detail lives in \`docs/slices/\`. Read \`AGENTS.md\` before executing any slice.

## Ownership model

The professor's constraint — **each member builds functional modules end-to-end, including UI** — is met by giving three members a **vertical domain** (Rasa instance → integration adapter → mock → chat cards → their role's admin content) and the fourth the **shared platform** (which is itself UI-heavy: login, chat shell, admin console framework, talk mode). Every member ships user-facing UI they built. Nobody is backend-only or frontend-only.

| Member | Primary domain | Owns end-to-end | Assignee  |
|---|---|---|---|
| **A** | HR role pack | VARIO public landing page, HRMS mock+adapter, Rasa-HR, HR chat cards (leave balance / request / FAQ), HR admin content, **rephraser-service** | Kishor |
| **B** | IT Support role pack | ITSM mock+adapter, Rasa-IT, IT chat cards (ticket create / status / password reset), IT admin content, **retraining-service**, **CI/CD** | Rohith |
| **C** | Admissions role pack | Admissions mock+adapter, Rasa-Admissions, Admissions cards (status / checklist / fees), Admissions admin content, **conversation-logs**, **local frontend/database validation** | Mitesh |
| **D** | Platform & Core | auth + mock-auth, gateway, session/router/renderer, shared chat shell + message component library, admin console framework, talk-mode/TTS, DB schema, **Docker Compose**, **hardening/perf** | Tahir |

The admin console is **role-scoped**, so A/B/C each build, seed, and verify *their own* role's admin screens on top of D's framework — that is how they get admin UI without colliding.

**Cross-cutting services** (rephraser, retraining, conversation-logs) are deliberately handed to A/B/C in the later sprints to balance D's load, once their own domains are stable.

## 7-week roadmap

Local-first, continuous integration. Sprint 1 delivers a real but minimal walking skeleton locally: public landing page → login → authenticated shell. GitHub Actions validates pull requests and builds; cloud deployment is not part of the project plan.

| Sprint | Weeks | Theme | Exit state |
|---|---|---|---|
| [1](sprint-01.md) | 1 | Local walking skeleton & CI pipeline | Public landing page and login work locally; local PostgreSQL migrations and Compose stack work; CI passes |
| [2](sprint-02.md) | 2–3 | Role packs & read flows | Each role pack stands up; all three status-lookup flows work through the local gateway |
| [3](sprint-03.md) | 4–5 | Write workflows + admin + voice | Every FR functionally complete and integrated in the local stack |
| [4](sprint-04.md) | 6–7 | Cross-cutting services + harden + demo | Hardened, 20-session demo rehearsed |

## Cadence & rules

- **All four members have a live lane every week.** Each sprint doc has a "Per-member lanes" table proving it.
- **One slice ≈ one agent session / roughly one member-week.** See the slice template in \`docs/slices/\`.
- **Local-first / continuous integration.** CI runs on pull requests and pushes to main. Developers run the application with Docker Compose; cloud deployment is not required.
- The **public landing page (\`slice-00\`) is a frontend-only foundation slice** and does not renumber or replace any existing slice 01–31.
- **The API contract (\`docs/api-contract.md\`) is frozen.** A/B/C build their role packs against it in isolation (Storybook + curl) in early Sprint 2, so they don't block on D's chat shell; integration happens within the same sprint.
- **Human review required** (per \`AGENTS.md\`) on: auth, DB schema/destructive migrations, and all infra/CI/secrets slices. These are marked ⚠️ in each sprint.
- **Commit/PR convention:** reference the slice ID, e.g. \`slice-14-hr-leave-balance: render leave balance card\`.

## Slice → owner → sprint index

Full slice specs live in \`docs/slices/\`. Summary:

| # | Slice | Owner | Sprint |
|---|---|---|---|
| **00** | landing-page | **A** | **1** |
| 01 | ⚠️ auth-login | D | 1 |
| 02 | ⚠️ db-schema | D | 1 |
| 27 | docker-compose | D | 1 |
| 28 | ⚠️ cicd | B | 1 |
| 29 | ~~⚠️ oci-cloudflare~~ — Won't Do (local demo, see slice-34) | A | 1 |
| 30 | ~~⚠️ vercel-neon~~ — Won't Do (local demo, see slice-34) | C | 1 |
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
| 09 | ⚠️ rephraser (if time — after EPIC-5) | A | 4 |
| 10 | retraining | B | 4 |
| 11 | conversation-logs | C | 4 |
| 31 | perf-hardening (minimal) | D | 4 |
| **32** | ⚠️ rasa-contract-v2 | D | 4 (EPIC-5) |
| **33** | chat-ui-hardening | D | 4 (EPIC-5) |
| **34** | ⚠️ local-demo-stack | D | 4 (EPIC-5) |
| **35** | hr-real-rasa | A | 4 (EPIC-5) |
| **36** | hr-data-fixes | A | 4 (EPIC-5) |
| **37** | it-real-rasa | B | 4 (EPIC-5) |
| **38** | ⚠️ it-data-and-ci | B | 4 (EPIC-5) |
| **39** | adm-real-rasa | C | 4 (EPIC-5) |
| **40** | admin-console-fixes | C | 4 (EPIC-5) |

Slices 32–40 come from the end-of-Sprint-3 integration audit (`docs/testing/sprint-3-integration-audit.md`), which logs 51 defects as Jira Bugs under EPIC-5. Import them with `docs/engineering/vario-epic5-jira-import.csv`.
