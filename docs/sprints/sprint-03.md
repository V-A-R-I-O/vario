# Sprint 3 — Write Workflows + Admin + Voice (Weeks 4–5)

## Goal
Complete every functional requirement: the multi-turn **write** workflows (leave submission, ticket creation, password reset), the **admin console** (each admin manages their own role pack's intents/FAQs/templates), and **talk mode** (voice in/out). Deployment targets already exist (Sprint 1), so every workflow **auto-deploys as it merges** — by the end of the sprint the product is functionally complete and live.

## Exit criteria
- [ ] HR: guided leave request (type/start/end/reason → confirm → reference ID), audit-logged (FR-8, FR-9).
- [ ] IT: guided ticket creation with duplicate-suppression (FR-13) and guided password reset with mock identity verification (FR-12).
- [ ] Admissions: fee/deadline answers from the configurable calendar (FR-16).
- [ ] An admin can create a static FAQ and edit a dynamic-workflow's response text, scoped to their own role pack; changes flag `needs_retrain` (FR-18).
- [ ] Admissions: document checklist by program → list component (FR-15).
- [ ] Talk mode: browser STT → chat → TTS audio playback, with graceful text-only fallback when TTS is unavailable.
- [ ] Audit log records every business-significant event and is viewable in the console (FR-19 partial).

## Per-member lanes

| Member | Slices | Focus |
|---|---|---|
| **A** | `slice-15-hr-leave-request`, `slice-16-hr-policy-faq` | Multi-turn leave form + confirm + audit; static policy FAQ + HR admin content on the console |
| **B** | `slice-19-it-ticket-create`, `slice-21-it-password-reset` | Ticket create + dedupe; password reset with mock identity verification |
| **C** | `slice-25-adm-checklist`, `slice-26-adm-fee-deadline` | Document checklist → list component; fee/deadline calendar |
| **D** | `slice-07-admin-shell`, `slice-08-admin-intent-crud`, `slice-06-talk-mode` | Admin console framework + audit-log UI; intent/phrase/template/variant CRUD; talk-mode/TTS |

## Dependencies & sequencing
- `slice-07-admin-shell` + `slice-08-admin-intent-crud` (D) must land before A wires HR admin content (`slice-16`) — D should front-load these in Week 4.
- `slice-15`, `slice-19`, `slice-21` all depend on the write path in chat-core (Sprint 2) and their adapters' write methods (`submit_leave`, `create_ticket`, `reset_password`).
- Everything merged this sprint auto-deploys via the Sprint 1 pipeline — no separate deploy step.

## Risks / de-risking
- **Multi-turn slot filling** is the trickiest Rasa work — budget time for form validation and the confirmation step. A/B share patterns (both build a confirm→submit→ref-ID flow).
- **TTS free-tier limits** — verify the graceful-degradation flag path works before relying on audio in the demo.

## Human review
- ⚠️ `slice-07-admin-shell` — establishes admin **role-based authorization** (scoping admins to their own role pack). Requires human review.
- ⚠️ `slice-06-talk-mode` — wires **Google Cloud TTS credentials** (a secret). Requires human review of the credential/env wiring.
- `slice-21-it-password-reset` simulates identity verification on **mock ITSM** — this is a business workflow, not VARIO's real auth; no ⚠️, but confirm during review that no real credential handling sneaks in.
