# V.A.R.I.O. (Voice Adaptive Role & Intent Orchestrator)

> **Status:** Planning complete. Development is about to begin with Sprint 1.

---

## Overview

V.A.R.I.O. is a role-specific, context-aware conversational framework designed to handle organizational workflows and queries across multiple functional domains (HR, IT Support, Admissions) from a single reusable core engine.

## Current Status

Planning and documentation are complete. The product requirements, architecture, API contract, and UI reference are finalized, and the work has been broken down into sprints and vertical slices. Implementation has not started yet.

* **Version:** `0.1.0-dev`
* **Development Phase:** Sprint 1 — Foundations & Infrastructure

## Upcoming Milestones

* Standing up the deployment pipeline and walking skeleton (Sprint 1)
* Building the three role packs and their read flows (Sprint 2)
* Implementing write workflows, the admin console, and voice (Sprint 3)
* Cross-cutting services, hardening, and demo (Sprint 4)

---

## Local Development

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (≥ 24.0)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2, bundled with Docker Desktop)

### Quick Start

```bash
# 1. Clone the repo
git clone <repo-url> && cd vario

# 2. Set up environment
cp .env.example .env
# Fill in any blank values (JWT_SECRET, API keys, etc.)

# 3. Start the core stack
docker compose up
```

This brings up the **core services** — Postgres, the FastAPI backend (gateway), the Next.js frontend, and the mock-auth service. All data is persisted in a Docker volume (`pgdata`).

### Starting the Full Stack (including stubs)

To also start the stub services (Rasa instances and remaining mock services):

```bash
docker compose --profile full up
```

> **Note:** Rasa images are large (~2 GB). The first pull will take a few minutes. Stub services will be replaced with real implementations as their slices land.

### Stopping the Stack

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop containers AND delete volumes (fresh start)
```

### Service Ports

| Service | Port | Description |
|---|---|---|
| `frontend` | [localhost:3000](http://localhost:3000) | Next.js UI |
| `gateway` | [localhost:8000](http://localhost:8000) | FastAPI backend — [health check](http://localhost:8000/health), [API docs](http://localhost:8000/docs) |
| `postgres` | `localhost:5432` | PostgreSQL 16 |
| `mock-auth` | `localhost:9001` | Mock authentication service |
| `mock-hrms` | `localhost:9002` | Mock HRMS *(stub)* |
| `mock-itsm` | `localhost:9003` | Mock ITSM *(stub)* |
| `mock-admissions` | `localhost:9004` | Mock Admissions *(stub)* |
| `rasa-hr` | `localhost:5005` | Rasa HR role pack *(stub)* |
| `rasa-it` | `localhost:5006` | Rasa IT role pack *(stub)* |
| `rasa-admissions` | `localhost:5007` | Rasa Admissions role pack *(stub)* |

### Environment Variables

All configuration is read from `.env` — see [`.env.example`](.env.example) for the full list. No secret values are committed to the repo.

---

*Planning docs live in `docs/`. Starting Sprint 1*
