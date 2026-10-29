# Slice 28 — CI and Local Build Validation

**Owner:** B · **Sprint:** 1 · **Module:** CI

## Decision
VARIO is developed and demonstrated locally. This slice owns continuous integration, not cloud deployment. OCI, permanent Cloudflare-hosted backend deployment, Vercel and Neon are superseded by the local-demo decision in Slice 34 / ADR-007.

## What to build
- GitHub Actions CI on pull requests and pushes to `main`.
- Install dependencies, run backend tests, frontend tests, lint and builds using the repository's actual scripts.
- Require passing CI and a pull-request review through repository branch protection.
- Keep secrets out of the repository; add only secrets required by active tests/workflows.

## Acceptance criteria
- [ ] Pull request updates trigger CI.
- [ ] CI runs the supported backend/frontend checks and builds; failures are visible and block merge where branch protection is configured.
- [ ] Main branch protection requires CI and review.
- [ ] No workflow deploys the application to OCI, Cloudflare, Vercel or Neon.
- [ ] Local startup instructions are documented in the README and Slice 34 runbook.

## Out of scope
- Production/cloud deployment and hosting.
- OCI VM provisioning, permanent Cloudflare Tunnel, Vercel project and Neon database provisioning.
- New deployment secrets or cloud-specific environment wiring.

## Human review required?
Yes — CI configuration, secrets and branch protection.
