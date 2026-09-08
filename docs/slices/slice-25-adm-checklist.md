# Slice 25 — adm-checklist

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 3 · **Module:** Admissions role pack (end-to-end feature)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (session / slots)
- `docs/ui-reference.md` § 4 → **List** and **Slot prompt** bot message types
- `docs/vario-overview.md` § 6 (FR-15)
- Depends on: `slice-05-chat-core`, `slice-22-adm-rasa`, `slice-23-adm-adapter` (`get_document_checklist`)

## What to build
A document-checklist lookup: the applicant names a program and gets the required-documents list.

Deliverables:
- A Rasa-Admissions intent `get_document_checklist` with a `program` slot/entity.
- Custom action calling `AdmissionsAdapter.get_document_checklist(program)`, returning a `template_key` + the checklist items.
- Render via the shared **list** component (numbered/bulleted).
- If no program is specified, ask which program (slot prompt); handle unknown programs gracefully.

## Acceptance criteria
- [ ] Given a program, when the applicant asks for the document checklist, then the bot returns the checklist as a list.
- [ ] Given no program specified, then the bot prompts for the program before answering.
- [ ] Given an unknown program, then the bot returns a graceful not-found (no crash).
- [ ] Given the bot response, then the persisted bot message records the intent + confidence.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **list** + **slot prompt** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Application status (`slice-24`) and fee/deadline (`slice-26`).
- Voice / talk mode.

## Human review required?
No.
