# Slice 40 — admin-console-fixes

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C (Mitesh) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** Admin console — conversation logs, intent editor, audit · **Story points:** 3

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `docs/slices/slice-08-admin-intent-crud.md`
- `docs/slices/slice-11-conversation-logs.md`
- `docs/api-contract.md § admin`
- `frontend/src/app/admin/`
- `frontend/src/components/admin/IntentEditor.tsx`
- `backend/app/routers/admin_crud.py`
- Depends on: None (can start on day 1).

## Dev environment
Mitesh — laptop C.

## What to build
- Conversation logs: the frontend types and page match the backend schema (`id`, `sender`, `user_name`, …); tests use contract-shaped fixtures.
- Filters apply on Apply (or debounced); the "to" date is inclusive; actor search by name/email (add a backend filter if needed).
- IntentEditor sends a template update only when it changed; the backend regenerates variants only when `base_text` changes.
- The seed sets variant positions: the original is 0, the others 1..n.
- Admin CRUD writes audit entries with `role_pack`: intent_created/updated/deleted, template_edited, variant_edited/deleted. The audit filter dropdown lists exactly the recorded types, including `password_reset_initiated`.
- Hide the "Retraining" nav item until slice-10 ships.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B8 | Blocker | Admin conversation-logs page expects field names the backend doesn't send |
| M9a | Major | Saving an intent wipes its stored reply variants |
| M9b | Minor | Seeded reply variants can't be deleted |
| M9c | Minor | Admin configuration changes are not audit-logged |
| N15 | Minor | Conversation-log filters fire on every keystroke; the 'to' date excludes that day |
| N16 | Trivial | 'Retraining' nav item links to a page that doesn't exist |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given an admin opens Conversation Logs and clicks a row, then only that row expands with its transcript, and user and bot messages are distinguished.
- [ ] Given typing in a filter, then no request is sent until Apply (or the debounce delay).
- [ ] Given "to" = today, then today's conversations are included.
- [ ] Given an admin adds a phrase and saves, then the template's variants are unchanged.
- [ ] Given a seeded non-original variant, then it can be deleted.
- [ ] Given any admin config change, then an audit entry appears in the audit log, filterable by its type.
- [ ] Given the admin nav, then no link leads to a 404.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Retraining itself (slice-10).
- Rephraser (slice-09).

## Human review required?
No.
