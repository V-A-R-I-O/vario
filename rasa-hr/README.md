# VARIO — Rasa HR Role Pack

NLU and dialogue orchestration engine for the HR Role Pack. Runs at `RASA_HR_URL` (`http://localhost:5005`).

## Core Responsibilities

- **Intent Recognition:** Identifies user intentions (`check_leave_balance`, `ask_leave_status`, `submit_leave_request`, `ask_policy_faq`).
- **Entity Extraction:** Extracts `employee_id` (e.g., `EMP-1042`), `leave_type` (e.g., `annual`, `sick`, `casual`), and `policy_topic` (e.g., `maternity`, `paternity`, `sick`).
- **Dialogue Policy & Fallback:** `FallbackClassifier` triggers graceful fallback prompts when confidence < 0.4 (supports FR-2).
- **Employee Context & Privacy:** Validates employee context before returning leave data. Does not silently fall back to arbitrary employee data; prompts for required employee IDs when missing.
- **Sanitized Logging:** Never logs employee identifiers, raw message PII, or sensitive HR slot data in runtime logs.
- **VARIO Converse Contract:** Implements `POST /webhooks/vario/converse` per `docs/decisions/ADR-002-rasa-chat-contract.md`.
- **Custom Actions:** Provides `action_check_leave_balance` skeleton returning `template_key` + slots shape.

## Runtime

HR runs on **real Rasa Open Source 3.6.20** (ADR-006):

- **Rasa server:** the shared `vario_rasa.channel.VarioInputChannel` serves `POST /webhooks/vario/converse`; dialogue state lives in the redacting SQL tracker store (`endpoints.yml`).
- **Action server:** `rasa run actions` runs `actions/actions.py`, which calls mock-hrms through `actions/hrms_adapter.py` (`MOCK_HRMS_URL`). The signed-in employee comes from `metadata.auth_context`, never from chat text.
- **Leave form:** each slot is filled only while it is being asked for, so a later answer can't overwrite an earlier one. "cancel" leaves the form at any step, and a balance, status or policy question is answered before the form resumes.
- **Docker:** `docker build -f rasa-hr/Dockerfile .` from the repo root trains the model at build time; the same image runs the action server.

Run natively (Python 3.10):

```bash
pip install -r requirements-rasa.txt
export PYTHONPATH=../rasa-shared:.
rasa train
MOCK_HRMS_URL=http://localhost:9002 rasa run actions --actions actions --port 5055 &
ACTION_ENDPOINT_URL=http://localhost:5055/webhook POSTGRES_HOST=localhost POSTGRES_DB=rasa_hr \
  POSTGRES_USER=vario POSTGRES_PASSWORD=vario rasa run --enable-api --port 5005
```

Tests:

- `tests/test_real_rasa_hr_e2e.py` (Python 3.10, `requirements-rasa.txt`) trains the model and drives the HR flows end to end against the real mock service.
- `tests/test_real_rasa_hr.py` validates the data and NLU metrics.
- `tests/test_hr_rasa.py` covers the legacy keyword `server.py` (Python 3.11, `requirements.txt`). `server.py` is no longer the runtime and is kept only for those tests.

## Directory Structure

```
rasa-hr/
├── config.yml           # Pipeline and policy configuration
├── domain.yml           # Intents, entities, slots, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── server.py            # Legacy keyword runtime, kept only for tests/test_hr_rasa.py
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations (action_check_leave_balance)
└── tests/
    └── test_hr_rasa.py  # Unit and regression tests for HR Rasa service
```
