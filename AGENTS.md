# AGENTS.md

> Instructions for AI coding agents working in this repo. Read this before starting any slice.

## What this project is
A Role-Specific Voice Assistant Framework for Organizations and Entities. Full context lives in `docs/PRD.md` and `docs/ADD.md` (the Architecture & Design Document) — read those first if you're unfamiliar with the project. `docs/vario-overview.md` is the best single-page briefing if you want the whole picture quickly.

## How work is structured
Work is broken into **slices** (`docs/slices/`), grouped into **sprints** (`docs/sprints/`). Each slice has:
- A module it belongs to (see `docs/ADD.md`)
- Acceptance criteria written as testable statements — treat these as the test plan
- An "out of scope" note, if present — do not build beyond it

**Only work on the slice you've been given.** Do not expand scope, add "nice to have" extras, or refactor unrelated code unless explicitly asked.

## Commit / PR convention
Reference the slice ID in your commit messages and PR title, e.g. `slice-03-user-auth: add login endpoint`. This keeps code traceable back to its spec.

## Human review required — do not merge/deploy without it
- Authentication / authorization changes
- Payments
- Data deletion or destructive migrations
- Infra / CI-CD configuration changes
- Anything touching secrets or environment variables

For everything else, proceed and open a PR as normal.

## Secrets & environment
Never read, log, or commit actual secret values. Reference `.env.example` for the list of expected variables — ask the human to provide actual values if needed.

## Testing
Acceptance criteria in the slice doc are the test contract. Write tests that verify those criteria, not just tests that pass against your own implementation.

## If something is ambiguous
Stop and ask, rather than guessing. If the slice, architecture, or PRD doesn't answer your question, flag it — don't assume.

## CI / Docker / release pipelines
The architecture *does* call for Docker Compose (local dev) and CI/CD on every PR (see `docs/ADD.md` and `docs/vario-overview.md` §9) — but these are deliberate infra slices, not things to add as a side effect of another task. Only create or modify CI workflows, Dockerfiles, `docker-compose.yml`, or release pipelines when the slice you're on is explicitly about that. Don't scaffold them incidentally.

## Decisions log
If you make a non-obvious architectural choice while executing a slice, note it in `docs/decisions/ADR-XXX-<short-name>.md` (short — a few lines is enough). Not every choice needs one — only ones that would be genuinely confusing to revisit later without the reasoning.