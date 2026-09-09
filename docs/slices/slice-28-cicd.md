# Slice 28 — cicd

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** B · **Sprint:** 1 · **Module:** infra / CI-CD

## References — read these first
- `AGENTS.md` (human review required for CI config + secrets; never commit secret values)
- `docs/vario-overview.md` § 9 (engineering process: pytest backend, Jest/RTL frontend, GitHub Actions, mandatory PR review)
- `docs/sprints/sprint-01.md` (this is the pipeline the whole "continuous delivery" plan depends on)
- Coordinates with `slice-29-oci-cloudflare` (backend deploy target) and `slice-30-vercel-neon` (frontend deploy target)

## What to build
The GitHub Actions pipeline that gates every PR and auto-deploys every merge to `main` — the backbone of the infra-first plan. After this lands, any merged slice is reflected in the live app automatically.

Deliverables:
- **`ci.yml`** (on pull request): install deps, lint, run backend tests (`pytest`) and frontend tests (`Jest`/React Testing Library), build both. Must pass to allow merge.
- **`deploy.yml`** (on push to `main`): build and deploy the backend to the OCI target (from `slice-29`) and the frontend to Vercel (from `slice-30`).
- **Branch protection** on `main`: require the CI checks to pass and require PR review before merge.
- All credentials referenced from **GitHub Actions secrets** — nothing committed.

## Acceptance criteria
- [ ] Given a pull request, when it's opened/updated, then CI runs backend `pytest` + frontend `Jest` + lint + build, and a failing check blocks merge.
- [ ] Given `main`'s branch protection, then a PR cannot merge without passing CI and at least one review.
- [ ] Given a merge to `main`, when the deploy workflow runs, then the frontend deploys to Vercel and the backend deploys to the OCI target.
- [ ] Given a trivial visible change merged to `main`, when the pipeline completes, then the change is visible on the live production URL.
- [ ] Given the workflows, then every credential/token is read from GitHub Actions secrets and none appears in the repo.

## Mockup / reference (if UI-facing)
No UI surface.

## Out of scope for this slice
- Provisioning the deploy targets themselves (OCI → `slice-29`, Vercel/Neon → `slice-30`); this slice consumes them.
- SonarQube / static-analysis gate (optional, later — note it as a follow-up, don't build it now).
- Coverage thresholds, blue/green or canary deploys.

## Human review required?
**Yes** — CI/CD configuration and secrets. Do not merge without human review (per `AGENTS.md`).
