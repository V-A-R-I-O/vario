# Slice 08 — admin-intent-crud

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 3 · **Module:** `admin-crud` (+ Create/Edit Intent page)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Admin — Intents (`GET`/`POST`/`PUT`/`DELETE`), § Admin — Response Templates (`GET`/`PUT`), § Admin — Response Variants (`PUT`/`DELETE`) — read the notes on `static_faq` vs `dynamic_workflow`, immutable names, placeholder validation, and the 5-variants rule
- `docs/ADD.md` → `admin-crud` module
- `docs/ui-reference.md` § 7 (Create/Edit Intent — Mode A dynamic workflow, Mode B static FAQ, shared elements)
- `docs/vario-overview.md` § 6 (FR-18)
- Depends on: `slice-07-admin-shell` (authorization + Intent List shell)

## What to build
Full CRUD for the admin's role-pack config, plus the Create/Edit Intent page. Enforce the business rules that keep developer-owned workflows safe while letting admins own their FAQs.

> **Rephraser seam:** `POST /api/admin/intents` and template save are supposed to auto-generate variants, but the rephraser itself is `slice-09` (Sprint 4). Build a `RephraserClient` **interface** here with a passthrough default (stores the original `base_text` as variant index 0, no generated variants) so CRUD ships now; `slice-09` implements real generation behind the same interface. Same for the "Generate Similar" endpoint — wire the route, stub the generation.

Deliverables:
- Endpoints (all scoped by role claim via `slice-07`): `GET`/`POST`/`PUT`/`DELETE /api/admin/intents[/:id]`, `GET`/`PUT /api/admin/templates[/:id]`, `PUT`/`DELETE /api/admin/variants/:id`.
- Business rules: FAQ create → `intent_type: static_faq`, empty `available_variables`, `needs_retrain: true`, `409` on duplicate name, `422` on validation; `PUT` intent → `403` when renaming a `dynamic_workflow`; `DELETE` → only `static_faq` (dynamic → `403`); variant `PUT` → `422` if placeholders from the base template are missing; variant `DELETE` → `400` on the original (index 0).
- `RephraserClient` interface + passthrough default (see seam note).
- **Create/Edit Intent page**, two modes:
  - **Mode A (dynamic workflow):** read-only System Key, available-variables badges/chips, response textarea with an "unknown variable" warning, training-phrases section. Name + variables not editable.
  - **Mode B (static FAQ):** validated intent-name input, response textarea (no variables), training-phrases section.
  - Shared: training-phrases add/delete + "Generate Similar" button (calls the stubbed endpoint until `slice-09`), "Allow rephrasing" toggle + variant list (editable/deletable), Save/Cancel.

## Acceptance criteria
- [ ] Given an admin creating a FAQ, then it's stored as `static_faq` with empty `available_variables` and `needs_retrain: true`; a duplicate name → `409`; missing name/phrases → `422`.
- [ ] Given a `PUT` that renames a `dynamic_workflow`, then `403`; renaming a `static_faq` succeeds.
- [ ] Given `DELETE` on a `static_faq`, then it deletes the intent + its phrases/template/variants; on a `dynamic_workflow`, then `403`.
- [ ] Given a variant `PUT` that drops a placeholder present in the base template, then `422`; a variant `DELETE` on the original (index 0), then `400`.
- [ ] Given any admin op on another role pack's resource, then `403`.
- [ ] Given the Create/Edit Intent page, then Mode A shows read-only key + variable badges + unknown-variable warning, and Mode B shows a validated name + variable-free textarea.
- [ ] Given the rephraser seam, then CRUD works end-to-end with the passthrough client (original stored as the only variant) and swaps to real generation when `slice-09` lands, with no contract change.

## Mockup / reference (if UI-facing)
`docs/design/admin-create-edit-intent.html` (matches `docs/ui-reference.md` §7).

## Out of scope for this slice
- Real LLM variant generation and "Generate Similar" phrase generation (`slice-09`).
- Retraining (`slice-10`).

## Human review required?
No — authorization is enforced by `slice-07`, and deletes are guarded (static-FAQ only, role-scoped). Standard PR review applies.
