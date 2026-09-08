# Slice 12 — hr-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 2 · **Module:** `role-pack-runtime` (HR instance)

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `role-pack-runtime` module (each Rasa instance owns classification, entities, slot filling, actions)
- `docs/vario-overview.md` § 6 (FR-6…FR-9) and § 12 (`intents`, `training_phrases`, `response_templates` — the seed data shape)
- `docs/api-contract.md` § Admin — Intents (the intent/phrase/template structures the DB seed must match)
- `.env.example` (`RASA_HR_URL`)

## What to build
Stand up the HR Rasa instance and seed its data. This slice is the **NLU backbone** of A's vertical; the HRMS adapter is `slice-13` and the end-to-end leave-balance card is `slice-14`. Scope the classification work here to **`check_leave_balance`**; other HR intents are seeded as stubs for later slices.

Deliverables:
- A Rasa project for HR (`config.yml`, `domain.yml`, `nlu.yml`, rules/stories, `actions.py`) running as a service at `RASA_HR_URL`.
- Seed intents in the DB (`role_pack = hr`): `check_leave_balance` (`dynamic_workflow`), plus placeholders for `ask_leave_status`, `submit_leave_request`, `ask_policy_faq` to be fleshed out in later slices.
- ~30–50 training phrases for `check_leave_balance`; a handful for the others.
- An `nlu_fallback` policy so low-confidence utterances can trigger clarification (supports FR-2 upstream).
- A custom action skeleton `action_check_leave_balance` that will call the HRMS adapter (wired in `slice-14`) and return `template_key` + slots.
- `response_templates` seeded for the leave-balance response with `{balance}`-style placeholders.

## Acceptance criteria
- [ ] Given the HR Rasa service, when it starts, then it is reachable at `RASA_HR_URL`.
- [ ] Given variations of "what's my leave balance", then Rasa-HR classifies `check_leave_balance` with high confidence.
- [ ] Given an off-topic message, then the `nlu_fallback` intent fires (enabling clarification).
- [ ] Given the seed step, then the DB contains the HR dynamic-workflow intent(s) with training phrases and a leave-balance response template (so they appear in the admin console later).
- [ ] Given `action_check_leave_balance`, then it exists and returns a `template_key` + slots shape (the adapter call is wired in `slice-14`).

## Mockup / reference (if UI-facing)
No UI surface (Rasa runtime). HR's chat cards are built in `slice-14`.

## Out of scope for this slice
- HRMS mock + adapter (`slice-13`).
- The end-to-end leave-balance card + real adapter call (`slice-14`).
- The full guided leave-request form (`slice-15`) and policy FAQ content (`slice-16`).
- IT and Admissions role packs.

## Human review required?
No.
