# Slice 36 — hr-data-fixes

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A (Pavan Kishor) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** HR role pack — FAQ content, mock HRMS · **Story points:** 3

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docs/slices/slice-13-hrms-adapter.md`
- `docs/slices/slice-16-hr-policy-faq.md`
- `mock-hrms-service/`
- `backend/scripts/seed.py`
- Depends on: slice-35 for the intent and form wiring (same owner — sequence it after the NLU skeleton).

## Dev environment
Pavan — laptop B.

## What to build
- Topic-specific policy answers (maternity, paternity, sick, bereavement, carry-forward, WFH), each with its own seeded, admin-editable template, so the generic answer can't overwrite them.
- Policy facts from one source of truth (mock-hrms `/policies` or the same seed data). Fix the current contradictions.
- mock-hrms: `/reset` fully restores balances and reference counters. Reject past dates, end-before-start and requests exceeding the balance.
- FR-6 leave-request status: show the logged-in employee's latest (or referenced) request status from HRMS, as a card.
- HRMS seed covers every mock-auth login added in slice-34.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| M4b | Major | Topic-specific HR FAQ answers are replaced by the generic policy template |
| N8 | Major | Leave request status (FR-6) is a stub |
| M7a | Minor | HR FAQ answers contradict the mock HRMS policy data |
| N6 | Minor | mock-hrms /reset does not restore leave balances |
| N7 | Minor | mock-hrms accepts invalid leave requests |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given "what is the maternity policy?", then the maternity answer (matching mock-hrms data) is returned; the same holds for each topic.
- [ ] Given an admin edits the maternity template, then the next maternity answer uses the edit.
- [ ] Given leave was submitted, when `POST /reset` is called, then balances and the reference counter return to seed values.
- [ ] Given an invalid leave request to mock-hrms, then it's rejected with a clear error.
- [ ] Given "has my leave been approved?", then the status of the employee's latest request is shown.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- NLU/form runtime (slice-35).

## Human review required?
No.
