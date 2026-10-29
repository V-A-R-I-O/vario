# Slice 33 — chat-ui-hardening

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D (Tahir) · **Sprint:** 4 · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Module:** Frontend — chat shell and message component library · **Story points:** 3

**Jira:** _key assigned on import_ — use it in branch and commit names per `docs/engineering/vario-development-naming-convention.md`.

## References — read these first
- `AGENTS.md`
- `docs/testing/sprint-3-integration-audit.md` — the defects this slice closes, with repro steps
- `docs/decisions/ADR-006-rasa-contract-v2.md` (written in slice-32 — the contract every pack and the UI build against)
- `frontend/src/app/home/chat/[id]/page.tsx`
- `frontend/src/components/chat/`
- `frontend/src/lib/useSpeechRecognition.ts`
- `frontend/src/app/home/layout.tsx`
- `docs/mockups/ui-reference.md § 4`
- Depends on: ADR-006 from slice-32 (start on day 1 against its fixtures).

## Dev environment
Tahir — laptop A. Frontend runs natively; use the ADR-006 fixtures, no Rasa needed.

## What to build
- Render every bot card from that reply's own `card` field — live and from history. Remove the slot-key sniffing and regex-on-text card detection in `toThreadRow`.
- Disable Confirm/Cancel/option buttons while a send is in flight and once answered; guard `/home/new` against double-create.
- Refresh the sidebar conversation list after creating a conversation and after each turn.
- Talk mode: detect insecure origins (`window.isSecureContext`) and explain; exit the overlay with a message on any speech-recognition error and on a failed send.
- Distinct error messages for rate limit (429), server error and network failure; mark a failed user message and offer retry.
- Show an "Admin console" link for admin roles.

## Defects this slice closes

| Bug | Severity | Summary |
|---|---|---|
| B5b | Blocker | Chat page picks cards from accumulated session slots, so stale cards replace later replies |
| M12 | Major | Cards break after a page reload because card data isn't stored with the message |
| M8 | Major | Talk mode gets stuck on 'Listening…' and doesn't detect insecure origins |
| M10 | Major | Double-clicking Confirm or an option button sends the message twice |
| M11 | Minor | Sidebar conversation list never refreshes; admins have no link to the console |
| N2 | Minor | Every chat error shows 'Connection lost'; failed messages have no retry |

Each defect's repro steps double as a regression test: re-run them on laptop C before closing the Jira bug.

## Acceptance criteria
- [ ] Given an HR balance check followed by a WFH question and a leave request, then the WFH answer renders as text, the leave prompts show their options, and the confirmation shows Confirm/Cancel.
- [ ] Given an Admissions checklist followed by a status lookup, then the status lookup renders as a status card.
- [ ] Given any conversation, when the page is reloaded, then every card renders the same as it did live.
- [ ] Given a double-click on Confirm, then exactly one message is sent.
- [ ] Given the UI opened on `http://<LAN-IP>:3000`, when talk mode is started, then the user sees a "voice needs HTTPS or localhost" message instead of a stuck overlay.
- [ ] Given a speech-recognition error or a failed send in talk mode, then the overlay closes with a message.
- [ ] Given a 429, then the message tells the user to wait; given the backend is down, then it says the service is unavailable.
- [ ] Given a new conversation, then it appears in the sidebar without a reload.
- [ ] Given an admin login, then a link to `/admin` is visible.
- [ ] Given the Jest suite, then tests cover each criterion using ADR-006 contract-shaped fixtures.
- [ ] Every defect in the table above is re-tested with its repro steps and closed in Jira.

## Out of scope for this slice
- Backend changes (slice-32).
- Admin console pages (slice-40).

## Human review required?
No.
