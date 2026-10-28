# VARIO — Rasa IT Support Role Pack

Implements the Slice 17 IT Support NLU assets and the ADR-002 /`webhooks/vario/converse` contract. The local lightweight runtime listens on port `5006` (`RASA_IT_URL=http://localhost:5006`).

- Primary intent: `check_ticket_status` with `ticket_id` extraction (for example, `TKT-1234`).
- Placeholder intents: `raise_ticket` and `reset_password` for later slices.
- Off-topic input falls back instead of being routed as an IT workflow.
- The status action returns the stable template/slot contract but does not invent ticket status. Slice 20 connects the ITSM adapter.
- `config.yml`, `domain.yml` and `data/*.yml` are the canonical Rasa training assets. The FastAPI runtime is lightweight for local development and CI; the real Rasa model can be trained from these assets separately.

Run locally from this directory:

```bash
python -m pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 5006
```

Run tests from this directory:

```bash
python -m pytest
```
