# Slice 31 — perf-hardening

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 4 · **Module:** platform (non-functional hardening)

## References — read these first
- `AGENTS.md`
- `docs/vario-overview.md` § 3 (success criteria) + § 7 (NFRs: Performance, Reliability, Security, Usability)
- `docs/PRD.md` § Success criteria (2s p95, 20 concurrent sessions)
- `docs/ADD.md` § Constraints (expected scale, performance budget, graceful degradation)

## What to build
Prove and harden the non-functional bar the demo will be judged on: performance under concurrency, graceful degradation, session recovery, and input validation. Run the load test **early in the sprint** so there's time to fix what it exposes.

Deliverables:
- **Load/perf test harness** simulating 20 concurrent sessions across the role packs; measure p95 latency (excluding the artificial mock-API delay); record results in `docs/perf-report.md`.
- **Graceful degradation** — verify/harden the end-to-end user experience when a mock API is down (inform, don't crash) for each role pack, and when TTS is unavailable (text fallback, from `slice-06`).
- **Session recovery** — confirm a conversation resumes correctly after a transient backend restart (Postgres is the source of truth).
- **Input validation/sanitization** — ensure user input is validated/sanitized before it reaches NLU or persistence.
- Fix the issues these expose (and log any coverage the test deliberately skips).

## Acceptance criteria
- [ ] Given 20 concurrent sessions, then p95 response time is < 2s excluding mock-API delays, with results documented in `docs/perf-report.md`.
- [ ] Given a mock API is down, when a user asks a question that needs it, then they get a graceful message and the system does not crash (verified per role pack).
- [ ] Given TTS is unavailable, then talk mode degrades to text.
- [ ] Given a backend restart mid-conversation, then the session resumes with its context intact.
- [ ] Given malformed or malicious input, then it is validated/sanitized before NLU or persistence.

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Production-scale tuning beyond the 20-session demo target.
- New features — this is hardening only.

## Human review required?
No (hardening of existing paths). Flag to a teammate if the input-sanitization work changes any security-relevant behaviour.

---

> **Sprint 4 also includes team-wide activities that are not slices:** an FR-by-FR test pass (every FR gets ≥1 automated or documented manual test), demo-script rehearsal, and doc finalisation. These are tracked in `docs/sprints/sprint-04.md`, not here.
