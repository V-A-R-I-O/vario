#!/bin/sh
# Gateway container start: bring the schema up to date, load the idempotent
# role-pack seed, then serve. Safe to run on every start.
set -eu

alembic upgrade head
python -m scripts.seed

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
