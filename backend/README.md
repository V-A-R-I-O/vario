# VARIO gateway (FastAPI)

The gateway handles auth (via mock-auth), chat routing to the Rasa role packs, the admin API and retraining. The API is described in `docs/api-contract.md`; interactive docs are at `/docs` when it runs.

## Run with Docker

`docker compose up -d` from the repo root. On start, `docker-entrypoint.sh` runs `alembic upgrade head`, then the idempotent seed (`python -m scripts.seed`), then uvicorn.

## Run natively

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -r requirements.txt
cp ../.env.example .env        # set JWT_SECRET; DATABASE_URL points at localhost
alembic upgrade head
python -m scripts.seed         # safe to re-run
uvicorn app.main:app --reload --port 8000
```

Without `DATABASE_URL`, the gateway uses in-memory SQLite and creates its tables at startup; this is for quick experiments only. The mocks and Rasa packs are reached through the `MOCK_*_URL` and `RASA_*_URL` settings (see `app/config.py`).

## Tests

```bash
python -m pytest
```

The tests use SQLite and patch every outbound call, so no other service needs to run.
