# Slice 22 — adm-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 2 · **Module:** `role-pack-runtime` (Admissions instance)

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `role-pack-runtime` module
- `docs/vario-overview.md` § 6 (FR-14…FR-17) and § 12 (seed-data shape)
- `docs/api-contract.md` § Admin — Intents (intent/phrase/template structures)
- `.env.example` (`RASA_ADMISSIONS_URL`)

## What to build
Stand up the Admissions Rasa instance and seed its data. NLU backbone of C's vertical; the Admissions adapter is `slice-23` and the end-to-end application-status card is `slice-24`. Scope classification here to **`check_application_status`**; other Admissions intents are seeded as stubs for later slices.

Deliverables:
- A Rasa project for Admissions (`config.yml`, `domain.yml`, `nlu.yml`, rules/stories, `actions.py`) running at `RASA_ADMISSIONS_URL`.
- Seed intents (`role_pack = admissions`): `check_application_status` (`dynamic_workflow`), plus placeholders for `get_document_checklist`, `ask_fee_deadline` to be fleshed out in `slice-25` / `slice-26`.
- ~30–50 training phrases for `check_application_status` (with an `application_id` entity); a handful for the others.
- An `nlu_fallback` policy for low-confidence utterances.
- A custom action skeleton `action_check_application_status` that will call the Admissions adapter (wired in `slice-24`) and return `template_key` + slots.
- `response_templates` seeded for the application-status response with `{application_id}` / `{status}` placeholders.

## Acceptance criteria
- [ ] Given the Admissions Rasa service, when it starts, then it is reachable at `RASA_ADMISSIONS_URL`.
- [ ] Given variations of "what's the status of application APP-1001", then Rasa-Admissions classifies `check_application_status` and extracts the `application_id` entity.
- [ ] Given an off-topic message, then `nlu_fallback` fires.
- [ ] Given the seed step, then the DB contains the Admissions dynamic-workflow intent(s) with training phrases and an application-status response template.
- [ ] Given `action_check_application_status`, then it exists and returns a `template_key` + slots shape (adapter call wired in `slice-24`).

## Mockup / reference (if UI-facing)
No UI surface (Rasa runtime). Admissions chat cards are built in `slice-24`.

## Out of scope for this slice
- Admissions mock + adapter (`slice-23`).
- End-to-end application-status card (`slice-24`), document checklist (`slice-25`), fee/deadline calendar (`slice-26`).
- HR and IT role packs.

## Human review required?
No.
