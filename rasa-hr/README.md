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

## Runtime Architecture: Live Rasa vs. Development Mock

1. **Full Rasa Open Source Engine (Docker / OCI — Slice 27 / Slice 29):**
   - Built via `Dockerfile` and orchestrated with `docker-compose.yml` using `rasa/rasa:3.6.20-full`.
   - Uses `config.yml`, `domain.yml`, and `data/nlu.yml` to train and serve DIETClassifier and FallbackClassifier.
   - Connects custom channel `channels.vario.VarioInputChannel` to expose `POST /webhooks/vario/converse`.

2. **Scoped Development Mock & Proxy (`server.py`):**
   - Lightweight FastAPI service running at `RASA_HR_URL` implementing the ADR-002 converse webhook contract.
   - When `RASA_NLU_URL` is set, dynamically proxies classification requests to the upstream live Rasa `/model/parse` endpoint.
   - When running standalone without the heavy 4GB Rasa Docker container, operates as a deterministic rule-based mock for fast local development and unit tests.

## Directory Structure

```
rasa-hr/
├── config.yml           # Pipeline and policy configuration
├── domain.yml           # Intents, entities, slots, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── server.py            # FastAPI server running ADR-002 converse webhook & upstream proxy
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations (action_check_leave_balance)
├── channels/
│   └── vario.py         # ADR-002 converse webhook implementation
└── tests/
    └── test_hr_rasa.py  # Unit and regression tests for HR Rasa service
```
