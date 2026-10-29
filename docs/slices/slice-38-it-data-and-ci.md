# Slice 38 — it-data-and-ci

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B (Rohith) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** IT data alignment + CI/CD · **Story points:** 3

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `.github/workflows/ci.yml`
- `docs/slices/slice-28-cicd.md`
- `mock-itsm-service/app/seed_data.py`
- Depends on: slice-34 for the final list of demo accounts.

## Dev environment
Rohith — laptop D. CI runs on GitHub, so no Docker is needed locally.

## What to build
- Use one ticket ID format across mock-itsm, the prompts and examples, the NLU regex and examples, the seed templates and the specs. The bot's own example must be a valid format.
- mock-itsm seed covers every mock-auth login (including the slice-34 demo accounts) with security questions; list the answers in the demo runbook.
- When ticket creation is rejected, show the reason and stop the Confirm card from looping.
- CI:
  - Run the mock-hrms, mock-itsm and mock-admissions tests.
  - Add the async test plugin so no IT tests are skipped.
  - Run `rasa data validate` for each pack.
  - Remove the stale "when present" IT job.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| M7b | Major | Bot asks for TKT-1234 but every ticket ID is IT-10xx |
| M7c | Major | IT and Admissions admin logins don't exist in mock-ITSM, so ticket creation loops |
| N11 | Minor | CI gaps: mock-service tests never run, 9 IT tests silently skipped, no Rasa validation |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given the bot's example ticket ID format, then a real ticket can be looked up using that format.
- [ ] Given a login as it@ or admissions@, when they raise a ticket, then the ticket is created.
- [ ] Given ticket creation is rejected, then the user sees why and can retry or cancel.
- [ ] Given a PR, then CI runs every service's tests with 0 skipped and validates each pack's Rasa data.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- IT Rasa runtime (slice-37).

## Human review required?
Yes — CI configuration.
