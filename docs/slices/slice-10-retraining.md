# Slice 10 — retraining

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 4 · **Module:** `retraining-service`

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Admin — Retraining (`POST /api/admin/retrain` — role from JWT, `202` + job id; `GET /api/admin/retrain/:job_id` — states)
- `docs/ADD.md` → `retraining-service` module + admin flow diagram
- `docs/ui-reference.md` § 8 (Retraining page)
- `docs/vario-overview.md` § 6 (FR-3: new/updated intents live via config, no redeploy)
- Depends on: `slice-07-admin-shell` (authz), `slice-08-admin-intent-crud` (the intent/phrase data), `slice-12/17/22` (the Rasa instances)

## What to build
Manual, admin-triggered retraining: pull the role pack's intents + phrases from Postgres, build Rasa YAML, `rasa train`, reload the live instance, clear `needs_retrain`. This is what makes admin edits (`slice-16` etc.) actually take effect — closing the FR-3 loop.

Deliverables:
- **retraining-service** — reads intents + training phrases for the role pack, converts to Rasa YAML, runs `rasa train`, reloads the corresponding live Rasa instance, clears `needs_retrain` for that pack. Long-running (~30–120s); run as an async job.
- **`POST /api/admin/retrain`** — role pack **derived from the JWT** (not the body); returns `202` + `retrain_job_id`. (Gateway already rate-limits this 3/hour.)
- **`GET /api/admin/retrain/:job_id`** — returns `state` (`pending` | `training` | `complete` | `failed`), timestamps, and `error_message`.
- **Retraining page** — role-pack model name, last-trained timestamp, status ("Up to date" / "N intents modified"), "Retrain Now" button, progress (pending → training → complete/failed), estimated time, error display on failure.

## Acceptance criteria
- [ ] Given an admin triggers `POST /api/admin/retrain`, then it returns `202` with a job id, and the role pack is taken from the JWT (a body value cannot retrain another pack).
- [ ] Given a retrain job, then it builds Rasa YAML from that pack's intents/phrases, runs `rasa train`, and reloads the live Rasa instance.
- [ ] Given a completed retrain, then `needs_retrain` is cleared for that pack's intents.
- [ ] Given `GET /api/admin/retrain/:job_id`, then it reports the correct state through `pending → training → complete` (or `failed` with a message).
- [ ] Given a static FAQ created earlier (`slice-16`) and then a retrain, then the bot recognises the new FAQ afterward — with no code change or redeploy (FR-3).
- [ ] Given the Retraining page, then it shows status/progress and surfaces failures.

## Mockup / reference (if UI-facing)
`docs/design/admin-retraining.html` (matches `docs/ui-reference.md` §8).

## Out of scope for this slice
- Automatic/scheduled retraining (manual trigger only).
- Variant/phrase generation (`slice-09`).

## Human review required?
No — operational feature (shells out to `rasa train` and reloads a model); not infra/CI config or secrets. Standard PR review applies.
