# Sprint 4 — Cross-cutting Services, Hardening & Demo (Weeks 6–7)

## Goal
Ship the cross-cutting admin services that make the console feel complete (variant generation, retraining, conversation logs), then harden and rehearse. The three domain owners each pick up one shared service now that their own domains are stable; D drives the non-functional bar (performance, graceful degradation). By the end: hardened, deployed, and a 20-session demo rehearsed end-to-end.

## Exit criteria
- [ ] Rephraser: saving a template auto-generates 4 paraphrased variants (placeholders preserved); "Generate Similar" returns 8 reviewable training phrases (US-8, US-9).
- [ ] Retraining: an admin can trigger `rasa train`+reload for their role pack and poll job status; `needs_retrain` clears on success.
- [ ] Conversation logs: an admin can browse and read (read-only) their role pack's conversation transcripts with per-message intent + confidence (FR-19 complete).
- [ ] Performance: 95% of queries respond within 2s (excluding mock delays); 20 concurrent sessions with no noticeable degradation.
- [ ] Reliability: the system degrades gracefully (informs, doesn't crash) when a mock API or TTS is down; session context survives a transient backend restart.
- [ ] Every FR has at least one test (automated or documented manual); demo script rehearsed.

## Per-member lanes

| Member | Slices | Focus |
|---|---|---|
| **A** | `slice-09-rephraser` | Rephraser-service (Gemini) + "Generate Similar" + variant editor UI; HR test pass + polish |
| **B** | `slice-10-retraining` | Retraining-service + Retraining UI + status polling; IT test pass; CI/CD finalised |
| **C** | `slice-11-conversation-logs` | `GET /api/admin/conversations` + transcript UI; Admissions test pass; deploy finalised |
| **D** | `slice-31-perf-hardening` | Load/perf test (20 sessions, 2s p95), graceful-degradation paths, session recovery; demo-infra readiness |

## EPIC-5 — Integration defects & real Rasa (added after the Sprint 3 audit)

The end-of-Sprint-3 integration audit (`docs/testing/sprint-3-integration-audit.md`) found 51 defects that only show up when all services run together. It also found that the role packs were keyword matchers rather than Rasa.

The team decided:
- **Migrate the packs to real Rasa 3.6.20.**
- **Demo locally on laptop C** instead of deploying, so slices 29 and 30 are Won't Do.
- **Do EPIC-5 first.** Slice-10 stays, slice-31 stays minimal, and slice-09 is "if time".

| Member | EPIC-5 slices | Points | Laptop |
|---|---|---|---|
| **D** Tahir | ⚠️`slice-32-rasa-contract-v2`, `slice-33-chat-ui-hardening`, ⚠️`slice-34-local-demo-stack` | 13 | A (M1, 8 GB) |
| **A** Pavan Kishor | `slice-35-hr-real-rasa`, `slice-36-hr-data-fixes` | 11 | B (M4, 8 GB) |
| **B** Rohith | `slice-37-it-real-rasa`, ⚠️`slice-38-it-data-and-ci` (+ `slice-10-retraining`) | 11 | D (Win 10, 8 GB, no Docker) |
| **C** Mitesh | `slice-39-adm-real-rasa`, `slice-40-admin-console-fixes` | 11 | C (LOQ, 24 GB) — **demo host** |

How the slices run in parallel:
- **Day 1:** Tahir merges ADR-006, which freezes the gateway↔Rasa contract. Same pattern as Sprint 2's frozen API contract.
- **Days 1–5:** A, B and C build their Rasa packs against it (`rasa train`, `rasa shell` and `rasa test` need no gateway). D builds 32, then 33.
- **Days 4–6:** slice-34 brings the full stack up on laptop C, and each pack plugs in.
- **Last 2–3 days:** re-test every defect with its repro steps on laptop C, close it in Jira, then rehearse the demo.

## Dependencies & sequencing
- `slice-09-rephraser` depends on `slice-08-admin-intent-crud` (template save hook) from Sprint 3.
- `slice-10-retraining` depends on the Rasa runtime + admin-crud training data.
- `slice-11-conversation-logs` reuses `slice-04-conversation-store`.
- Reserve the **last 2–3 days** purely for demo rehearsal, bug-fix triage, and doc finalisation — no new feature work.

## Risks / de-risking
- **Rephraser/retraining land late by design** — they're quality-of-life, not on the critical path. If time is tight, retraining can ship as "trigger + poll" with minimal UI; rephraser variants are the higher-value of the two (they're user-visible in every bot reply).
- **Perf surprises** — run the load test at the *start* of the sprint, not the end, so there's time to fix anything it exposes.

## Human review
- ⚠️ `slice-09-rephraser` — wires the **Gemini API key** (a secret). Requires human review of the credential/env wiring.
- `slice-11-conversation-logs` exposes end-user conversation content to role admins — authorization is enforced by `slice-07`; confirm the role-pack scoping holds during review.
- Any change to deployment config or secrets during hardening still requires human review per `AGENTS.md`.
