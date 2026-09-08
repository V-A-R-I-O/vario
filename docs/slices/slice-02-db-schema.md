# Slice 02 — db-schema

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 1 · **Module:** platform / data model

## References — read these first
- `AGENTS.md` (human review required for schema; secrets policy)
- `docs/ADD.md` § Data model (the 9 entities and their relationships — authoritative)
- `docs/vario-overview.md` § 12 (data model summary)
- `docs/api-contract.md` (field shapes that must round-trip: `entities`, `slots`, `details`, `available_variables`, enums)
- `.env.example` (`DATABASE_URL`)

## What to build
The full relational schema for VARIO's 9 entities, as SQLAlchemy models plus an Alembic migration, runnable against Postgres/Neon. This is the single source of truth — Postgres, no in-memory cache.

Deliverables:
- **SQLAlchemy models** for all 9 entities: `users`, `conversations`, `messages`, `sessions`, `intents`, `training_phrases`, `response_templates`, `response_variants`, `audit_log`.
- **Alembic migration** that creates them (with an `up` and `down`).
- **DB session/engine wiring** reading `DATABASE_URL`.
- A **seed-runner scaffold** (empty hooks the role-pack slices will fill) — this slice does not author role-pack intent data.

Schema specifics (from `docs/ADD.md`):
- `users`: `user_id`, `email`, `full_name`, `role`, `external_id`, `created_at`.
- `conversations`: belongs to `users`; `role_pack`, `title`, `status`, `created_at`, `last_message_at`.
- `messages`: belongs to `conversations`; `sender` (`user`|`bot`), `content`, `intent_name`, `confidence`, `entities` (JSONB), `created_at`.
- `sessions`: 1:1 with `conversations`; `current_form`, `current_step`, `slots` (JSONB), `expires_at`.
- `intents`: `role_pack`, `name`, `intent_type` (`dynamic_workflow`|`static_faq`), `needs_retrain`, `updated_at`.
- `training_phrases`: belongs to `intents`; `phrase_text`, authored by a `users` (admin), `created_at`.
- `response_templates`: `role_pack`, `template_key`, `base_text`, `allow_rephrasing`, `available_variables` (string array).
- `response_variants`: belongs to `response_templates`; `variant_text`, `generated_at`. (5 rows per template: original at index 0 + 4 generated.)
- `audit_log`: append-only; references `users` as actor; `action_type`, `reference_id`, `details` (JSONB), `created_at`.

## Acceptance criteria
- [ ] Given a fresh database, when the migration runs `up`, then all 9 tables are created with the columns/types above; `down` drops them cleanly.
- [ ] Given the migration, when it runs against a **Neon** database (via `DATABASE_URL`), then it succeeds.
- [ ] Given the schema, then foreign keys enforce: `conversations→users`, `messages→conversations`, `sessions→conversations` (unique 1:1), `training_phrases→intents`, `response_variants→response_templates`, `audit_log→users`.
- [ ] Given the schema, then JSONB columns exist for `messages.entities`, `sessions.slots`, `audit_log.details`, and `response_templates.available_variables` is a string array.
- [ ] Given the schema, then check/enum constraints enforce `messages.sender ∈ {user,bot}`, `intents.intent_type ∈ {dynamic_workflow,static_faq}`, and `role_pack ∈ {hr,it,admissions}` on `intents`, `response_templates`, and `conversations`.
- [ ] Given the model layer, when the backend imports it, then it connects using `DATABASE_URL` with no hardcoded credentials.
- [ ] There is **no** `auth_tokens` table (removed per ADR-001).

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Seeding role-pack intents / phrases / templates (each role owner does this in their own slice).
- Business logic, CRUD endpoints, ORM query helpers beyond what the migration needs.
- Provisioning the Neon instance itself (that's `slice-30-vercel-neon`) — this slice consumes the `DATABASE_URL` it provides.

## Human review required?
**Yes** — schema / data-model change. Coordinate the `DATABASE_URL` with `slice-30`.
