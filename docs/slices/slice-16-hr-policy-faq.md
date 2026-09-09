# Slice 16 — hr-policy-faq

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 3 · **Module:** HR role pack (static FAQ + HR admin content)

## References — read these first
- `AGENTS.md`
- `docs/api-contract.md` § Admin — Intents (`POST` FAQ create → `static_faq`)
- `docs/ui-reference.md` § 4 → **FAQ answer** bot message type, § 7 → Mode B (Create Static FAQ)
- `docs/vario-overview.md` § 6 (FR-7), § 8 — US-6
- Depends on: `slice-05-chat-core`, `slice-08-admin-intent-crud` (console), `slice-12-hr-rasa`

## What to build
HR policy FAQs end-to-end, plus proving the HR admin can own them from the console. This is where A exercises the admin UI for their role pack.

Deliverables:
- Seed a few HR policy FAQ intents (`static_faq`): e.g. WFH policy, leave policy — training phrases + static response templates.
- An `ask_policy_faq`-style classification in Rasa-HR that resolves to the right FAQ answer, rendered via the **FAQ answer** component.
- **HR admin usage:** verify an `hr_admin` can create/edit a policy FAQ through the console (`slice-08` framework), scoped to HR, and that it sets `needs_retrain` (it becomes live after retraining, `slice-10`).

## Acceptance criteria
- [ ] Given an HR policy question (e.g. "what's the WFH policy?"), when asked in an HR conversation, then the bot returns the policy answer via the FAQ-answer component.
- [ ] Given an `hr_admin`, when they create a new static FAQ (name + phrases + response) in the console, then it is stored scoped to HR with `needs_retrain: true`.
- [ ] Given a low-confidence policy question, then the bot asks for clarification rather than answering wrongly (FR-2 upstream).
- [ ] Given the seed step, then the default HR policy FAQs exist and are visible in the HR admin Intent List.

## Mockup / reference (if UI-facing)
`docs/design/chat-view.html` (FAQ answer) and `docs/design/admin-create-edit-intent.html` (Mode B) — match `docs/ui-reference.md` §4, §7.

## Out of scope for this slice
- LLM variant generation / "Generate Similar" (`slice-09`) and retraining execution (`slice-10`) — creating the FAQ + setting `needs_retrain` is enough here.
- Leave balance (`slice-14`) and leave request (`slice-15`).
- IT and Admissions content.

## Human review required?
No.
