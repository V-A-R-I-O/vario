# Slice 24 — adm-app-status

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** C · **Sprint:** 2 · **Module:** Admissions role pack (end-to-end feature)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Chat (response shape)
- `docs/ui-reference.md` § 4 → **Data card** and **Not found** bot message types
- `docs/vario-overview.md` § 6 (FR-14, FR-17), § 8 (UC-5)
- Depends on: `slice-05-chat-core`, `slice-22-adm-rasa`, `slice-23-adm-adapter`

## What to build
The first fully working Admissions thread: an applicant asks for their application status by ID and gets a status card with next steps — or a graceful, helpful "not found" when the ID is unknown. Connects `slice-22` and `slice-23` through `chat-core`.

Deliverables:
- Complete `action_check_application_status` in Rasa-Admissions so it reads the `application_id` entity, calls `AdmissionsAdapter.get_application_status`, and returns the `template_key` + slots.
- Seed the application-status `response_template` + variants using `{application_id}` / `{status}` placeholders.
- An Admissions **status card** composing the shared data-card component; plus the **not-found** component wired to show a suggested next step (FR-17).
- Verify the full path in the deployed app.

## Acceptance criteria
- [ ] Given a logged-in applicant in an Admissions conversation, when they ask for a valid application's status, then a status card renders with status + next step.
- [ ] Given an unknown application id, then the bot returns a graceful "not found" with a suggested next step (FR-17) — no crash.
- [ ] Given the bot response, then the persisted bot message records `intent_name = check_application_status` and a `confidence`.
- [ ] Given repeated asks, then wording varies (renderer picks a random variant).
- [ ] Given a merge to `main`, then the working flow is visible in the deployed app.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` — **data card** + **not found** examples (matches `docs/ui-reference.md` §4).

## Out of scope for this slice
- Document checklist (`slice-25`) and fee/deadline calendar (`slice-26`).
- Voice / talk mode.

## Human review required?
No.
