# Slice 17 — it-rasa

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 2 · **Module:** `role-pack-runtime` (IT Support instance)

## References — read these first
- `AGENTS.md`
- `docs/ADD.md` → `role-pack-runtime` module
- `docs/vario-overview.md` § 6 (FR-10…FR-13) and § 12 (seed-data shape)
- `docs/api-contract.md` § Admin — Intents (intent/phrase/template structures)
- `.env.example` (`RASA_IT_URL`)

## What to build
Stand up the IT Support Rasa instance and seed its data. NLU backbone of B's vertical; the ITSM adapter is `slice-18` and the end-to-end ticket-status card is `slice-20`. Scope classification here to **`check_ticket_status`**; other IT intents are seeded as stubs for later slices.

Deliverables:
- A Rasa project for IT (`config.yml`, `domain.yml`, `nlu.yml`, rules/stories, `actions.py`) running at `RASA_IT_URL`.
- Seed intents (`role_pack = it`): `check_ticket_status` (`dynamic_workflow`), plus placeholders for `raise_ticket`, `reset_password` to be fleshed out in `slice-19` / `slice-21`.
- ~30–50 training phrases for `check_ticket_status` (with a `ticket_id` entity); a handful for the others.
- An `nlu_fallback` policy for low-confidence utterances.
- A custom action skeleton `action_check_ticket_status` that will call the ITSM adapter (wired in `slice-20`) and return `template_key` + slots.
- `response_templates` seeded for the ticket-status response with `{ticket_id}` / `{status}` placeholders.

## Acceptance criteria
- [ ] Given the IT Rasa service, when it starts, then it is reachable at `RASA_IT_URL`.
- [ ] Given variations of "what's the status of my ticket TKT-1234", then Rasa-IT classifies `check_ticket_status` and extracts the `ticket_id` entity.
- [ ] Given an off-topic message, then `nlu_fallback` fires.
- [ ] Given the seed step, then the DB contains the IT dynamic-workflow intent(s) with training phrases and a ticket-status response template.
- [ ] Given `action_check_ticket_status`, then it exists and returns a `template_key` + slots shape (adapter call wired in `slice-20`).

## Mockup / reference (if UI-facing)
No UI surface (Rasa runtime). IT chat cards are built in `slice-20`.

## Out of scope for this slice
- ITSM mock + adapter (`slice-18`).
- End-to-end ticket-status card (`slice-20`), ticket creation + dedupe (`slice-19`), password reset (`slice-21`).
- HR and Admissions role packs.

## Human review required?
No.
