# VARIO — Rasa Admissions Role Pack

NLU and dialogue orchestration engine for the Admissions Role Pack. Runs at `RASA_ADMISSIONS_URL` (`http://localhost:5007` natively, `http://rasa-admissions:5005` in compose).

## Core Responsibilities

- **Intent Recognition:** Identifies user intentions (`check_application_status`, `get_document_checklist`, `ask_fee_deadline`).
- **Entity Extraction:** Extracts `application_id` (e.g., `APP-1001`) and degree `program`.
- **Dialogue Policy & Fallback:** `FallbackClassifier` triggers graceful fallback prompts when confidence < 0.4 or when intent ambiguity is detected (`ambiguity_threshold: 0.1`).
- **Missing Slot Prompts:** When checking application status without providing an ID, requests the application ID rather than assuming a default ID.
- **VARIO Converse Contract:** `POST /webhooks/vario/converse` per `docs/decisions/ADR-006-rasa-contract-v2.md`, through the shared channel in `rasa-shared/`.

## Runtime

Admissions runs on **real Rasa Open Source 3.6.20**, like HR and IT (ADR-006):

- **Rasa server:** the shared `vario_rasa.channel.VarioInputChannel` serves `POST /webhooks/vario/converse`, and dialogue state is kept in the redacting SQL tracker store (`endpoints.yml`).
- **Action server:** `rasa run actions` runs `actions/actions.py`, which calls mock-admissions through `actions/admissions_adapter.py` (`MOCK_ADMISSIONS_URL`).
- **Forms:** `application_status_form` asks for the `APP-####` ID and `checklist_form` asks for the program (with B.Tech / M.Tech / MBA buttons). A fee, checklist or status question asked while a form is waiting interrupts it (rules in `data/rules.yml`).
- **Docker:** `docker build -f rasa-admissions/Dockerfile .` from the repo root trains the model at build time; the same image runs the action server.

Run natively (Python 3.10):

```bash
pip install -r requirements-rasa.txt
export PYTHONPATH=../rasa-shared:.
rasa train
MOCK_ADMISSIONS_URL=http://localhost:9004 rasa run actions --actions actions --port 5055 &
ACTION_ENDPOINT_URL=http://localhost:5055/webhook POSTGRES_HOST=localhost POSTGRES_DB=rasa_admissions \
  POSTGRES_USER=vario POSTGRES_PASSWORD=vario rasa run --enable-api --port 5007
```

Tests:

- `tests/test_real_rasa_admissions.py` (Python 3.10, `requirements-rasa.txt`) trains the model and drives the flows end to end against the real mock service.
- `tests/test_admissions_rasa.py` covers the legacy keyword `server.py` (Python 3.11, `requirements.txt`). `server.py` is no longer the runtime and is kept only for those tests.

## Directory Structure

```
rasa-admissions/
├── config.yml           # Pipeline and policy configuration (DIET, FallbackClassifier)
├── domain.yml           # Intents, entities, slots, forms, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations (ActionCheckApplicationStatus)
└── server.py            # Legacy keyword runtime, kept only for tests/test_admissions_rasa.py
```

