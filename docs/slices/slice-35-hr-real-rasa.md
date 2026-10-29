# Slice 35 — hr-real-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A (Pavan Kishor) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** HR role pack — Rasa runtime, forms, actions · **Story points:** 8

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docs/slices/slice-12-hr-rasa.md`
- `docs/slices/slice-14-hr-leave-balance.md`
- `docs/slices/slice-15-hr-leave-request.md`
- `docs/decisions/ADR-005-hrms-adapter-contract.md`
- `rasa-hr/`
- `backend/app/services/hrms_adapter.py`
- Depends on: ADR-006 from slice-32 (start NLU/domain/forms on day 1; plug in the shared channel when it lands).

## Dev environment
Pavan — laptop B (M4, 8 GB, Docker). Run `rasa/rasa:3.6.20-full` (arm64 image exists) or a Python 3.10 venv with `pip install rasa==3.6.20`. Run only the HR pack locally; full-stack integration on laptop C.

## What to build
- Replace the keyword matcher in `rasa-hr/server.py` with a **Rasa 3.6.20 project**:
  - `config.yml` with a DIET pipeline and FallbackClassifier at threshold 0.4
  - `domain.yml` with intents, entities, slots, responses and forms
  - `data/` with nlu, rules and stories — reuse and extend the existing YAML
- **Action server** (rasa-sdk 3.6.x, Python 3.10) in `rasa-hr/actions`:
  - The HRMS adapter lives inside the pack (no `../backend` import) and calls mock-hrms via `MOCK_HRMS_URL`.
  - No hardcoded employee data.
  - An HRMS outage gives a clear "HR system unavailable" reply.
- **Identity:** balance and leave submission use `metadata.auth_context.employee_id`. Employee IDs typed in chat are ignored for these intents.
- **leave_request_form:**
  - Steps: leave_type (including `annual`), start_date, end_date, reason → confirm → submit → reference ID, plus an audit event that includes the employee ID.
  - Validation: dates, end ≥ start, no past dates.
  - Cancel/stop works at any step, and other intents can interrupt.
  - Slots reset after submit or cancel.
- Responses for greet, goodbye and out-of-scope — no debug text.
- Use the shared channel from slice-32; return `template_key`/`card` per ADR-006.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B6 | Blocker | HR ignores the logged-in employee: balance loops and leave submission always fails |
| B7 | Blocker | Every leave-request question shows 'Sorry, I couldn't put together a response' |
| B2a | Blocker | HR pack imports backend code and silently serves hardcoded data when that fails |
| M1a | Major | A second leave request reuses the previous request's dates and reason |
| M2a | Major | Any user can read another employee's leave balance and file leave as them |
| M3a | Major | Leave form gets stuck after an off-script reply at the confirmation step |
| M4a | Major | Off-topic policy questions get the leave policy at 0.9 confidence |
| M5a | Major | HR replies with 'Intent greet acknowledged' debug text |
| N5 | Minor | Leave form rejects 'annual' and natural-language dates |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given EMP-1001 is logged in, when they ask "what is my leave balance?", then their balance card shows without asking for an ID.
- [ ] Given EMP-1001 types "leave balance for EMP-1042", then EMP-1001's own balance (or a polite refusal) is shown — never EMP-1042's.
- [ ] Given a leave request, then each step asks its question in words, accepts `annual`, rejects invalid dates with guidance, and confirm files the request for the logged-in employee with a reference ID and an audit entry.
- [ ] Given a completed or cancelled request, when a new one starts, then every question is asked again.
- [ ] Given an off-script reply at the confirmation step, then the bot re-asks; "cancel" exits at any step.
- [ ] Given "what is the travel reimbursement policy?", then the bot clarifies instead of answering with the leave policy.
- [ ] Given "hi" or "bye", then a proper greeting or goodbye is returned.
- [ ] Given mock-hrms is stopped, then the reply says the HR system is unavailable — no hardcoded numbers.
- [ ] Given `rasa data validate` and `rasa test nlu`, then validation passes, and the existing HR flow tests are ported to the new runtime.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Topic FAQ content and mock-hrms fixes (slice-36).
- Chat UI cards (slice-33).

## Human review required?
No — but the reviewer confirms the employee ID is never taken from chat text for balance or submission.
