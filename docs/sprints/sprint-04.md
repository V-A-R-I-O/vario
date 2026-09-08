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
