# V.A.R.I.O. (Voice Adaptive Role & Intent Orchestrator)

A role-specific voice assistant framework for organizations: one core engine, with pluggable **role packs** for HR, IT support and Admissions. Each role pack does three things:
- recognises intents with Rasa;
- runs multi-step workflows such as leave requests, IT tickets and password resets;
- calls the organization's internal systems, which are mocked here.

Users chat or talk to it. Admins manage intents, answers and retraining from a web console.

> **Status:** Sprint 4. Everything runs locally with Docker Compose; there is no cloud deployment (see `docs/decisions/ADR-007-local-first-runtime.md`). GitHub Actions runs the tests on every PR.

## Run the demo

You need Docker Desktop with about 12 GB of memory for Docker.

```bash
cp .env.example .env      # then set JWT_SECRET (and RETRAINING_INTERNAL_TOKEN)
docker compose build      # first time: 15–25 min, it trains the three Rasa models
docker compose up -d      # wait until `docker compose ps` shows every service healthy
```

Open <http://localhost:3000> and log in as `emp1@org.example.com` / `password123`.

To run it on one laptop and present from others on the same Wi-Fi or hotspot, follow **[docs/demo/local-demo.md](docs/demo/local-demo.md)**. It covers the firewall, the network, the microphone on client laptops, every demo account, resets and troubleshooting.

```bash
docker compose down       # stop; data is kept in volumes
docker compose down -v    # stop and wipe everything (the next start re-seeds)
```

## What runs

| Service | Port | What it is |
|---|---|---|
| `frontend` | **3000** (the only port other laptops need) | Next.js chat UI and admin console. It proxies `/api` to the gateway. |
| `gateway` | 127.0.0.1:8000, see [API docs](http://localhost:8000/docs) | FastAPI: auth, chat routing, admin, retraining. It migrates and seeds the database on start. |
| `postgres` | 127.0.0.1:5432 | VARIO data, plus each pack's Rasa tracker store (`rasa_hr`, `rasa_it`, `rasa_admissions`) |
| `rasa-hr`, `rasa-it`, `rasa-admissions` | 127.0.0.1:5005 / 5006 / 5007 | Rasa Open Source 3.6.20, one per role pack, each with an action server |
| `mock-auth`, `mock-hrms`, `mock-itsm`, `mock-admissions` | 127.0.0.1:9001–9004 | Stand-ins for the organization's login, HR, ticketing and admissions systems |

## Demo accounts

Every account's password is `password123`. The full list, with IT security answers, is in the [runbook](docs/demo/local-demo.md#4-demo-accounts).

| Login | Use it for |
|---|---|
| `emp1@`, `pavan@`, `tahir@`, `rohith@`, `mitesh@org.example.com` | Employees: HR and IT chats (one per presenter) |
| `applicant@org.example.com` | Admissions chats |
| `hr@`, `it@`, `admissions@org.example.com` | The admin console for each pack |

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI gateway, Alembic migrations, seed script (`python -m scripts.seed`) |
| `frontend/` | Next.js app |
| `rasa-hr/`, `rasa-it/`, `rasa-admissions/` | Role packs: Rasa config, domain, training data, custom actions |
| `rasa-shared/` | The gateway ↔ Rasa contract (ADR-006): input channel, redacting tracker store, card fixtures |
| `mock-*-service/` | Mock internal systems |
| `docs/` | PRD, architecture (ADD), API contract, decisions (ADRs), slices, sprints, test reports |

## Developing without Docker

Each service also runs natively; see the README in each folder.
- The Rasa packs need **Python 3.10** (Rasa 3.6 doesn't support 3.11+).
- Use `.env.example` for the native URLs and export `PYTHONPATH=<repo>/rasa-shared` for the packs.
- The frontend's `/api` proxy targets `http://localhost:8000` unless `API_PROXY_TARGET` is set.

Tests:
- `backend/`: `python -m pytest`
- `frontend/`: `npm test`
- each pack and mock: `python -m pytest` in its folder
- `rasa-shared/`: `python -m pytest`, with Rasa installed

## Where to read more

- `docs/overview.md`: the whole project on one page
- `docs/PRD.md` and `docs/ADD.md`: requirements and architecture
- `docs/api-contract.md`: the gateway API
- `docs/decisions/`: architecture decisions (ADR-006 is the Rasa contract)
- `AGENTS.md`: how work is split into slices and sprints
