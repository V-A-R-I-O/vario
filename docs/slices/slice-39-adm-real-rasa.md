# Slice 39 — adm-real-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C (Mitesh) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** Admissions role pack — Rasa runtime, forms, actions · **Story points:** 8

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docs/slices/slice-22-adm-rasa.md`
- `docs/slices/slice-24-adm-app-status.md`
- `docs/slices/slice-25-adm-checklist.md`
- `docs/slices/slice-26-adm-fee-deadline.md`
- `rasa-admissions/`
- `backend/app/services/admissions_adapter.py`
- Depends on: ADR-006 from slice-32 (start NLU/domain/forms on day 1).

## Dev environment
Mitesh — laptop C (Windows 11, 24 GB, Docker Desktop; also the demo host). Run all three Rasa packs here for integration.

## What to build
- Replace `rasa-admissions/server.py` with a **Rasa 3.6.20 project** (DIET + FallbackClassifier 0.4).
- Forms: `application_status_form` (application_id) and `checklist_form` (program). Other intents can interrupt; slots reset per lookup.
- Action server (Python 3.10, rasa-sdk 3.6.x):
  - The Admissions adapter lives inside the pack.
  - Remove the `OFFLINE_*` hardcoded data; every answer comes from mock-admissions (FR-14..17).
  - "Service down" and "not found" get different messages.
- Fee and deadline answers come from the single mock-admissions calendar (FR-16); calendar edits show up without a restart.
- Greet, goodbye and out-of-scope responses.
- Render admissions cards through `AdmissionsStatusCard` and friends (coordinate with slice-33), or delete the dead components.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B2b | Blocker | Admissions pack never calls mock-admissions; answers are hardcoded (FR-16 broken) |
| M3c | Major | A pending Admissions prompt swallows the next message |
| M1b | Major | Admissions reuses stale application IDs and programs |
| M5b | Major | Admissions replies with 'Intent greet acknowledged' debug text |
| M6b | Minor | Admissions reports 'not found' when the service is actually down |
| N13 | Minor | Admissions misclassifies common follow-up questions |
| N14 | Trivial | Admissions card components are dead code duplicated in the chat page |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given status, checklist and fee questions, then mock-admissions receives the requests and the answers match its data.
- [ ] Given `PUT /calendar` changes the MBA fee, when the fee is asked again, then the new fee is answered.
- [ ] Given the application-ID prompt, when the user asks about the MBA fee, then the fee is answered.
- [ ] Given a completed lookup, when "check application status" is asked again, then it asks for an ID.
- [ ] Given mock-admissions is stopped, then the reply says the service is unavailable (not "not found").
- [ ] Given "and for btech?" after a fee question, then the B.Tech fee is answered; "hi" gets a greeting.
- [ ] Given `rasa data validate`, then it passes; the ported tests use the mock, not hardcoded data.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Admin conversation logs (slice-40).
- Chat page card dispatch (slice-33).

## Human review required?
No.
