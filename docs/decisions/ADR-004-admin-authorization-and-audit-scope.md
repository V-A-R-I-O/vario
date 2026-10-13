# ADR 004: Admin Authorization & Audit-Log Scoping

**Date:** 2026-10-13
**Status:** Accepted
**Slice:** slice-07-admin-shell

## Context
The admin console must (a) admit only admins, and (b) scope every admin to their own role pack — an `hr_admin` must never see IT or Admissions data. The gateway JWT middleware (slice-03) already authenticates requests and puts `{user_id, role, email}` on `request.state`, but it does not enforce admin-ness or resolve a role pack. The `audit_log` table from the initial schema (slice-02) had no column to scope entries by pack.

## Decision

### Reusable admin guard
`require_admin` (in `app/services/admin_guard.py`) is a FastAPI dependency layered on top of the gateway middleware. It reads the already-verified role claim, maps it to a role pack, and returns an `AdminContext(user_id, role, role_pack, email)`. A non-admin (or missing) role → `403`; a missing/invalid token is already `401` upstream.

The role → pack mapping is defined once, here:

| JWT role            | role pack     |
|---------------------|---------------|
| `hr_admin`          | `hr`          |
| `it_admin`          | `it`          |
| `admissions_admin`  | `admissions`  |

Admin routers depend on `require_admin` rather than re-reading `request.state`, so scoping is consistent and future admin endpoints (slices 08–11) inherit it for free. Enforcing admin-ness at the route (not the middleware) keeps data-level scoping next to the queries that use it.

### Audit-log gets a `role_pack` column
`audit_log` gains a nullable, indexed `role_pack` column (migration `b1c2d3e4f5a6`). The write-only sink (`audit_log_service.record`) always sets it; `GET /api/admin/audit-log` filters strictly on `admin.role_pack`, so cross-pack entries are invisible by construction — there is no parameter to request another pack's data.

### Fire-and-forget sink
`record(...)` is best-effort: a failed audit write is rolled back and logged, never raised, so logging can never break the business action that triggered it.

## Consequences
- **Positive:** One place defines "who is an admin" and "which pack they own"; every admin route stays uniform. The 403-on-cross-pack guarantee is structural (scoped query), not a per-endpoint check that could be forgotten.
- **Positive:** The audit sink is decoupled and safe to call from any module without transaction-coupling concerns.
- **Negative / human review:** This establishes role-based authorization — flagged for human review per `AGENTS.md` before merge/deploy.
- **Note:** `role_pack` is nullable for migration safety on the pre-existing table; all new writes populate it, and reads filter by a concrete pack so null rows are simply never returned.
