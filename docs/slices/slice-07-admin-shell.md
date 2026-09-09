# Slice 07 — admin-shell

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 3 · **Module:** admin console framework + `audit-log`

## References — read these first
- `AGENTS.md` (human review required — establishes admin authorization)
- `docs/api-contract.md` § Admin — Audit Log (`GET /api/admin/audit-log` — filters, pagination, envelope) + § top (roles: `hr_admin`, `it_admin`, `admissions_admin`)
- `docs/ADD.md` → `audit-log` module + § Security (admin endpoints scoped by role claim; an HR admin cannot access IT data)
- `docs/ui-reference.md` § Admin Console (shared layout + nav), § 6 (Intent List framework), § 9 (Audit Log)
- `docs/vario-overview.md` § 6 (FR-19, audit portion)

## What to build
The admin console frame that every admin page hangs off, the authorization that scopes an admin to their own role pack, and the audit-log sink + viewer. Intent CRUD itself is `slice-08`; this slice ships the shell + the Intent List **table framework** + audit log.

Deliverables:
- **Admin authorization** — admin routes require an admin role claim; every admin request is scoped to the admin's own role pack (an HR admin gets `403` on IT/Admissions data). Implement as a reusable guard on top of the gateway's JWT middleware (`slice-03`).
- **Admin layout & nav** — top bar (admin name + role badge: HR/IT/Admissions Admin + logout), side nav (Intent Management, Retraining, Audit Log, Conversation Logs). Distinct from the end-user nav. Nav + headers reflect the admin's role pack only.
- **Intent List page framework** — the table shell for the admin's role pack: rows show intent name, type badge (Dynamic Workflow vs Static FAQ), phrase count, needs-retrain badge, last-updated, actions (Edit / Delete, with Delete disabled for Dynamic Workflows); a retrain-status banner. (Row data comes from `GET /api/admin/intents` built in `slice-08`; build the shell + empty/loading states here.)
- **audit-log service** — write-only sink accepting `{actor_id, role_pack, action_type, reference_id, details}`, fire-and-forget.
- **`GET /api/admin/audit-log`** — scoped to the admin's role pack; filters `action_type` / `actor_id` / `from` / `to`; `limit` / `offset` pagination.
- **Audit Log page** — filter bar, results table (timestamp, actor, human-readable action, reference id, expandable JSONB details), pagination.

## Acceptance criteria
- [ ] Given a non-admin JWT, when any `/api/admin/*` route is called, then it returns `403`.
- [ ] Given an `hr_admin`, then the console nav/headers show HR only, and any attempt to read IT or Admissions admin data returns `403`.
- [ ] Given a business event, when a module calls the audit-log sink, then an `audit_log` row is appended (actor, role_pack, action_type, reference_id, details).
- [ ] Given `GET /api/admin/audit-log`, then it returns only the admin's role-pack entries, honouring the filters and pagination, in envelope form.
- [ ] Given the Intent List page, then it renders the role-pack's intents with type badges and the retrain-status banner, with Delete disabled for Dynamic Workflows; empty and loading states render.
- [ ] Given the Audit Log page, then filter bar, table with expandable details, and pagination work.

## Mockup / reference (if UI-facing)
`docs/design/admin-intent-list.html` and `docs/design/admin-audit-log.html` (match `docs/ui-reference.md` §6, §9).

## Out of scope for this slice
- Intent/phrase/template/variant create-edit-delete operations and the Create/Edit Intent page (`slice-08`).
- Rephraser / Generate Similar (`slice-09`), retraining (`slice-10`), conversation logs (`slice-11`).

## Human review required?
**Yes** — establishes admin role-based authorization. Do not merge without human review (per `AGENTS.md`).
